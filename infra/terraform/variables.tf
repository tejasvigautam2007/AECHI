variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "ap-south-1"
}

variable "stage" {
  description = "Environment stage (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "alert_email" {
  description = "Email address for high severity alerts"
  type        = string
  default     = ""
}

variable "webhook_url" {
  description = "Slack or PagerDuty webhook URL"
  type        = string
  default     = ""
}
