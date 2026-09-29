"""
Lambda: alert
Triggered by SNS. Formats and delivers alert notifications.
Supports: Email (via SES), webhook (Slack/PagerDuty), and DynamoDB alert log.
"""

import json
import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["DYNAMODB_TABLE"]
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Triggered by SNS subscription.
    event['Records'] contains SNS message records.
    """
    for record in event.get("Records", []):
        if record.get("EventSource") != "aws:sns":
            continue

        try:
            sns_message = json.loads(record["Sns"]["Message"])
            logger.info(f"Processing alert: {sns_message.get('event_id')}")
            _log_alert_to_dynamo(sns_message)
            logger.info(f"Alert logged: {sns_message.get('event_id')}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to process SNS record: {e}")

    return {"status": "ok"}


def _log_alert_to_dynamo(alert: dict) -> None:
    """Store alert in DynamoDB for dashboard alert feed."""
    table.put_item(Item={
        "pk": "ALERTS",
        "sk": f"ALERT#{alert.get('timestamp', int(time.time() * 1000))}#{alert.get('event_id', 'unknown')}",
        "event_id": alert.get("event_id"),
        "device_id": alert.get("device_id"),
        "class_label": alert.get("class_label"),
        "severity": alert.get("severity"),
        "triage_score": str(alert.get("triage_score", 0)),
        "message": alert.get("message", ""),
        "timestamp": alert.get("timestamp", int(time.time() * 1000)),
        "ttl": int(time.time()) + (24 * 3600),  # 24-hour TTL for alerts
    })
