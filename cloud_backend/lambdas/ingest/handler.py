"""
Lambda: ingest
Receives detection event batches from edge nodes via API Gateway.
Validates, stores evidence crops to S3, writes metadata to DynamoDB,
and publishes to EventBridge for downstream triage processing.
"""

import base64
import json
import os
import time
import uuid
import logging
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")
s3 = boto3.client("s3")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "aechi-events-prod")
EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")
S3_BUCKET = os.environ.get("CROPS_BUCKET", "")

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    HTTP POST /events from edge nodes.
    Body: { "device_id": str, "events": [ {...}, ... ] }
    """
    try:
        body = _parse_body(event)
    except ValueError as e:
        logger.warning(f"Bad request: {e}")
        return _response(400, {"error": str(e)})

    device_id = body.get("device_id", "unknown")
    raw_events = body.get("events", [])

    if not raw_events:
        return _response(400, {"error": "events list is empty"})

    logger.info(f"Received {len(raw_events)} events from device={device_id}")

    stored_ids = []
    eb_entries = []

    for raw in raw_events:
        try:
            enriched = _enrich_event(raw, device_id)

            # Upload evidence crop to S3 if present
            crop_b64 = raw.get("anon_crop_b64")
            crop_s3_key = None
            if crop_b64 and S3_BUCKET:
                crop_s3_key = _upload_crop_to_s3(
                    crop_b64=crop_b64,
                    device_id=enriched["device_id"],
                    event_id=enriched["event_id"]
                )
                enriched["crop_s3_key"] = crop_s3_key

            _store_event(enriched)
            stored_ids.append(enriched["event_id"])
            eb_entries.append(_build_eb_entry(enriched))
        except Exception as e:
            logger.error(f"Failed to process event: {e} | raw={raw}", exc_info=True)

    # Publish to EventBridge in batches of 10 (AWS limit)
    for i in range(0, len(eb_entries), 10):
        try:
            eventbridge.put_events(Entries=eb_entries[i:i+10])
        except ClientError as e:
            logger.error(f"EventBridge publish failed: {e}")

    return _response(200, {
        "accepted": len(stored_ids),
        "event_ids": stored_ids
    })


def _parse_body(event: dict) -> dict:
    body = event.get("body", "{}")
    if isinstance(body, str):
        return json.loads(body)
    return body or {}


def _enrich_event(raw: dict, device_id: str) -> dict:
    """Validate and enrich a single detection event."""
    required = {"timestamp", "class_label", "confidence", "severity"}
    missing = required - set(raw.keys())
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    event_id = str(uuid.uuid4())
    return {
        "event_id": event_id,
        "device_id": str(raw.get("device_id", device_id)),
        "timestamp": int(raw["timestamp"]),
        "ingested_at": int(time.time() * 1000),
        "class_label": str(raw["class_label"]),
        "confidence": float(raw["confidence"]),
        "bbox": raw.get("bbox", []),
        "model_tier": str(raw.get("model_tier", "unknown")),
        "inference_ms": float(raw.get("inference_ms", 0)),
        "severity": str(raw["severity"]).upper(),
        "lat": float(raw.get("lat", 0.0)),
        "lon": float(raw.get("lon", 0.0)),
        "status": "pending_triage",
        "ttl": int(time.time()) + (7 * 24 * 3600),  # 7-day TTL
    }


def _upload_crop_to_s3(crop_b64: str, device_id: str, event_id: str) -> str:
    """Decode base64 crop and persist in S3 Crops bucket."""
    s3_key = f"crops/{device_id}/{event_id}.jpg"
    try:
        image_bytes = base64.b64decode(crop_b64)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType="image/jpeg",
            Metadata={"device_id": device_id, "event_id": event_id}
        )
        logger.info(f"Persisted evidence crop to s3://{S3_BUCKET}/{s3_key}")
        return s3_key
    except Exception as e:
        logger.error(f"S3 crop upload error: {e}")
        return ""


def _to_decimal(val):
    """Recursively convert float to Decimal for DynamoDB serialization."""
    if isinstance(val, float):
        return Decimal(str(val))
    if isinstance(val, dict):
        return {k: _to_decimal(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_decimal(v) for v in val]
    return val


def _store_event(enriched: dict) -> None:
    """Write enriched event to DynamoDB."""
    item = dict(enriched)
    item["pk"] = f"DEVICE#{enriched['device_id']}"
    item["sk"] = f"EVENT#{enriched['timestamp']}#{enriched['event_id']}"
    table.put_item(Item=_to_decimal(item))


def _build_eb_entry(enriched: dict) -> dict:
    """Build an EventBridge PutEvents entry."""
    return {
        "Source": "aechi.edge",
        "DetailType": "HazardDetection",
        "Detail": json.dumps({
            "event_id": enriched["event_id"],
            "device_id": enriched["device_id"],
            "class_label": enriched["class_label"],
            "severity": enriched["severity"],
            "confidence": enriched["confidence"],
            "timestamp": enriched["timestamp"],
            "lat": enriched.get("lat", 0.0),
            "lon": enriched.get("lon", 0.0),
            "crop_s3_key": enriched.get("crop_s3_key", ""),
        }),
        "EventBusName": EVENT_BUS_NAME,
    }


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Device-ID,x-api-key",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body),
    }
