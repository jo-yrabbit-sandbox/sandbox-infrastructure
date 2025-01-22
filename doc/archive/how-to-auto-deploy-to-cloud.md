## How to set up auto deployment

This is an outdated how-to for manually setting up "Github actions" for automatic deployment of the API server of the infrastructure only, in standalone.
It does not integrate the Bot platform, and has no terraform management.

This how-to is obsolete because we now use terraform to manage all AWS resources and deployment workflow.
However, this doc may help future troubleshooting/prototyping efforts, so we will leave it here, along with other archived how-tos.

### Bootstrapping steps

#### Github settings
* The repo `my-repo-name` must be part of an organization `my-organization-name` (i.e. not a personal repo)
    * Create an organization if you don't have one yet
    * Existing personal repos can be transferred to an organization as long as you are `admin`
        * Go to your repo Settings > General > Danger Zone > Transfer ownership
    * Set Workflow permissions in BOTH the organization AND repo
        * Navigate to organization > Settings > Actions (left column) > General
            * Select "Read and write permissions"
            * Check "Allow GitHub Actions to create and approve pull requests"
        * Do the same for your repo

#### AWS settings
* We assume that user has an IAM account already
* There are several ways to implement Github Actions and we will go with a "role-based" approach
    * Has 1 IAM user that is dedicated to executing Github Actions for the project (`github-actions-deployer`)
    * For each repo, create a new Role (attached to above User) that will execute the Github Action for that repo
* The alternative is a "user-based" approach that will allow 1 IAM user execute Github Actions for multiple repos, but requires sharing of same secrets and is less secure. It is easier for quick prototyping and the how-to is provided for reference.

### Steps before creating the Role

