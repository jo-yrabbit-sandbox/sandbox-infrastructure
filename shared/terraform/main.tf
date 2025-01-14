# infrastructure/shared/terraform/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "jolly-sandbox-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Managed_by  = "terraform"
    }
  }
}

# Call the API server module
module "api_server" {
  source = "../../api-server/terraform"
  
  vpc_id               = aws_vpc.main.id
  public_subnet_ids    = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  private_subnet_ids   = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  private_subnet_cidrs = [aws_subnet.private_1.cidr_block, aws_subnet.private_2.cidr_block]
  environment          = var.environment
  allowed_ip           = var.allowed_ip
}

module "bot_platform" {
  source = "../../bot-platform/terraform"
  
  environment          = var.environment
  vpc_id              = aws_vpc.main.id
  private_subnet_ids  = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  api_security_group_id = module.api_server.security_group_id
}