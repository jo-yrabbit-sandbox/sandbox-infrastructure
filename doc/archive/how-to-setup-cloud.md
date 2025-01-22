## How to deploy to cloud

This is an outdated how-to for manually setting up AWS resources for API server portion of the infrastructure only, in standalone.
It does not integrate the Bot platform, and has no terraform management.

This how-to is obsolete because we now use terraform to manage all AWS resources and deployment workflow.
However, this doc may help future troubleshooting/prototyping efforts, so we will leave it here, along with other archived how-tos.

### Overview

#### Create a Redis cluster in ElastiCache
- Choose cache subnet group in your VPC
- Note down the endpoint URL
- Set up security group allowing inbound traffic on port 6379

#### Launch EC2 instance
- Use Amazon Linux 2 or Ubuntu
- Place it in the same VPC as ElastiCache
- Create/use security group allowing:
  - Inbound HTTP (80)
  - HTTPS (443) 
  - Custom TCP (5000) for Flask
  - SSH (22) for admin access

### How-to

#### Create VPC
1. Go to AWS Console > VPC
2. Click "Create VPC"
3. Select "VPC and more" (this automatically creates subnets, route tables, etc.)
* `Name`: sandbox-api-vpc
* `IPv4 CIDR block`: 10.0.0.0/16 (65,536 IP addresses)
* `Number of Availability Zones (AZs)`: 2
* `Number of public subnets`: 2 (for EC2 hosting `api-server`)
* `Number of private subnets`: 2 (for ElastiCache hosting `redis`)
* `NAT gateways`: 1 AZ (costs $)
* `VPC endpoints`: None (not needed for this setup)
4. Note the `VPC ID` for next step (ElastiCache redis cluster setup)

