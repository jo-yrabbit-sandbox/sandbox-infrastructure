# bot-platform/terraform/variables.tf
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "api_security_group_id" {
  description = "Security Group ID of the API server"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "bot_names" {
  description = "List of bot names to create repositories for"
  type        = list(string)
  default     = ["test-bot"]  # Default for testing
}

variable "api_endpoint" {
  description = "API Server endpoint with port"
  type        = string
}