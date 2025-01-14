# infrastructure/bot-platform/terraform/iam.tf

# 1. ECS Task Execution Role
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

# Allow ECS to pull images and write logs
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow reading from SSM Parameter Store for secrets
resource "aws_iam_role_policy" "task_execution_ssm" {
  name = "${var.environment}-bot-execution-ssm-policy"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          for bot_name in var.bot_names :
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${var.environment}/bots/${bot_name}/*"
        ]
      }
    ]
  })
}

# 2. Task Role - This is used by the bot application itself
resource "aws_iam_role" "bot_task_role" {
  name = "${var.environment}-bot-task-role"

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

# Add basic permissions for bot tasks
resource "aws_iam_role_policy" "bot_task_policy" {
  name = "${var.environment}-bot-task-policy"
  role = aws_iam_role.bot_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          for bot_name in var.bot_names :
          "${aws_cloudwatch_log_group.bot_logs[bot_name].arn}:*"
        ]
      }
    ]
  })
}

# 3. ECS service-linked role
resource "aws_iam_service_linked_role" "ecs" {
  aws_service_name = "ecs.amazonaws.com"
  description      = "Role to enable Amazon ECS to manage your cluster."
}