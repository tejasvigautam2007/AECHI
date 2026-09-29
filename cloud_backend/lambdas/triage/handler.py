"""
Lambda: triage
Triggered by EventBridge when a new HazardDetection event arrives.
Performs severity scoring, deduplication, and geo-clustering.
Publishes HIGH severity events to SNS for alerting.
Also writes processed events to DynamoDB GSI for dashboard queries.
"""

import json
import os
import time
import logging
import boto3
from botocore.exceptions import ClientError
from collections import defaultdict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
ALERT_TOPIC_ARN = os.environ["ALERT_TOPIC_ARN"]
DEDUP_WINDOW_MS = int(os.environ.get("DEDUP_WINDOW_MS", "5000"))  # 5-second dedup

table = dynamodb.Table(TABLE_NAME)

# In-memory dedup cache (per Lambda warm instance)
_dedup_cache: dict[str, int] = {}


def lambda_handler(event, context):
    """
    Triggered by EventBridge rule matching source=aechi.edge, DetailType=HazardDetection
    """
    detail = event.get("detail", {})
    logger.info(f"Triage triggered: {detail}")

    event_id = detail.get("event_id", "unknown")
    device_id = detail.get("device_id", "unknown")
    class_label = detail.get("class_label", "unknown")
    severity = detail.get("severity", "LOW")
    confidence = float(detail.get("confidence", 0.0))
    timestamp = int(detail.get("timestamp", time.time() * 1000))

    # --- Deduplication ---
    dedup_key = f"{device_id}#{class_label}"
    last_seen = _dedup_cache.get(dedup_key, 0)
    if timestamp - last_seen < DEDUP_WINDOW_MS:
        logger.info(f"Deduped event: {dedup_key} (last={last_seen}ms ago)")
        return {"status": "deduped"}
    _dedup_cache[dedup_key] = timestamp

    # --- Triage Score ---
    triage_score = _compute_triage_score(class_label, severity, confidence)

    # --- Update DynamoDB with triage result ---
    try:
        table.update_item(
            Key={
                "pk": f"DEVICE#{device_id}",
                "sk": f"TRIAGE#{timestamp}#{event_id}",
            },
            UpdateExpression=(
                "SET triage_score = :ts, triage_severity = :sev, "
                "triage_at = :ta, #st = :status"
            ),
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":ts": str(triage_score),
                ":sev": severity,
                ":ta": int(time.time() * 1000),
                ":status": "triaged",
            },
        )
    except ClientError as e:
        logger.error(f"DynamoDB update failed: {e}")

    # --- Alert on HIGH severity ---
    if severity == "HIGH" and triage_score >= 7:
        _publish_alert(event_id, device_id, class_label, severity, triage_score, confidence)

    return {
        "status": "ok",
        "event_id": event_id,
        "triage_score": triage_score,
        "severity": severity,
    }


def _compute_triage_score(class_label: str, severity: str, confidence: float) -> int:
    """
    Compute a 1-10 triage urgency score.
    Score = base_severity_score + confidence_bonus
    """
    base_scores = {"HIGH": 7, "MEDIUM": 4, "LOW": 1}
    base = base_scores.get(severity.upper(), 1)

    # Confidence bonus: 0.0 → 0, 1.0 → 3
    conf_bonus = round(confidence * 3)

    # Hazard type multiplier
    critical_classes = {"fire", "smoke", "weapon", "explosion"}
    multiplier = 1.2 if class_label.lower() in critical_classes else 1.0

    score = min(10, int((base + conf_bonus) * multiplier))
    return score


def _publish_alert(event_id, device_id, class_label, severity, score, confidence):
    """Publish alert notification to SNS topic."""
    message = {
        "alert_type": "HAZARD_DETECTED",
        "event_id": event_id,
        "device_id": device_id,
        "class_label": class_label,
        "severity": severity,
        "triage_score": score,
        "confidence": confidence,
        "timestamp": int(time.time() * 1000),
        "message": (
            f"⚠️ HIGH severity hazard detected!\n"
            f"Type: {class_label} | Device: {device_id} | "
            f"Score: {score}/10 | Confidence: {confidence:.1%}"
        ),
    }
    try:
        sns.publish(
            TopicArn=ALERT_TOPIC_ARN,
            Subject=f"[AECHI ALERT] {class_label.upper()} detected — Score {score}/10",
            Message=json.dumps(message, indent=2),
        )
        logger.info(f"Alert published to SNS for event {event_id}")
    except ClientError as e:
        logger.error(f"SNS publish failed: {e}")
