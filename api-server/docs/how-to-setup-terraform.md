## How to set up terraform

omg.

### Prerequisites

Assumes you have:
* Installed `terraform`
* Have a repo you're trying to deploy: `<pardir>/infrastructure`

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
```js
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

#### Create an IAM policy for Terraform State Management

1. Go to AWS Console > IAM > Policies > Create policy

2. Switch to JSON editor and paste the following content
* Replace bucket name `your-company-terraform-state` with your own bucket name
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::your-company-terraform-state"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-company-terraform-state/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:DeleteItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/terraform-state-locks"
        }
    ]
}
```

3. Name it "TerraformStateManagement". You will attach this policy to roles/users that will be running `terraform` commands in AWS.

##### (Optional) Test it locally

1. Create a new IAM user with `AdministratorAccess` for testing locally only (e.g. `terraform-user`)

2. Attach the above policy to this new user

3. Configure AWS for above new IAM user
```sh
aws configure  # set your secrets
```

4. Test the following command passes:
```sh
aws sts get-caller-identity # confirm this works
```

### Modify your Github Actions to deploy with terraform

* Follow directions in [how-to-auto-deploy-to-cloud.md](./how-to-auto-deploy-to-cloud.md)
* Then, make the following modification

#### Create Policy to allow Github Action with terraform

In addition to the policy you create during `Create Policy for EC2 and ElastiCache deployment`, create another policy that allows terraform to deploy its state files to your newly created backend s3 bucket.

1. Go to AWS Console > IAM > Policies > Create policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeImages",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeVpcAttribute",
                "ec2:DescribeTags",
                "ec2:DescribeInstanceAttribute",
                "ec2:DescribeVolumes",
                "ec2:DescribeInstanceCreditSpecifications"
            ],
            "Resource": [
                  "*"
            ]
        }
    ]
}
```
2. Name it `github-actions-my-repo-name-terraform-addons`

3. Attach this new policy to your existing Github Actions role for this repo

4. Make a commit and make sure your deploy job completes successfully