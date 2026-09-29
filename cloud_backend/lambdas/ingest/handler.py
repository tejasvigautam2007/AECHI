"""
Lambda: ingest
Receives detection event batches from edge nodes via API Gateway.
Validates, enriches, and writes to DynamoDB.
Publishes to EventBridge for downstream triage processing.
"""

import json
import os
import time
import uuid
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")

TABLE_NAME = os.environ["DYNAMODB_TABLE"]
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
            _store_event(enriched)
            stored_ids.append(enriched["event_id"])
            eb_entries.append(_build_eb_entry(enriched))
        except Exception as e:
            logger.error(f"Failed to process event: {e} | raw={raw}")

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

    return {
        "event_id": str(uuid.uuid4()),
        "device_id": raw.get("device_id", device_id),
        "timestamp": int(raw["timestamp"]),
        "ingested_at": int(time.time() * 1000),
        "class_label": str(raw["class_label"]),
        "confidence": float(raw["confidence"]),
        "bbox": raw.get("bbox", []),
        "model_tier": raw.get("model_tier", "unknown"),
        "inference_ms": float(raw.get("inference_ms", 0)),
        "severity": str(raw["severity"]),
        "anon_crop_b64": raw.get("anon_crop_b64", ""),
        "ttl": int(time.time()) + (7 * 24 * 3600),  # 7-day TTL
    }


def _store_event(enriched: dict) -> None:
    """Write enriched event to DynamoDB (strip large b64 crop for main table)."""
    item = {k: v for k, v in enriched.items() if k != "anon_crop_b64"}
    item["pk"] = f"DEVICE#{enriched['device_id']}"
    item["sk"] = f"EVENT#{enriched['timestamp']}#{enriched['event_id']}"
    table.put_item(Item=item)


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
        }),
        "EventBusName": EVENT_BUS_NAME,
    }


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }
