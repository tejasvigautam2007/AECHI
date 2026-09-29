terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = "AECHI"
      Stage     = var.stage
      ManagedBy = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

# ─────────────────────────────────────────
# DynamoDB Table
# ─────────────────────────────────────────
resource "aws_dynamodb_table" "events" {
  name         = "aechi-events-${var.stage}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "severity"
    type = "S"
  }
  attribute {
    name = "ingested_at"
    type = "N"
  }

  global_secondary_index {
    name            = "severity-time-index"
    hash_key        = "severity"
    range_key       = "ingested_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
}

# ─────────────────────────────────────────
# S3 Bucket for Anonymized Evidence Crops
# ─────────────────────────────────────────
resource "aws_s3_bucket" "crops" {
  bucket = "aechi-crops-${var.stage}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "crops" {
  bucket = aws_s3_bucket.crops.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "crops" {
  bucket = aws_s3_bucket.crops.id

  rule {
    id     = "auto-delete-crops-30d"
    status = "Enabled"

    expiration {
      days = 30
    }
  }
}

# ─────────────────────────────────────────
# EventBridge Custom Bus
# ─────────────────────────────────────────
resource "aws_cloudwatch_event_bus" "hazard_bus" {
  name = "aechi-hazard-bus-${var.stage}"
}

# ─────────────────────────────────────────
# SNS Alert Topic
# ─────────────────────────────────────────
resource "aws_sns_topic" "alerts" {
  name         = "aechi-alerts-${var.stage}"
  display_name = "AECHI Hazard Alerts"
}
