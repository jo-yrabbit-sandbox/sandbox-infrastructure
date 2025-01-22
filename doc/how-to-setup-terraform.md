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
        ├── deploy-infrastructure.yml  # Creates resources for infrastructure (API and bot)
        ├── deploy-api-server.yml      # Deploys API application to infrastructure
        └── reusable-bot-deploy.yml    # External bot devs will reuse this template to deploy
```

## Bootstrap resources

Before running Terraform, you need to manually create your resources for terraform state management

1. Create s3 bucket for Terraform state
```sh
# Create bucket (replace ACCOUNT_ID with your AWS account ID)
aws s3api create-bucket \
    --bucket your-project-terraform-state \
    --region us-east-2

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
    --region us-east-2
```

3. Update terraform backend configuration
After creating these resources, update `shared/terraform/main.tf` to use them

```hcl
terraform {
  backend "s3" {
    bucket         = "your-project-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-2"
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}
```

## Initial Setup

### 1. AWS IAM Setup

#### Create a base "Identity provider"
This will be used as the starting point for all roles created in this sectoin.
It is a generic setup which allows us to use Github Actions.
Later, when creating new roles for different repos/deployment workflows, we will reference this "Identity provider" then add customizations such as the "Audience" and specific "Organization/Repo name".

1. Go to AWS Console > IAM > Identity providers > Add provider
2. For the provider configuration:
    * Select "OpenID Connect"
    * For Provider URL, enter: https://token.actions.githubusercontent.com
    * For Audience, enter: sts.amazonaws.com
    * Click "Add provider"
3. Note the GitHub OIDC provider to use for later. This is the base OIDC configuration.


#### Create two roles for GitHub Actions:

Using the above Github OIDC provider, create two roles for your two deployment jobs
1. Terraformer role
2. Deployer role

##### 1. Terraformer role for infrastructure management

1. Create role `infrastructure-terraformer` with Web Identity using GitHub's OIDC provider
2. Attach the following policies:

- TerraformStateManagement (S3 and DynamoDB access)
    - Make sure to use the bucket names you created during previous bootstrap step
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"dynamodb:PutItem",
				"dynamodb:DescribeTable",
				"dynamodb:DeleteItem",
				"dynamodb:GetItem"
			],
			"Resource": "arn:aws:dynamodb:*:*:table/terraform-state-locks"
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"ec2:DescribeInstances",
				"ec2:DescribeTags",
				"ec2:CreateTags",
				"ec2:DescribeInstanceAttribute",
				"ec2:RunInstances",
				"ec2:StopInstances",
				"ec2:DescribeVpcAttribute",
				"ec2:DescribeInstanceCreditSpecifications",
				"ec2:DescribeSecurityGroups",
				"ec2:DescribeImages",
				"ec2:StartInstances",
				"ec2:DescribeVpcs",
				"ec2:DescribeVolumes",
				"ec2:DescribeInstanceTypes",
				"ec2:ModifyInstanceAttribute",
				"ec2:DescribeSubnets",
				"ec2:DescribeKeyPairs"
			],
			"Resource": "*"
		},
		{
			"Sid": "VisualEditor2",
			"Effect": "Allow",
			"Action": [
				"s3:PutObject",
				"s3:GetObject",
				"s3:ListBucket",
				"s3:DeleteObject"
			],
			"Resource": [
				"arn:aws:s3:::your-project-terraform-state/*",
				"arn:aws:s3:::your-project-terraform-state"
			]
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
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"ec2:AuthorizeSecurityGroupEgress",
				"ec2:AuthorizeSecurityGroupIngress",
				"ec2:DescribeAddresses",
				"ec2:DescribeInstances",
				"ec2:DescribeTags",
				"ec2:DescribeNatGateways",
				"ec2:DescribeSecurityGroups",
				"ec2:RevokeSecurityGroupIngress",
				"ec2:DescribeInternetGateways",
				"ec2:DescribeSecurityGroupRules",
				"ec2:DescribeNetworkInterfaces",
				"ec2:DescribeAvailabilityZones",
				"ec2:DescribeVpcs",
				"ec2:CreateSecurityGroup",
				"ec2:RevokeSecurityGroupEgress",
				"ec2:DeleteSecurityGroup",
				"ec2:DescribeSubnets",
				"ec2:DescribeRouteTables"
			],
			"Resource": "*"
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"ec2:ModifyVolume",
				"ec2:TerminateInstances",
				"ec2:StartInstances",
				"ec2:RunInstances",
				"ec2:ModifyInstanceAttribute",
				"ec2:StopInstances"
			],
			"Resource": [
				"arn:aws:ec2:*:*:subnet/*",
				"arn:aws:ec2:*:*:instance/*",
				"arn:aws:ec2:*:*:volume/*",
				"arn:aws:ec2:*:*:security-group/*",
				"arn:aws:ec2:*:*:network-interface/*"
			]
		},
		{
			"Sid": "VisualEditor2",
			"Effect": "Allow",
			"Action": "ec2:CreateTags",
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
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"elasticache:DescribeCacheParameters",
				"elasticache:DeleteCacheCluster",
				"elasticache:AddTagsToResource",
				"elasticache:DescribeCacheSubnetGroups",
				"elasticache:CreateCacheSubnetGroup",
				"elasticache:ModifyCacheParameterGroup",
				"elasticache:ModifyCacheCluster",
				"elasticache:DescribeCacheParameterGroups",
				"elasticache:CreateCacheParameterGroup",
				"elasticache:DeleteCacheParameterGroup",
				"elasticache:DescribeCacheClusters",
				"elasticache:CreateCacheCluster",
				"elasticache:DeleteCacheSubnetGroup",
				"elasticache:ListTagsForResource",
				"elasticache:ModifyCacheSubnetGroup"
			],
			"Resource": "*"
		}
	]
}
```

- TerraformECSManagement (Bot service ECR/ECS management)
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"ecr:PutLifecyclePolicy",
				"ecr:CreateRepository",
				"ecr:PutImageScanningConfiguration",
				"ecr:TagResource",
				"ecr:DescribeRepositories",
				"ecr:ListTagsForResource",
				"ecr:ListImages",
				"ecr:DeleteLifecyclePolicy",
				"ecr:DeleteRepository",
				"ecr:GetLifecyclePolicy"
			],
			"Resource": [
				"arn:aws:ecr:*:*:repository/sandbox-*",
				"arn:aws:ecr:*:*:repository/production-*"
			]
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"ecs:DeregisterTaskDefinition",
				"ecs:UpdateService",
				"ecs:CreateService",
				"ecs:CreateCluster",
				"ecs:RegisterTaskDefinition",
				"ecs:DeleteService",
				"ecs:DeleteCluster",
				"ecs:DescribeServices",
				"ecs:TagResource",
				"ecs:ListTaskDefinitions",
				"ecs:DescribeTaskDefinition",
				"ecs:DescribeClusters"
			],
			"Resource": "*"
		}
	]
}
```

- TerraformSSMManagement (Store bot telegram token on SSM)
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": "ssm:DescribeParameters",
			"Resource": "*"
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"ssm:PutParameter",
				"ssm:DeleteParameter",
				"ssm:RemoveTagsFromResource",
				"ssm:AddTagsToResource",
				"ssm:ListTagsForResource",
				"ssm:GetParameters",
				"ssm:GetParameter"
			],
			"Resource": [
				"arn:aws:ssm:*:*:parameter/sandbox/bots/*",
				"arn:aws:ssm:*:*:parameter/production/bots/*"
			]
		}
	]
}
```

