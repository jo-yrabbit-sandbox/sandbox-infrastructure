# infrastructure/bot-platform/terraform/main.tf

# ECS Cluster
resource "aws_ecs_cluster" "bot_cluster" {
  name = "${var.environment}-telegram-bot-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.environment}-bot-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECR Repository for each bot
resource "aws_ecr_repository" "bot_repos" {
  for_each = toset(var.bot_names)

  name = "${var.environment}-${each.key}"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.environment}-${each.key}"
  }
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.environment}-bot-tasks-sg"
  description = "Security group for bot ECS tasks"
  vpc_id      = var.vpc_id

  # Outbound to API Server
  egress {
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [var.api_security_group_id]
  }

  # General outbound access (for Telegram API)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-bot-tasks-sg"
  }
}