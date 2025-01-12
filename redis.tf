# redis.tf

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name_prefix}-redis-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "${local.name_prefix}-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.name_prefix}-redis-cluster"
  engine              = "redis"
  node_type           = "cache.t4g.micro"  # cheapest for dev/testing, but adjust based on your needs
  num_cache_nodes     = 1
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  port                = 6379
  security_group_ids  = [aws_security_group.redis.id]
  subnet_group_name   = aws_elasticache_subnet_group.redis.name

  tags = {
    Name = "${local.name_prefix}-redis"
  }
}
