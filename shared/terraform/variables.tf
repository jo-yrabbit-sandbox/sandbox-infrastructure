# infrastructure/shared/terraform/variables.tf
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "existing_vpc_id" {
  description = "Existing VPC ID"
  type        = string
  default     = "vpc-09c0020a4fdedf318"
}

variable "existing_public_subnet_ids" {
  description = "Existing public subnet IDs"
  type        = list(string)
  default     = ["subnet-006b35601869ac401", "subnet-095bcd8bd03445693"]
}