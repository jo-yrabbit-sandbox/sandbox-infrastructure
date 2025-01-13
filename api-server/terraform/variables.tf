# Variables from parent module
variable "vpc_id" {
  description = "VPC ID from shared module"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs from shared module"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs from shared module"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "Private subnet cidr blocks from shared module"
  type        = list(string)
}

variable "environment" {
  description = "Environment name (e.g., sandbox, prod)"
  type        = string
}

locals {
  name_prefix = "${var.environment}-api"
}