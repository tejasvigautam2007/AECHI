"""
Lambda: triage
Triggered by EventBridge when a new HazardDetection event arrives.
Performs:
  - Distributed deduplication via DynamoDB conditional locking
  - Multi-camera Geo-Clustering (spatial & temporal event correlation)
  - Urgency & Triage scoring (1-10) with multi-node corroboration bonus
  - SNS alert routing for high severity incidents
"""

import json
import math
import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "aechi-events-prod")
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN", "")
DEDUP_WINDOW_SEC = int(os.environ.get("DEDUP_WINDOW_SEC", "5"))
GEO_CLUSTER_RADIUS_METERS = float(os.environ.get("GEO_CLUSTER_RADIUS_METERS", "150.0"))

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Triggered by EventBridge rule matching source=aechi.edge, DetailType=HazardDetection
    """
    detail = event.get("detail", {})
    logger.info(f"Triage initiated: {detail}")

    event_id = detail.get("event_id", "unknown")
    device_id = detail.get("device_id", "unknown")
    class_label = detail.get("class_label", "unknown")
    severity = str(detail.get("severity", "LOW")).upper()
    confidence = float(detail.get("confidence", 0.0))
    timestamp = int(detail.get("timestamp", time.time() * 1000))
    lat = float(detail.get("lat", 0.0))
    lon = float(detail.get("lon", 0.0))
    crop_s3_key = detail.get("crop_s3_key", "")

    # 1. Distributed Deduplication via DynamoDB
    if _is_duplicate_event(device_id, class_label, timestamp):
        logger.info(f"Deduped event: device={device_id} class={class_label}")
        return {"status": "deduped", "event_id": event_id}

    # 2. Geo-Clustering & Multi-Camera Corroboration
    incident_id, corroborating_devices = _correlate_incident(
        lat=lat,
        lon=lon,
        class_label=class_label,
        timestamp=timestamp,
        device_id=device_id
    )

    # 3. Urgency / Triage Scoring
    triage_score = _compute_triage_score(
        class_label=class_label,
        severity=severity,
        confidence=confidence,
        corroborating_count=len(corroborating_devices)
    )

    # 4. Update Original Event in DynamoDB
    _update_event_record(
        device_id=device_id,
        timestamp=timestamp,
        event_id=event_id,
        triage_score=triage_score,
        incident_id=incident_id,
        corroborating_count=len(corroborating_devices)
    )

    # 5. Alert Trigger (HIGH severity and triage_score >= 7)
    if severity == "HIGH" and triage_score >= 7:
        _publish_alert(
            event_id=event_id,
            incident_id=incident_id,
            device_id=device_id,
            class_label=class_label,
            severity=severity,
            score=triage_score,
            confidence=confidence,
            lat=lat,
            lon=lon,
            corroborating_devices=corroborating_devices,
            crop_s3_key=crop_s3_key
        )

    return {
        "status": "triaged",
        "event_id": event_id,
        "incident_id": incident_id,
        "triage_score": triage_score,
        "severity": severity,
        "corroborating_cams": len(corroborating_devices)
    }


def _is_duplicate_event(device_id: str, class_label: str, timestamp: int) -> bool:
    """
    Distributed atomic dedup check using DynamoDB conditional write.
    Bucket timestamp by DEDUP_WINDOW_SEC window.
    """
    time_window = timestamp // (DEDUP_WINDOW_SEC * 1000)
    dedup_pk = f"DEDUP#{device_id}#{class_label}"
    dedup_sk = f"WINDOW#{time_window}"

    try:
        table.put_item(
            Item={
                "pk": dedup_pk,
                "sk": dedup_sk,
                "ttl": int(time.time()) + (DEDUP_WINDOW_SEC * 3),
            },
            ConditionExpression="attribute_not_exists(pk)"
        )
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True
        logger.warning(f"Dedup check error: {e}")
        return False


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _correlate_incident(lat: float, lon: float, class_label: str, timestamp: int, device_id: str):
    """
    Identify or create an active incident cluster within GEO_CLUSTER_RADIUS_METERS
    and a 60-second window.
    """
    incident_window_ms = 60 * 1000
    now_ms = timestamp
    window_start = now_ms - incident_window_ms

    corroborating = {device_id}

    if lat == 0.0 and lon == 0.0:
        # Fallback if no geo coords provided
        return f"INC-{class_label[:3].upper()}-{str(now_ms)[-6:]}", list(corroborating)

    # Query active incidents in the last 60 seconds
    try:
        res = table.query(
            KeyConditionExpression="pk = :pk AND sk >= :sk_min",
            ExpressionAttributeValues={
                ":pk": "ACTIVE_INCIDENTS",
                ":sk_min": f"INC#{window_start}"
            },
            Limit=15
        )
        for item in res.get("Items", []):
            i_lat = float(item.get("lat", 0.0))
            i_lon = float(item.get("lon", 0.0))
            i_class = item.get("class_label", "")

            if i_class == class_label:
                dist = _haversine_distance_meters(lat, lon, i_lat, i_lon)
                if dist <= GEO_CLUSTER_RADIUS_METERS:
                    inc_id = item.get("incident_id")
                    devices = set(item.get("devices", []))
                    devices.add(device_id)

                    # Update incident cluster with latest device
                    table.update_item(
                        Key={"pk": "ACTIVE_INCIDENTS", "sk": item["sk"]},
                        UpdateExpression="SET devices = :d, #upd = :now",
                        ExpressionAttributeNames={"#upd": "updated_at"},
                        ExpressionAttributeValues={
                            ":d": list(devices),
                            ":now": now_ms
                        }
                    )
                    logger.info(f"Correlated into existing incident {inc_id} with {len(devices)} cameras (dist={dist:.1f}m)")
                    return inc_id, list(devices)

    except Exception as e:
        logger.warning(f"Geo-correlation query failed: {e}")

    # No existing incident cluster found — initialize new incident
    new_incident_id = f"INC-{class_label[:4].upper()}-{str(now_ms)[-6:]}"
    try:
        table.put_item(
            Item={
                "pk": "ACTIVE_INCIDENTS",
                "sk": f"INC#{now_ms}#{new_incident_id}",
                "incident_id": new_incident_id,
                "class_label": class_label,
                "lat": str(lat),
                "lon": str(lon),
                "devices": [device_id],
                "created_at": now_ms,
                "updated_at": now_ms,
                "ttl": int(time.time()) + (24 * 3600),
            }
        )
    except Exception as e:
        logger.error(f"Failed to record new incident: {e}")

    return new_incident_id, list(corroborating)


def _compute_triage_score(class_label: str, severity: str, confidence: float, corroborating_count: int) -> int:
    """
    Compute a 1-10 triage urgency score:
    Base (1-7) + confidence bonus (0-2) + multi-camera bonus (0-2)
    """
    base_scores = {"HIGH": 7, "MEDIUM": 4, "LOW": 1}
    base = base_scores.get(severity.upper(), 1)

    conf_bonus = round(confidence * 2)

    # Multi-camera corroboration bonus (if 2 or more separate cameras see the hazard)
    multi_cam_bonus = 2 if corroborating_count >= 2 else 0

    critical_classes = {"fire", "smoke", "weapon", "explosion", "accident"}
    multiplier = 1.15 if class_label.lower() in critical_classes else 1.0

    score = int((base + conf_bonus + multi_cam_bonus) * multiplier)
    return max(1, min(10, score))


def _update_event_record(device_id: str, timestamp: int, event_id: str, triage_score: int, incident_id: str, corroborating_count: int):
    """Update original event with triage enrichments."""
    try:
        table.update_item(
            Key={
                "pk": f"DEVICE#{device_id}",
                "sk": f"EVENT#{timestamp}#{event_id}",
            },
            UpdateExpression=(
                "SET triage_score = :ts, incident_id = :inc, "
                "corroborating_cams = :cc, #st = :status, triaged_at = :ta"
            ),
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":ts": triage_score,
                ":inc": incident_id,
                ":cc": corroborating_count,
                ":status": "triaged",
                ":ta": int(time.time() * 1000),
            }
        )
    except Exception as e:
        logger.error(f"Failed to update event record: {e}")


def _publish_alert(event_id, incident_id, device_id, class_label, severity, score, confidence, lat, lon, corroborating_devices, crop_s3_key):
    """Publish alert notification to SNS topic."""
    if not ALERT_TOPIC_ARN:
        return

    message = {
        "alert_type": "HAZARD_TRIAGE_ALARM",
        "event_id": event_id,
        "incident_id": incident_id,
        "device_id": device_id,
        "class_label": class_label,
        "severity": severity,
        "triage_score": score,
        "confidence": confidence,
        "lat": lat,
        "lon": lon,
        "corroborating_cameras": len(corroborating_devices),
        "crop_s3_key": crop_s3_key,
        "timestamp": int(time.time() * 1000),
        "message": (
            f"🚨 URBAN HAZARD ALARM: {class_label.upper()}\n"
            f"Incident: {incident_id} | Priority Score: {score}/10\n"
            f"Origin Camera: {device_id} | Corroborating Nodes: {len(corroborating_devices)}\n"
            f"Location: ({lat}, {lon}) | Confidence: {confidence:.1%}"
        ),
    }

    try:
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Subject=f"[AECHI ALARM {score}/10] {class_label.upper()} detected at {device_id}",
            Message=json.dumps(message, indent=2),
        )
        logger.info(f"Published alert to SNS for incident={incident_id}")
    except ClientError as e:
        logger.error(f"SNS publish failed: {e}")
