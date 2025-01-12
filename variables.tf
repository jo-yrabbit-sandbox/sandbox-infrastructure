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

# Local variables
locals {
  name_prefix = "${var.environment}-api"
}

# variable "existing_instance_id" {
#   description = "ID of the existing EC2 instance"
#   type        = string
#   # You'll set this in terraform.tfvars
# }
# variable "team_names" {
#   description = "Value of teams using bot-platform"
#   type        = string
#   default     = "sandbox-bot"
# }

# variable "existing_security_group_id" {
#   description = "Existing security group ID"
#   type        = string
#   # You'll set this in terraform.tfvars
# }