#### Create IAM root account
Skip to next part if you already have a root account.
Root account will not be directly used in your Github Actions, but it is a required first step if you're new to your IAM account. 
1. Create IAM root account (requires credit card, free during trial period). Log in to AWS Console
2. Click on your username in the top right
3. Click "Security credentials"
4. Under "Access keys", click "Create access key"
5. AWS will show you both the `Access Key ID` and `Secret Access Key`. Save them both, because this is the only time AWS will show you the Secret Access Key for your root account. You will not be using the root account for Github Actions.
6. (Optional) Download and install [AWS CLI](https://aws.amazon.com/cli/), then run `aws configure`:
    * Your `Access Key ID`
    * Your `Secret Access Key`
    * Your default region (e.g., `us-east-2`)
    * Your preferred output format (`json` is recommended)

#### Create Policy for EC2 and ElastiCache deployment
This policy will be attached to the new Role you will be creating for this repo

1. Go to IAM in AWS Console and create a new policy `github-actions-my-repo-name`
Go to AWS Console > IAM > Policies > Create policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:RebootInstances",
                "ec2:CreateTags",
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "elasticache:DescribeCacheClusters",
                "elasticache:ModifyCacheCluster",
                "elasticache:RebootCacheCluster",
                "elasticache:DescribeReplicationGroups",
                "elasticache:ModifyReplicationGroup",
                "iam:PassRole",
                "ssm:SendCommand",
                "ssm:GetCommandInvocation"
            ],
            "Resource": [
                "arn:aws:ec2:*:*:instance/*",
                "arn:aws:elasticache:*:*:cluster/*",
                "arn:aws:elasticache:*:*:replicationgroup/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "elasticache:DescribeCacheClusters",
                "elasticache:DescribeReplicationGroups",
                "ec2:DescribeInstances",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:DescribeSecurityGroups",
                "ec2-instance-connect:SendSSHPublicKey"
            ],
            "Resource": "*"
        }
    ]
}
```
2. Note `YOUR_POLICY_ARN` and policy name for next step


#### Create a new IAM user (note: not role yet)
First, create one IAM user for managing Github Actions in general
Note that User is different from Role. One user will have multiple roles under it, and your Github Actions will be executed by Roles.
1. If you don't have one already, create a new IAM user for doing the deployment
```sh
aws iam create-user --user-name github-actions-deployer
```
2. Attach the policy you created earlier to this user
```sh
aws iam attach-user-policy --user-name github-actions-deployer --policy-arn YOUR_POLICY_ARN
```

#### Create Identity provider
Create a GitHub OIDC provider to be shared across multiple roles/repos.
1. Go to AWS Console > IAM > Identity providers > Add provider
2. For the provider configuration:
    * Select "OpenID Connect"
    * For Provider URL, enter: https://token.actions.githubusercontent.com
    * For Audience, enter: sts.amazonaws.com
    * Click "Add provider"
3. Note the GitHub OIDC provider to use for later. This is the base OIDC configuration. Later when creating a new role for your repo, you will be asked to select this base OIDC configuration and then make further adjustments (such as the Audience for this provider/repo name).


### Create a new IAM role
This is the role that will be referenced by your Github Actions yaml file.
You will be creating one role per repo.

1. Go to AWS Console > IAM > Roles > Create Role
2. Under "Trusted entity type" select "Web identity"
3. Under "Identity provider" select "token.actions.githubusercontent.com"
4. Under "Audience" select the GitHub OIDC provider that you created previously
5. Set the following:
    * GitHub organization: `my-organization-name`
    * GitHub repository - optional: `my-repo-name`
    * Click "Next"
6. Add permissions
    * Select the name of your policy created in previous step (e.g. `github-actions-my-repo-name`).
    * Click "Next"
7. Name your new role
    * e.g. `my-repo-name-deployer`
    * Click "Create role"
8. Note the Role ARN
    * This will be the `AWS_ROLE_ARN` secret that you will be creating in your repo


#### Set Trust relationships for your role
This is a critical step and it's easy to make typos so pay attention.
Trust relationships specify which entity can assume the above newly created role.
1. Go to AWS console > IAM > Roles > Select your new role `my-repo-name-deployer`
2. Navigate to Trust relationships tab
3. Add trust policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::my-account-id-123:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:my-organization-name/my-repo-name:*"
                }
            }
        }
    ]
}
```
4. Some pointers:
    * The `sts:AssumeRoleWithWebIdentity` is controlled through Trust relationships, and does not need to be added to Policy.
    * If your value contains a wildcard symbol (asterisk *), make sure to use the Condition key "StringLike". Wildcards are not compatible with "StringEquals".
    * If you run into issues, make sure to check that there are no typos in "repo:my-organization-name/my-repo-name:*"

### Create new Github Action
You will need:
* `AWS_REGION` of EC2 and ElastiCache instances (should be in same region)
* `AWS_ROLE_ARN` of `my-repo-name-deployer`
* `REDIS_HOST` from `.env`
* `EC2_INSTANCE_ID` from `.env`
* `EC2_USERNAME` from `.env`
* `THIS_REPO` being `this-repo-org/this-repo-name`

#### Set your secrets in GitHub repo
1. Go to your repo in Github > Settings > (left column) Secrets and variables > Actions
2. Add the following New organization level secrets
    * Set `AWS_REGION` of EC2 and ElastiCache instances (should be in same region)
3. Add the following New repository secrets:
    * Set `AWS_ROLE_ARN` associated with the previously created role `my-repo-name-deployer`
    * Set `REDIS_HOST` to your ElastiCache endpoint
    * Set `EC2_USERNAME` set to default (usually `ubuntu`)
    * Set `EC2_SSH_KEY` to the contents of the private key file created with EC2 instance
    * Set `THIS_REPO` to `this-repo-org/this-repo-name`

