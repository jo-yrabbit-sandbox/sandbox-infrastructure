# infrastructure/api-server/terraform/variables.tf
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "existing_security_group_id" {
  description = "Existing security group ID"
  type        = string
  default     = "sg-00dabfbfb3954248d"
}

variable "vpc_id" {
  description = "VPC ID from shared module"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs from shared module"
  type        = list(string)
}