#### Create security group
1. Go to AWS Console > VPC > Security Groups
2. Click "Create security group" (create a new one from scratch, even if a default one exists)
3. Configure:
* `Security group name`: sandbox-redis-elasticache-sg
* `Description`: Security group for Redis ElastiCache cluster (best practice to document this!)
* `VPC`: \<Select the VPC ID created in previous step\>
* `Inbound rules`: (set to below for now, and we'll update this later)
  * `Type`: Custom TCP
  * `Port`: 6379
  * `Source`: Anywhere IPv4 (for now, but change EC2 security group reference later)
* `Outbound rules`: Leave default (All traffic)
4. Note the `Security group ID` for next step (ElastiCache redis cluster setup)

#### Create redis cluster (ElastiCache)
1. Go to AWS Console → ElastiCache
2. Create new Redis OSS cache
3. Choose `Design your own cache` and `Cluster cache` with following Settings:
* Cluster:
  * `Cluster mode`: Disabled
  * `Name`: sandbox-redis-cluster
* Location:
  * `Location`: AWS Cloud
  * `Multi-AZ`: Disabled
* Cluster info:
  * `Node type`: cache.t4g.micro (cheapest for dev/testing)
  * `Number of replicas`: 0
* Connectivity:
  * `Subnet groups`: Create a new subnet group
  * `Name`: sandbox-vpc
  * `VPC ID`: \<Select the VPC ID created in previous step\>
  * `Subnets`: \<Select 2 private subnets created in previous step\>
* Advanced settings:
  * `Security`: \<Select the VPC ID created in previous step\>

#### Create cloud instance of api-server (EC2)
1. Go to AWS Console → EC2
2. Click "Launch instance"
3. Settings:
* `Name`: sandbox-api-server
* `AMI`: Ubuntu Server 22.04 LTS
* `Instance type`: t2.micro (free tier eligible)
* `Key pair`: Create a new pair and securely store the `your-key.pem` file somewhere
* `Network settings`
  * \<Select the VPC ID created in previous step\>
  * \<Select the *public* subnets you created in previous step\>!!!
  * `Auto-assign public IP`: Enable
  * Select `Create new security group`
    * `Name`: sandbox-api-server-ec2-sg
    * `Description`: Security group for Ubuntu 22.04 LTS EC2
    * Add the following `Inbound rules`. AWS console will have \<your public IP address\> in dropdown as `My IP` but if you want to double check, look it up at [https://whatismyip.com] or `curl ifconfig.me`
      * Custom ICMP - IPv4, Echo Request (Not reply), from \<your public IP address\>/32
      * SSH, Port 22, from \<your public IP address\>/32
      * Custom TCP, Port 5000, from 0.0.0.0/0
      * HTTP, Port 80, from 0.0.0.0/0
4. Note the Public DNS for your new EC2 instance for next step. Ping it from your PC:
```sh
ping <your-ec2-public-dns>
```
5. Connect to your EC2 instance
```sh
# Change permissions on your key file
chmod 400 your-key.pem
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-public-dns
```
* If you have connection issues, note that certain EC2 settings cannot be changed after instance is created:
  * Don't recycle key pairs. Create a new one on instance creation
  * The subnet you select for your EC2 needs to be public (the private subnets are for your backend redis ElastiCache)
  * Enable `Auto-assign public IP`

6. Update security group (for both EC2 and ElastiCache)
* Go to EC2 security group (sandbox-api-server-ec2-sg)
  * Add inbound rule to allow traffic to Redis:
    * Custom TCP, Port 6379, Source: redis-security-group ID
* Go to Redis ElastiCache security group (sandbox-redis-elasticache-sg)
  * Add inbound rule (AWS console will not allow you to edit the existing one, so delete the existing one):
    * Custom TCP, Port 6379, Source: sandbox-api-server-ec2-sg

### Deploy (manual)

1. SSH into instance
```sh
ssh -i your-key.pem ubuntu@your-ec2-public-dns
```

2. Install dependencies
```sh
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.10-venv -y
```

3. Place a copy of source code for Flask app `api-server` inside the EC2 instance
* Create folder structure inside your EC2 instance
```sh
# Inside EC2
mkdir -p ~/api-server
cd ~/api-server
mkdir api
exit
```
* Copy contents from your local PC to EC2 instance
```sh
# From local PC
scp -i your-key.pem -r app.py requirements.txt gunicorn_config.py .env ubuntu@your-ec2-public-dns:~/api-server/
scp -i your-key.pem -r api/redis_handler.py api/server.py api/__init__.py ubuntu@your-ec2-public-dns:~/api-server/api/
```

4. Test that your application runs if launched manually
```sh
source venv/bin/activate
pip install -r requirements.txt
python -m app  # application should launch and keep running until Ctrl+C
```

5. Create a systemd service for `api-server`
```sh
sudo vi /etc/systemd/system/api-server.service
```
Add this content into the file
```ini
[Unit]
Description=API Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/api-server
Environment="PATH=/home/ubuntu/api-server/venv/bin"
EnvironmentFile=/home/ubuntu/api-server/.env
ExecStart=/home/ubuntu/api-server/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

6. Start/restart the service on EC2
```sh
# Inside EC2
sudo systemctl daemon-reload  # Reload systemd to recognize new service
sudo systemctl restart api-server  # Start the service
sudo systemctl enable api-server  # Enable service to start on boot
sudo systemctl status api-server  # Check status
# Expect the output to show "Active: active (running)"
```

#### Troubleshoot
```sh
sudo systemctl stop api-server  # Stop the service
sudo systemctl restart api-server  # Restart the service
sudo journalctl -u api-server -f  # View logs
# View application logs
tail -f ~/api-server/logs/app.log
tail -f ~/api-server/logs/access.log
tail -f ~/api-server/logs/error.log
```

### Test

Now that your application is deployed to EC2, you should be able to make api calls from your local PC.

#### Sanity test (without redis)
* Url: http://your-ec2-public-dns:5000/api/v1/health
* Curl command: `curl -X GET <url>`
Expected response:
```json
{"status":"healthy"}
```

#### Test endpoints
1. Copy over some test messages to /tmp
```sh
# From your local PC
scp -i your-key.pem -r tests/test_message_1.json tests/test_message_2.json ubuntu@your-ec2-public-dns:/tmp/
```
2. Make `POST` request with url: http://your-ec2-public-dns:5000/api/v1/messages
```sh
# Send first message
curl -0 -v POST <url> \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @test_message_1.json
# Expected response
{"message_id":"msg:123","success":true}
# Send second message
curl -0 -v POST <url> \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @test_message_2.json
# Expected response with unique message_id
{"message_id":"msg:456","success":true}
```

3. Get latest message
  * Make `GET` request with url: http://your-ec2-public-dns:5000/api/v1/messages/latest?state=test_state
```sh
curl -X GET <url>
```
  * Expected response:
```json
{"message":"{'bot_id': 'test-bot', 'state': 'test_state', 'text': 'test_text_2', 'timestamp': 'test_timestamp_2'}"}
```
* If no messages have been stored in redis, error is expected because redis database has nothing stored in it at this time
```json
{"error":"Error getting latest message - Failed to get latest 1 messages using key state:test_state:messages"}
```
