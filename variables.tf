# infrastructure/variables.tf
variable "existing_instance_id" {
  description = "ID of the existing EC2 instance"
  type        = string
  # You'll set this in terraform.tfvars
}

variable "aws_region" {
  description = "Value of aws region"
  type        = string
  default     = "us-east-2"
}

variable "team_names" {
  description = "Value of teams using bot-platform"
  type        = string
  default     = "sandbox-bot"
}

variable "existing_security_group_id" {
  description = "Existing security group ID"
  type        = string
  # You'll set this in terraform.tfvars
}