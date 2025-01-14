# security.tf

resource "aws_security_group" "api" {
  name        = "${local.name_prefix_api}-sg"
  description = "Security group for API server"
  vpc_id      = var.vpc_id

  # Allow ICMP (pings only)
  ingress {
  from_port        = 8  # ICMP Echo Request
  to_port          = 0  # ICMP Echo Request subtype
  protocol         = "icmp"
  cidr_blocks      = ["${var.allowed_ip}/32"]
  }

  # SSH access for deployment
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${var.allowed_ip}/32"]
  }

  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # API server port 5000
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Allow public access
  }

  # Redis access (only from private subnets)
  ingress {
    from_port = 6379
    to_port   = 6379
    protocol  = "tcp"
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix_api}-sg"
  }
}

# Redis security group
resource "aws_security_group" "redis" {
  name        = "${local.name_prefix_api}-redis-sg"
  description = "Security group for Redis cluster"
  vpc_id      = var.vpc_id

  # Redis port access (only from API server)
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix_api}-redis-sg"
  }
}