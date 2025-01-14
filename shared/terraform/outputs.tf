# shared/terraform/outputs.tf
output "api_server_endpoint" {
  description = "Public DNS of the API server"
  value       = module.api_server.api_endpoint
}

output "api_server_security_group_id" {
  description = "Security group ID of the API server"
  value       = module.api_server.security_group_id
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.api_server.redis_endpoint
}

output "bot_cluster_name" {
  value = module.bot_platform.cluster_name
}

output "bot_ecr_repository_urls" {
  value = module.bot_platform.ecr_repository_urls
}