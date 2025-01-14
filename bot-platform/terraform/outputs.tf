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
  description = "ECR Repository URLs"
  value       = {
    for name, repo in aws_ecr_repository.bot_repos : name => repo.repository_url
  }
}
output "task_execution_role_arn" {
  description = "ECS Task Execution Role ARN"
  value       = aws_iam_role.ecs_task_execution_role.arn
}