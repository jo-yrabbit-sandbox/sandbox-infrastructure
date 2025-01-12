# infrastructure/terraform.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket = "jolly-sandbox-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-2"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

# module "shared" {
#   source = "./shared/terraform"
# }

# module "api_server" {
#   source = "./api-server/terraform"
  
#   vpc_id            = module.shared.vpc_id
#   # private_subnets   = module.shared.private_subnets
#   public_subnet_ids = module.shared.public_subnet_ids
#   # api_security_group = module.shared.api_security_group
# }

# Reference existing EC2 instance
data "aws_instance" "api_server" {
  filter {
    name   = "instance-id"
    values = [var.existing_instance_id]
  }
}

# Reference existing security group
data "aws_security_group" "api_server" {
  id = var.existing_security_group_id
}

# module "bot_platform" {
#   source = "./bot-platform/terraform"
  
#   vpc_id            = module.shared.vpc_id
#   private_subnets   = module.shared.private_subnets
#   team_names        = var.team_names
#   api_endpoint      = module.api_server.api_endpoint
# }

# Root level outputs
output "api_server_security_group_id" {
  description = "Security group ID of the API server"
  # value       = var.existing_security_group_id  # Use your existing security group ID here
  value       = data.aws_security_group.api_server.id
}

output "api_server_endpoint" {
  description = "Public DNS of the API server"
  # value       = module.api_server.api_endpoint
  value       = data.aws_instance.api_server.public_dns
}