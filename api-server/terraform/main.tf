# infrastructure/api-server/terraform/main.tf
# Reference existing security group
data "aws_security_group" "existing" {
  id = var.existing_security_group_id
}

# Your existing API server configuration, modified to use shared resources
resource "aws_instance" "api_server" {
  # Keep your existing EC2 configuration
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type
  subnet_id       = var.public_subnet_ids[0] # Using first subnet by default

  vpc_security_group_ids = [data.aws_security_group.existing.id]

  tags = {
    Name = "api-server"
  }
}

# Get latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

output "api_endpoint" {
  value = aws_instance.api_server.public_dns
}


#   # Configure load balancer and auto-scaling group for API server
#   resource "aws_lb" "api_lb" {
#   name               = "api-server-lb"
#   internal           = false
#   load_balancer_type = "application"
#   security_groups    = [aws_security_group.api_sg.id]
#   subnets           = var.public_subnets
#   }

#   resource "aws_autoscaling_group" "api_asg" {
#   name                = "api-server-asg"
#   desired_capacity    = 2
#   max_size            = 4
#   min_size            = 1
#   target_group_arns   = [aws_lb_target_group.api_tg.arn]
#   vpc_zone_identifier = var.private_subnets

#   launch_template {
#       id      = aws_launch_template.api_template.id
#       version = "$Latest"
#   }
#   }

#   # Security group for API server
#   resource "aws_security_group" "api_sg" {
#   name        = "api-server-sg"
#   description = "Security group for API server"
#   vpc_id      = var.vpc_id

#   ingress {
#       from_port   = 80
#       to_port     = 80
#       protocol    = "tcp"
#       cidr_blocks = ["0.0.0.0/0"]
#   }

#   egress {
#       from_port   = 0
#       to_port     = 0
#       protocol    = "-1"
#       cidr_blocks = ["0.0.0.0/0"]
#   }
#   }
# }