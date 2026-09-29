output "dynamodb_table_name" {
  description = "Name of the DynamoDB telemetry table"
  value       = aws_dynamodb_table.events.name
}

output "crops_bucket_name" {
  description = "Name of the S3 anonymized evidence bucket"
  value       = aws_s3_bucket.crops.id
}

output "event_bus_name" {
  description = "Name of the custom EventBridge hazard bus"
  value       = aws_cloudwatch_event_bus.hazard_bus.name
}

output "alert_topic_arn" {
  description = "ARN of the SNS hazard alert topic"
  value       = aws_sns_topic.alerts.arn
}
