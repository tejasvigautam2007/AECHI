"""
Lambda: alert
Triggered by SNS subscription when a HIGH severity hazard is triaged.
Dispatches notifications to:
  - Slack / PagerDuty / Webhook endpoint (if WEBHOOK_URL is set)
  - SES Email dispatch (if ALERT_EMAIL is set)
  - DynamoDB active alert feed (for dashboard live view)
"""

import json
import os
import time
import logging
import urllib.request
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
ses = boto3.client("ses")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "aechi-events-prod")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "")

table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """
    Triggered by SNS topic subscription.
    """
    for record in event.get("Records", []):
        if record.get("EventSource") != "aws:sns":
            continue

        try:
            sns_raw = record["Sns"]["Message"]
            alert_data = json.loads(sns_raw) if isinstance(sns_raw, str) else sns_raw
            logger.info(f"Dispatching alert: incident={alert_data.get('incident_id')} event={alert_data.get('event_id')}")

            # 1. Store in DynamoDB alert feed
            _log_alert_to_dynamo(alert_data)

            # 2. Dispatch to Slack/PagerDuty webhook if configured
            if WEBHOOK_URL:
                _dispatch_webhook(alert_data)

            # 3. Dispatch SES Email if configured
            if ALERT_EMAIL and SES_SENDER_EMAIL:
                _dispatch_email(alert_data)

        except Exception as e:
            logger.error(f"Failed to process SNS alert record: {e}", exc_info=True)

    return {"status": "ok"}


def _log_alert_to_dynamo(alert: dict) -> None:
    """Store alert in DynamoDB for real-time dashboard alert widget."""
    now_ms = int(time.time() * 1000)
    ts = int(alert.get("timestamp", now_ms))
    event_id = str(alert.get("event_id", "unknown"))

    table.put_item(Item={
        "pk": "ALERTS",
        "sk": f"ALERT#{ts}#{event_id}",
        "event_id": event_id,
        "incident_id": alert.get("incident_id", ""),
        "device_id": alert.get("device_id", "unknown"),
        "class_label": alert.get("class_label", "hazard"),
        "severity": alert.get("severity", "HIGH"),
        "triage_score": str(alert.get("triage_score", "7")),
        "confidence": str(alert.get("confidence", "0.0")),
        "lat": str(alert.get("lat", "0.0")),
        "lon": str(alert.get("lon", "0.0")),
        "corroborating_cameras": int(alert.get("corroborating_cameras", 1)),
        "crop_s3_key": alert.get("crop_s3_key", ""),
        "message": alert.get("message", ""),
        "timestamp": ts,
        "ttl": int(time.time()) + (48 * 3600),  # 48-hour alert TTL
    })


def _dispatch_webhook(alert: dict) -> None:
    """Send formatted notification to Slack / Teams / PagerDuty webhook."""
    try:
        class_label = alert.get("class_label", "Hazard").upper()
        score = alert.get("triage_score", "10")
        device_id = alert.get("device_id", "N/A")
        incident_id = alert.get("incident_id", "N/A")

        payload = {
            "text": f"🚨 *[AECHI ALERT - Priority {score}/10]* {class_label} detected by `{device_id}` (Incident: `{incident_id}`)",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🚨 AECHI Critical Urban Hazard Triage ({score}/10)"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Hazard:* {class_label}"},
                        {"type": "mrkdwn", "text": f"*Severity:* {alert.get('severity', 'HIGH')}"},
                        {"type": "mrkdwn", "text": f"*Camera:* `{device_id}`"},
                        {"type": "mrkdwn", "text": f"*Location:* {alert.get('lat')}, {alert.get('lon')}"},
                        {"type": "mrkdwn", "text": f"*Corroborating Nodes:* {alert.get('corroborating_cameras', 1)}"},
                        {"type": "mrkdwn", "text": f"*Incident ID:* `{incident_id}`"},
                    ]
                }
            ]
        }

        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            logger.info(f"Webhook alert dispatched successfully (status={response.status})")

    except Exception as e:
        logger.error(f"Failed to post to webhook: {e}")


def _dispatch_email(alert: dict) -> None:
    """Send email notification via Amazon SES."""
    try:
        subject = f"[AECHI ALARM] {alert.get('class_label', 'Hazard').upper()} detected - Priority {alert.get('triage_score', 'HIGH')}/10"
        body = alert.get("message", "High urgency hazard detected.")

        ses.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [ALERT_EMAIL]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            }
        )
        logger.info(f"SES email alert dispatched to {ALERT_EMAIL}")
    except ClientError as e:
        logger.error(f"SES email sending failed: {e}")
