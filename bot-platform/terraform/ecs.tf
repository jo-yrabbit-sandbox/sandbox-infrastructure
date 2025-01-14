# bot-platform/terraform/ecs.tf

# Task execution role already defined in main.tf
# Task role for the bots (the bot containers) to use defined in iam.tf

# Task definition template for bots
resource "aws_ecs_task_definition" "bot_task" {
  for_each = toset(var.bot_names)
  
  family                   = "${var.environment}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 256
  memory                  = 512
  task_role_arn           = aws_iam_role.bot_task_role.arn
  execution_role_arn      = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = each.key
      image = "${aws_ecr_repository.bot_repos[each.key].repository_url}:latest"
      
      environment = [
        {
          name  = "API_ENDPOINT"
          value = var.api_endpoint
        }
      ]

      secrets = [
        {
          name      = "TELEGRAM_TOKEN"
          valueFrom = aws_ssm_parameter.bot_tokens[each.key].arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.environment}/${each.key}"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# CloudWatch Log Groups for each bot
resource "aws_cloudwatch_log_group" "bot_logs" {
  for_each = toset(var.bot_names)
  
  name              = "/ecs/${var.environment}/${each.key}"
  retention_in_days = 30
}

# SSM Parameters for securely storing Telegram bot tokens
resource "aws_ssm_parameter" "bot_tokens" {
  for_each = toset(var.bot_names)
  
  name  = "/${var.environment}/bots/${each.key}/telegram-token"
  type  = "SecureString"
  value = "placeholder"  # Will be updated manually or through deployment

  lifecycle {
    ignore_changes = [value]
  }
}

# ECS Service for each bot, keeps it running
data "aws_iam_role" "ecs" {
  name = "AWSServiceRoleForECS"
}
resource "aws_ecs_service" "bot_service" {
  for_each = toset(var.bot_names)
  
  name            = "${var.environment}-${each.key}"
  cluster         = aws_ecs_cluster.bot_cluster.id
  task_definition = aws_ecs_task_definition.bot_task[each.key].arn
  desired_count   = 1  # Keep one instance running
  launch_type     = "FARGATE"
  depends_on = [data.aws_iam_role.ecs]

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}
