# outputs.tf
output "api_server_endpoint" {
  description = "Public DNS of the API server"
  value       = aws_instance.api_server.public_dns
}

output "api_server_security_group_id" {
  description = "Security group ID of the API server"
  value       = aws_security_group.api.id
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_cluster.redis.port
}