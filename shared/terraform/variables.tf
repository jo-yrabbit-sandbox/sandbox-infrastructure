# infrastructure/variables.tf
variable "aws_region" {
  description = "Value of aws region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "sandbox"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "allowed_ip" {
  description = "IP address allowed for SSH access"
  type        = string
  default     = "0.0.0.0"
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
  default     = "tee-gee-bots"
}

locals {
  name_prefix_api = "${var.environment}-api"
}