# Variables from parent module
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

variable "api_url" {
  description = "Full API URL including port"
  type        = string
}

variable "bot_configs" {
  description = "Map of bot configurations including their GitHub organizations"
  type = map(object({
    github_org = string
  }))
  # Example:
  # {
  #   "test-bot" = {
  #     github_org = "test-org"
  #   }
  #   "another-bot" = {
  #     github_org = "another-org"
  #   }
  # }
}