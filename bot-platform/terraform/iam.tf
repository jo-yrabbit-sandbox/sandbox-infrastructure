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
        Resource = flatten([
          for bot_name in keys(var.bot_configs) :
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${var.environment}/bots/${bot_name}/*"
        ])
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
        Resource = flatten([
          for bot_name in keys(var.bot_configs) :
          "${aws_cloudwatch_log_group.bot_logs[bot_name].arn}:*"
        ])
      }
    ]
  })
}

# 3. Bot deployment role for each bot
resource "aws_iam_role" "bot_deployment_roles" {
  for_each = var.bot_configs

  name = "bot-deployment-${each.key}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${each.value.github_org}/${each.key}:*"
          }
        }
      }
    ]
  })
}

# Create policy for each bot
resource "aws_iam_role_policy" "bot_deployment_policies" {
  for_each = var.bot_configs
  name     = "bot-deployment-policy-${each.key}"
  role     = aws_iam_role.bot_deployment_roles[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Resource = [
          "arn:aws:ecr:*:${data.aws_caller_identity.current.account_id}:repository/${var.environment}-${each.key}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService"
        ]
        Resource = [
          "arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:service/${var.environment}-telegram-bot-cluster/${var.environment}-${each.key}"
        ]
      },
      {
        "Effect": "Allow",
        "Action": [
          "ssm:PutParameter"
        ],
        "Resource": [
          "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/${var.environment}/bots/${each.key}/*"
        ]
      }
    ]
  })
}
