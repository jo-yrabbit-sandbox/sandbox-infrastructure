# api.tf
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

resource "aws_instance" "api_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"  # Adjust based on your needs
  subnet_id     = aws_subnet.public_1.id  # Using first public subnet
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