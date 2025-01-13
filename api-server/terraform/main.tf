# api.tf
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "api_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"  # Adjust based on your needs
  subnet_id     = var.public_subnet_ids[0] # Using first public subnet
  key_name      = "sandbox-api-server"

  associate_public_ip_address = true
  vpc_security_group_ids     = [aws_security_group.api.id]

  root_block_device {
    volume_size = 20  # Adjust based on your needs
  }

  tags = {
    Name = "${local.name_prefix}-server"
  }
}