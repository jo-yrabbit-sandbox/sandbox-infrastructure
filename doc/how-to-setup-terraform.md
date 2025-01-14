## How to setup deployment with terraform

## Prerequisites
- AWS Account
- GitHub Account
- Terraform installed locally
- AWS CLI installed locally

## Repository Structure
```
infrastructure/
├── shared/
│   └── terraform/        # Shared infrastructure (VPC, networking)
├── api-server/
│   ├── terraform/        # API-specific infrastructure
│   ├── api/              # API application code
│   ├── requirements.txt
│   └── scripts/
│       └── deploy.sh
├── bot-platform/
│   └── terraform/        # Bot infrastructure only
└── .github/
    └── workflows/
        ├── deploy-infrastructure.yml
        └── deploy-api-server.yml
```

## Bootstrap resources

Before running Terraform, you need to manually create the resources for state management

1. Create s3 bucket for Terraform state
```sh
# Create bucket (replace ACCOUNT_ID with your AWS account ID)
aws s3api create-bucket \
    --bucket your-project-terraform-state \
    --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket your-project-terraform-state \
    --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket your-project-terraform-state \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }'

# Block all public access
aws s3api put-public-access-block \
    --bucket your-project-terraform-state \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

2. Create DynamoDB Table for State Locking
```sh
bashCopyaws dynamodb create-table \
    --table-name terraform-state-locks \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

3. Update terraform backend configuration
After creating these resources, update `shared/terraform/main.tf` to use them

```hcl
terraform {
  backend "s3" {
    bucket         = "your-project-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}
```

## Initial Setup

### 1. AWS IAM Setup
Create two roles for GitHub Actions:

#### Terraform role for infrastructure management
- Create role with Web Identity using GitHub's OIDC provider
- Attach policies:
  - TerraformStateManagement (S3 and DynamoDB access)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-project-terraform-state",
                "arn:aws:s3:::your-project-terraform-state/*"
            ]
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
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeImages",
                "ec2:DescribeInstanceAttribute",
                "ec2:DescribeInstanceCreditSpecifications",
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceTypes",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeTags",
                "ec2:DescribeVolumes",
                "ec2:DescribeVpcAttribute",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeKeyPairs",
                "ec2:CreateTags",
                "ec2:RunInstances",
                "ec2:StopInstances",
                "ec2:StartInstances",
                "ec2:ModifyInstanceAttribute"
            ],
            "Resource": "*"
        }
    ]
}
```
  - TerraformEC2Management (EC2 and networking resources)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVpcs",
                "ec2:DescribeSubnets",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeTags",
                "ec2:DescribeAddresses",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DescribeInternetGateways",
                "ec2:DescribeNatGateways",
                "ec2:DescribeRouteTables",
                "ec2:CreateSecurityGroup",
                "ec2:DeleteSecurityGroup",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupEgress",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:AuthorizeSecurityGroupEgress"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:ModifyInstanceAttribute",
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:StartInstances",
                "ec2:StopInstances"
            ],
            "Resource": [
                "arn:aws:ec2:*:*:instance/*",
                "arn:aws:ec2:*:*:volume/*",
                "arn:aws:ec2:*:*:network-interface/*",
                "arn:aws:ec2:*:*:subnet/*",
                "arn:aws:ec2:*:*:security-group/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateTags"
            ],
            "Resource": [
                "arn:aws:ec2:*:*:instance/*",
                "arn:aws:ec2:*:*:volume/*"
            ]
        }
    ]
}
```
  - TerraformElastiCacheManagement (Redis cluster management)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "elasticache:CreateCacheCluster",
                "elasticache:DeleteCacheCluster",
                "elasticache:DescribeCacheClusters",
                "elasticache:ModifyCacheCluster",
                "elasticache:CreateCacheParameterGroup",
                "elasticache:DeleteCacheParameterGroup",
                "elasticache:DescribeCacheParameterGroups",
                "elasticache:ModifyCacheParameterGroup",
                "elasticache:CreateCacheSubnetGroup",
                "elasticache:DeleteCacheSubnetGroup",
                "elasticache:DescribeCacheSubnetGroups",
                "elasticache:ModifyCacheSubnetGroup",
                "elasticache:DescribeCacheParameters",
                "elasticache:ListTagsForResource",
                "elasticache:AddTagsToResource"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Deployer Role (Application Deployment)
Create role with Web Identity using GitHub's OIDC provider
1. Go to AWS Console > IAM > Identity providers > Add provider
2. For the provider configuration:
    * Select "OpenID Connect"
    * For Provider URL, enter: https://token.actions.githubusercontent.com
    * For Audience, enter: sts.amazonaws.com
    * Click "Add provider"
3. Note the GitHub OIDC provider to use for later. This is the base OIDC configuration. Later when creating a new role for your repo, you will be asked to select this base OIDC configuration and then make further adjustments (such as the Audience for this provider/repo name).
4. Attach policy:
  - EC2DeploymentOperations (EC2 instance access and security group modifications)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeSecurityGroups"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress"
            ],
            "Resource": "arn:aws:ec2:*:*:security-group/sg-abc123"
        }
    ]
}
```

### 2. GitHub Repository Secrets
1. Go to your repo in Github > Settings > (left column) Secrets and variables > Actions
2. Set up the following secrets in your repository:
```
# Infrastructure Management
TERRAFORM_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/terraform-role"
AWS_REGION="us-east-1"
ALLOWED_IP="your-ip-address"  # To restrict SSH access to EC2 instance
ENVIRONMENT="production"  # Becomes name prefix for many AWS resources ("sandbox", "production")

# Deployment
DEPLOY_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/deployer-role"
EC2_USERNAME="ubuntu"
EC2_SSH_KEY="your-private-key-content"
REDIS_HOST="your-elasticache-endpoint"  # Will be available after infrastructure creation
```

## Deployment Process

### 1. Infrastructure Deployment
The infrastructure workflow (`deploy-infrastructure.yml`) runs when:
- Changes are made to Terraform files
- Manually triggered through GitHub Actions UI

This creates:
- VPC with public/private subnets
- EC2 instance for API server
- ElastiCache Redis cluster
- Security groups and networking

### 2. API Server Deployment
The API deployment workflow (`deploy-api-server.yml`) runs when:
- Changes are made to API code or deployment scripts
- Manually triggered through GitHub Actions UI

This:
- Gets infrastructure outputs from Terraform
- Connects to EC2 instance
- Deploys updated application code

## Important Notes

### Security Groups
- API Server (EC2) security group allows:
  - SSH (port 22) from ALLOWED_IP (github repo secret) only
  - HTTP (port 80)
  - API traffic (port 5000)
  - Outbound to Redis (port 6379)

- Redis security group allows:
  - Inbound from API security group on port 6379

### Networking
- API server runs in public subnet
- Redis cluster runs in private subnet
- NAT Gateway enables private subnet internet access

### Application Configuration
- Redis connection uses ElastiCache endpoint
- Environment variables passed through systemd service
- Application logs available through journalctl

## Troubleshooting

### Common Issues
1. Redis Connection:
   - Verify security group rules
   - Check Redis endpoint in environment variables
   - Confirm correct port number (6379)

2. Deployment Failures:
   - Check GitHub Actions logs
   - Verify SSH key access
   - Review systemd service logs

### Useful Commands
```bash
# Check API server status
sudo systemctl status api-server

# View application logs
sudo journalctl -u api-server -f

# Test Redis connection
nc -zv REDIS_ENDPOINT 6379

# Check security group rules
aws ec2 describe-security-groups --group-ids YOUR_SG_ID
```