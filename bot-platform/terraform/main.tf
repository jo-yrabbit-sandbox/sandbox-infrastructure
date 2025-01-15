# infrastructure/bot-platform/terraform/main.tf

# ECS Cluster
resource "aws_ecs_cluster" "bot_cluster" {
  name = "${var.environment}-telegram-bot-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECR Repository for each bot
resource "aws_ecr_repository" "bot_repos" {
  for_each = var.bot_configs

  name = "${var.environment}-${each.key}"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.environment}-${each.key}"
  }
}

resource "aws_security_group_rule" "api_from_bots" {
  type                     = "ingress"
  from_port               = 5000
  to_port                 = 5000
  protocol                = "tcp"
  source_security_group_id = aws_security_group.ecs_tasks.id
  security_group_id       = var.api_security_group_id
  description            = "Allow inbound from bot tasks"
}