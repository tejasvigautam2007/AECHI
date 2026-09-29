"""
Lambda: dashboard
Serves events, alerts, live map telemetry, incidents, and statistics
to the React dashboard via API Gateway.
"""

import json
import os
import time
import logging
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "aechi-events-prod")
CROPS_BUCKET = os.environ.get("CROPS_BUCKET", "")

table = dynamodb.Table(TABLE_NAME)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Device-ID,x-api-key",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def lambda_handler(event, context):
    path = event.get("path", "/")
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}

    logger.info(f"Dashboard request: {method} {path}")

    if path.endswith("/events"):
        return _get_events(params)
    elif path.endswith("/alerts"):
        return _get_alerts(params)
    elif path.endswith("/stats"):
        return _get_stats(params)
    elif path.endswith("/incidents"):
        return _get_incidents(params)
    elif path.endswith("/map-events"):
        return _get_map_events(params)
    else:
        return _response(404, {"error": "Endpoint not found"})


def _get_events(params: dict) -> dict:
    """Return recent detection events across all devices."""
    limit = min(int(params.get("limit", 50)), 200)
    severity_filter = params.get("severity")

    try:
        if severity_filter:
            result = table.query(
                IndexName="severity-time-index",
                KeyConditionExpression=Key("severity").eq(severity_filter.upper()),
                ScanIndexForward=False,
                Limit=limit,
            )
        else:
            result = table.scan(
                FilterExpression="begins_with(sk, :prefix)",
                ExpressionAttributeValues={":prefix": "EVENT#"},
                Limit=limit,
            )

        items = result.get("Items", [])
        for item in items:
            item.pop("anon_crop_b64", None)
            # Generate presigned S3 URL for evidence crop if stored
            crop_key = item.get("crop_s3_key")
            if crop_key and CROPS_BUCKET:
                item["crop_url"] = _generate_presigned_url(crop_key)

        return _response(200, {"events": items, "count": len(items)})
    except Exception as e:
        logger.error(f"get_events error: {e}")
        return _response(500, {"error": "Internal server error"})


def _get_alerts(params: dict) -> dict:
    """Return recent HIGH severity alerts for alert feed widget."""
    limit = min(int(params.get("limit", 20)), 100)
    try:
        result = table.query(
            KeyConditionExpression=Key("pk").eq("ALERTS"),
            ScanIndexForward=False,
            Limit=limit,
        )
        alerts = result.get("Items", [])
        for a in alerts:
            crop_key = a.get("crop_s3_key")
            if crop_key and CROPS_BUCKET:
                a["crop_url"] = _generate_presigned_url(crop_key)

        return _response(200, {"alerts": alerts, "count": len(alerts)})
    except Exception as e:
        logger.error(f"get_alerts error: {e}")
        return _response(500, {"error": "Internal server error"})


def _get_incidents(params: dict) -> dict:
    """Return active geo-clustered multi-camera hazard incidents."""
    try:
        result = table.query(
            KeyConditionExpression=Key("pk").eq("ACTIVE_INCIDENTS"),
            ScanIndexForward=False,
            Limit=20,
        )
        return _response(200, {"incidents": result.get("Items", [])})
    except Exception as e:
        logger.error(f"get_incidents error: {e}")
        return _response(500, {"error": "Internal server error"})


def _get_map_events(params: dict) -> dict:
    """Return geolocated events with coordinates for live GIS map."""
    limit = min(int(params.get("limit", 100)), 250)
    try:
        result = table.scan(
            FilterExpression="begins_with(sk, :prefix) AND attribute_exists(lat)",
            ExpressionAttributeValues={":prefix": "EVENT#"},
            Limit=limit,
        )
        items = result.get("Items", [])
        valid_geo = []
        for it in items:
            lat = float(it.get("lat", 0.0))
            lon = float(it.get("lon", 0.0))
            if lat != 0.0 or lon != 0.0:
                crop_key = it.get("crop_s3_key")
                if crop_key and CROPS_BUCKET:
                    it["crop_url"] = _generate_presigned_url(crop_key)
                it.pop("anon_crop_b64", None)
                valid_geo.append(it)

        return _response(200, {"map_events": valid_geo, "count": len(valid_geo)})
    except Exception as e:
        logger.error(f"get_map_events error: {e}")
        return _response(500, {"error": "Internal server error"})


def _get_stats(params: dict) -> dict:
    """Return aggregate statistics for stats bar and gauge widgets."""
    now_ms = int(time.time() * 1000)
    one_hour_ago = now_ms - (60 * 60 * 1000)

    try:
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for severity in counts:
            result = table.query(
                IndexName="severity-time-index",
                KeyConditionExpression=(
                    Key("severity").eq(severity) &
                    Key("ingested_at").gte(one_hour_ago)
                ),
                Select="COUNT",
            )
            counts[severity] = result.get("Count", 0)

        return _response(200, {
            "period": "last_1h",
            "total": sum(counts.values()),
            "by_severity": counts,
            "server_time": now_ms,
        })
    except Exception as e:
        logger.error(f"get_stats error: {e}")
        return _response(500, {"error": "Internal server error"})


def _generate_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned S3 GET URL for evidence crop preview."""
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": CROPS_BUCKET, "Key": s3_key},
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        logger.warning(f"Presigned URL generation failed for {s3_key}: {e}")
        return ""


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }
