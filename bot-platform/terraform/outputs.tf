# Outputs to be used by parent module
# bot-platform/terraform/outputs.tf

output "cluster_id" {
  description = "ECS Cluster ID"
  value       = aws_ecs_cluster.bot_cluster.id
}

output "cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.bot_cluster.name
}

output "ecr_repository_urls" {
  description = "Map of bot names to their ECR repository URLs"
  value = {
    for name, repo in aws_ecr_repository.bot_repos : name => repo.repository_url
  }
}

output "bot_service_names" {
  description = "Map of bot names to their ECS service names"
  value = {
    for name, service in aws_ecs_service.bot_service : name => service.name
  }
}

output "task_execution_role_arn" {
  description = "ECS Task Execution Role ARN"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "bot_role_arns" {
  value = {
    for name, role in aws_iam_role.bot_deployment_roles : name => role.arn
  }
}