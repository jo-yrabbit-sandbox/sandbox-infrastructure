# bot-platform/terraform/security.tf

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
    description     = "Allow outbound to API server"
  }

  # Outbound to internet (for Telegram API)
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS outbound to internet (for Telegram API)"
  }

  # DNS resolution
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow DNS resolution"
  }

  tags = {
    Name = "${var.environment}-bot-tasks-sg"
  }
}