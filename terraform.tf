# infrastructure/terraform.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
  
  required_version = ">= 1.2.0"

  backend "s3" {
    bucket = "jolly-sandbox-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-2"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}

# provider "aws" {
#   region = var.aws_region
# }

module "shared" {
  source = "./shared/terraform"
}


module "api_server" {
  source = "./api-server/terraform"
  
  vpc_id            = module.shared.vpc_id
  # private_subnets   = module.shared.private_subnets
  public_subnet_ids = module.shared.public_subnet_ids
  # api_security_group = module.shared.api_security_group
}

# module "bot_platform" {
#   source = "./bot-platform/terraform"
  
#   vpc_id            = module.shared.vpc_id
#   private_subnets   = module.shared.private_subnets
#   team_names        = var.team_names
#   api_endpoint      = module.api_server.api_endpoint
# }