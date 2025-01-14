# bot-platform/terraform/data.tf

# Get AWS account info for ARN construction
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}