- TerraformIAMManagement (Automate IAM role management)
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"iam:GetRole",
				"iam:UntagRole",
				"iam:TagRole",
				"iam:CreateRole",
				"iam:DeleteRole",
				"iam:AttachRolePolicy",
				"iam:PutRolePolicy",
				"iam:ListInstanceProfilesForRole",
				"iam:GetServiceLinkedRoleDeletionStatus",
				"iam:PassRole",
				"iam:CreateServiceLinkedRole",
				"iam:DetachRolePolicy",
				"iam:ListAttachedRolePolicies",
				"iam:DeleteRolePolicy",
				"iam:DeleteServiceLinkedRole",
				"iam:ListRolePolicies",
				"iam:GetRolePolicy"
			],
			"Resource": [
				"arn:aws:iam::*:role/sandbox-bot-*",
				"arn:aws:iam::*:role/production-bot-*",
				"arn:aws:iam::*:role/sandbox-*-execution-role",
				"arn:aws:iam::*:role/production-*-execution-role",
				"arn:aws:iam::*:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS",
				"arn:aws:iam::*:role/bot-deployment-*"
			]
		}
	]
}
```

- TerraformCloudWatchManagement (Bot log management)
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"logs:ListTagsLogGroup",
				"logs:DescribeLogGroups"
			],
			"Resource": "*"
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"logs:TagLogGroup",
				"logs:UntagLogGroup",
				"logs:DeleteLogGroup",
				"logs:DeleteRetentionPolicy",
				"logs:PutRetentionPolicy",
				"logs:CreateLogGroup"
			],
			"Resource": [
				"arn:aws:logs:*:*:log-group:/ecs/sandbox/*",
				"arn:aws:logs:*:*:log-group:/ecs/production/*"
			]
		}
	]
}
```

