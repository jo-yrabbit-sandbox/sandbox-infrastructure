## How to set up terraform

omg.

### Prerequisites

Assumes you have:
* Installed `terraform`
* Have a repo you're trying to deploy: `<pardir>/infrastructure`

#### Create an IAM user that has admin privileges (TODO: make user role more secure later)
* Test your permissions
```sh
aws configure  # set your secrets
aws sts get-caller-identity # confirm this works
```
* Create .env file
```sh
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-2"
```

#### Create a backend s3 bucket to keep terraform state

1. Set up a new directory just for s3 setup
```sh
mkdir backend-setup
cd backend-setup
```

2. Create `main.tf`
* Change the aws `region` and `bucket` name
* Make sure bucket name is unique
```sh
# First, create the backend resources using this configuration
# backend-setup/main.tf

provider "aws" {
  region = "us-east-1"  # Change this to your desired region
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "your-company-terraform-state"  # Change this to your desired bucket name
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-state-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

output "s3_bucket_name" {
  value = aws_s3_bucket.terraform_state.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.terraform_locks.id
}
```

3. Create the resources
```sh
terraform init
terraform apply
```

#### Modify infrastructure to use that s3 bucket

1. Go back to your repo `cd ../infrastructure` and modify main `terraform.tf` to use the new s3 bucket
```sh
# infrastructure/terraform.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "your-company-terraform-state"  # Same as bucket name above
    region         = "us-east-1"  # Set your region to same region for bucket
    key            = "infrastructure/terraform.tfstate"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}
```

2. Confirm it works
```sh
terraform init
terraform plan
```