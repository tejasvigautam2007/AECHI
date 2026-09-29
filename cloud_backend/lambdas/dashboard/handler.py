"""
Lambda: dashboard
Serves recent events, alerts, and stats to the React dashboard via API Gateway.
"""

import json
import os
import time
import logging
import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["DYNAMODB_TABLE"]
table = dynamodb.Table(TABLE_NAME)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Device-ID",
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
    else:
        return _response(404, {"error": "Not found"})


def _get_events(params: dict) -> dict:
    """Return recent detection events across all devices."""
    limit = min(int(params.get("limit", 50)), 200)
    severity_filter = params.get("severity")  # HIGH | MEDIUM | LOW

    try:
        if severity_filter:
            result = table.query(
                IndexName="severity-time-index",
                KeyConditionExpression=Key("severity").eq(severity_filter.upper()),
                ScanIndexForward=False,  # newest first
                Limit=limit,
            )
        else:
            # Scan recent events (demo-scale — add pagination for prod)
            result = table.scan(
                FilterExpression="begins_with(sk, :prefix)",
                ExpressionAttributeValues={":prefix": "EVENT#"},
                Limit=limit,
            )

        items = result.get("Items", [])
        # Remove large base64 crops from response
        for item in items:
            item.pop("anon_crop_b64", None)

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
        return _response(200, {"alerts": result.get("Items", [])})
    except Exception as e:
        logger.error(f"get_alerts error: {e}")
        return _response(500, {"error": "Internal server error"})


def _get_stats(params: dict) -> dict:
    """Return aggregate statistics for stats bar widget."""
    now_ms = int(time.time() * 1000)
    one_hour_ago = now_ms - (60 * 60 * 1000)

    try:
        # Count by severity using GSI
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


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }
