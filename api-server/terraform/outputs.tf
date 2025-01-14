# Outputs to be used by parent module

# For SSH access (without port)
output "api_endpoint" {
  description = "Public DNS of the API server"
  value       = aws_instance.api_server.public_dns
}

# For bot communication (with port)
output "api_url" {
  description = "Full API URL including port"
  value       = "${aws_instance.api_server.public_dns}:5000"
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "security_group_id" {
  description = "Security group ID of the API server"
  value       = aws_security_group.api.id
}