Create a new workflow file
```sh
mkdir -p .github/workflows/
touch .github/workflows/deploy.yml
```
```yaml
name: Deploy to AWS
on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
          role-duration-seconds: 900

      - name: Update Security Group
        run: |
          # Get runner's public IP
          RUNNER_IP=$(curl -s https://api.ipify.org)
          echo "Runner IP: $RUNNER_IP"
          
          # Get security group ID
          SG_ID=$(aws ec2 describe-instances \
            --instance-ids ${{ secrets.EC2_INSTANCE_ID }} \
            --query 'Reservations[*].Instances[*].SecurityGroups[0].GroupId' \
            --output text)
          echo "Security Group ID: $SG_ID"
          
          # Add temporary rule for GitHub runner
          aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp \
            --port 22 \
            --cidr $RUNNER_IP/32

      - name: Setup SSH and Test Connection
        run: |
          # Setup SSH directory and files
          mkdir -p ~/.ssh
          touch ~/.ssh/known_hosts
          chmod 700 ~/.ssh
          chmod 600 ~/.ssh/known_hosts

          # Add EC2 key
          echo "${{ secrets.EC2_SSH_KEY }}" > ~/.ssh/ec2_key.pem
          chmod 600 ~/.ssh/ec2_key.pem

          # Get EC2 DNS
          EC2_PUBLIC_DNS=$(aws ec2 describe-instances \
            --instance-ids ${{ secrets.EC2_INSTANCE_ID }} \
            --query 'Reservations[*].Instances[*].PublicDnsName' \
            --output text)
          echo "EC2 Public DNS: $EC2_PUBLIC_DNS"

          # Disable strict host key checking for this connection
          echo "StrictHostKeyChecking no" >> ~/.ssh/config
          chmod 600 ~/.ssh/config

          # Test SSH connection
          ssh -i ~/.ssh/ec2_key.pem ${{ secrets.EC2_USERNAME }}@$EC2_PUBLIC_DNS 'echo "SSH connection test successful"'

      - name: Check EC2 Status
        run: |
          aws ec2 describe-instances \
            --instance-ids ${{ secrets.EC2_INSTANCE_ID }} \
            --query 'Reservations[*].Instances[*].[State.Name,Status.Status]' \
            --output text

      - name: Deploy to EC2
        env:
          REDIS_HOST: ${{ secrets.REDIS_HOST }}
        run: |
          # Debug EC2 instance info
          echo "Getting EC2 information..."
          EC2_PUBLIC_DNS=$(aws ec2 describe-instances \
            --instance-ids ${{ secrets.EC2_INSTANCE_ID }} \
            --query 'Reservations[*].Instances[*].PublicDnsName' \
            --output text)
          echo "EC2 Public DNS: $EC2_PUBLIC_DNS"

          # Debug known_hosts
          # Try ssh-keyscan with verbose output
          echo "Running ssh-keyscan with verbose output..."
          ssh-keyscan -v -H $EC2_PUBLIC_DNS 2>&1
          echo "known_hosts content:"
          cat ~/.ssh/known_hosts

          echo "Starting deployment..."
          ssh -v -i ~/.ssh/ec2_key.pem ${{ secrets.EC2_USERNAME }}@$EC2_PUBLIC_DNS 'bash -s' < scripts/deploy.sh
        
          # Print deploy.sh content for debugging
          echo "Content of deploy.sh:"
          cat scripts/deploy.sh

      - name: Cleanup Security Group
        if: always()
        run: |
          # Get the current IP and security group ID again
          RUNNER_IP=$(curl -s https://api.ipify.org)
          SG_ID=$(aws ec2 describe-instances \
            --instance-ids ${{ secrets.EC2_INSTANCE_ID }} \
            --query 'Reservations[*].Instances[*].SecurityGroups[0].GroupId' \
            --output text)
          
          # Check if the rule exists before trying to remove it
          RULE_EXISTS=$(aws ec2 describe-security-groups \
            --group-ids $SG_ID \
            --filters "Name=ip-permission.cidr,Values=$RUNNER_IP/32" \
            --filters "Name=ip-permission.from-port,Values=22" \
            --query 'SecurityGroups[*].IpPermissions[?FromPort==`22`]' \
            --output text)
          
          if [ ! -z "$RULE_EXISTS" ]; then
            echo "Removing temporary security group rule..."
            aws ec2 revoke-security-group-ingress \
              --group-id $SG_ID \
              --protocol tcp \
              --port 22 \
              --cidr $RUNNER_IP/32
          else
            echo "Security group rule not found, skipping removal"
          fi
```