##### 2. Deployer Role for API application deployment to EC2

1. Create role `infrastructure-deployer` with Web Identity using GitHub's OIDC provider
2. Attach the following policies:

  - EC2DeploymentOperations (EC2 instance access and security group modifications)
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "VisualEditor0",
			"Effect": "Allow",
			"Action": [
				"ec2:DescribeInstances",
				"ec2:DescribeSecurityGroups"
			],
			"Resource": "*"
		},
		{
			"Sid": "VisualEditor1",
			"Effect": "Allow",
			"Action": [
				"ec2:RevokeSecurityGroupIngress",
				"ec2:AuthorizeSecurityGroupIngress"
			],
			"Resource": "arn:aws:ec2:*:*:security-group/sg-abc123"
		},
		{
			"Sid": "VisualEditor2",
			"Effect": "Allow",
			"Action": "ecr:GetAuthorizationToken",
			"Resource": "*"
		}
	]
}
```

### 2. Register GitHub Repository Secrets

1. Go to your repo in Github > Settings > (left column) Secrets and variables > Actions
2. Set up the following secrets in your repository:

```
# Organization-level secret
AWS_REGION="us-east-2"

# Repo-level secret (Infrastructure Management)
TERRAFORM_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/terraform-role"
ALLOWED_IP="your-ip-address"  # To restrict SSH access to API server EC2 instance
ENVIRONMENT="sandbox"         # Becomes name prefix for many AWS resources ("sandbox", "production")

# Repo-level secret (Deployment)
DEPLOY_ROLE_ARN="arn:aws:iam::ACCOUNT_ID:role/deployer-role"
EC2_USERNAME="ubuntu"
EC2_SSH_KEY="your-private-key-content"
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

### 3. Bot Platform Deployment
The Bot Platform is actually a reuable workflow which runs when:
- Bot developers push changes to their own external bot repo referencing this infrastructure
- Manually triggered through Github Actions UI in bot repo, not in infrastructure (this) repo

The bots get deployed to a cookie-cutter infrastructure managed inside this mono-repo.
This allows bot developers to focus on actual bot development rather than infrastructure deployment.
Logging, network/security groups, are all managed for them, assuring proper access to this API server and infrastructure.

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