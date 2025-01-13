# infrastructure/variables.tf
variable "aws_region" {
  description = "Value of aws region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

locals {
  name_prefix = "${var.environment}-api"
}

# variable "team_names" {
#   description = "Value of teams using bot-platform"
#   type        = string
#   default     = "sandbox-bot"
# }
