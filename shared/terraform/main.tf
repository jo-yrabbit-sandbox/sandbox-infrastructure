# infrastructure/shared/terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Reference existing VPC
data "aws_vpc" "existing" {
  id = var.existing_vpc_id
}

# Reference existing subnets
data "aws_subnet" "public" {
  count = length(var.existing_public_subnet_ids)
  id    = var.existing_public_subnet_ids[count.index]
}

# Output these for use in other modules
output "vpc_id" {
  value = data.aws_vpc.existing.id
}

output "public_subnet_ids" {
  value = [for subnet in data.aws_subnet.public : subnet.id]
}