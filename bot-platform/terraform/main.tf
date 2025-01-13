# Bot ECS Service (bot-platform/terraform/main.tf)
resource "aws_ecs_cluster" "bot_cluster" {
  name = "telegram-bot-cluster"
}

resource "aws_ecs_task_definition" "bot_task" {
  family                   = "telegram-bot"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 256
  memory                  = 512

  container_definitions = jsonencode([
    {
      name  = "telegram-bot"
      image = "${var.ecr_repository_url}:latest"
      environment = [
        {
          name  = "API_ENDPOINT"
          value = "http://${aws_lb.api_lb.dns_name}"
        },
        {
          name  = "TELEGRAM_TOKEN"
          value = var.telegram_token
        }
      ]
    }
  ])
}

resource "aws_ecs_service" "bot_service" {
  name            = "telegram-bot-service"
  cluster         = aws_ecs_cluster.bot_cluster.id
  task_definition = aws_ecs_task_definition.bot_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnets
    security_groups = [aws_security_group.bot_sg.id]
  }
}