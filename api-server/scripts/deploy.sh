#!/bin/bash
set -x  # Print commands and their arguments as they are executed
trap 'echo "Error on line $LINENO"' ERR  # Print line number where any error occurs

echo "Starting deployment..."

# Navigate to app directory (create if doesn't exist)
APP_DIR="/home/ubuntu/api-server"
mkdir -p $APP_DIR
cd $APP_DIR

# Backup current version if exists
if [ -d "current" ]; then
    mv current previous_$(date +%Y%m%d_%H%M%S)
fi

# Create new deployment directory
mkdir -p current
cd current

# Clone latest code (you might want to use a deploy key for private repos)
git clone https://github.com/jo-yrabbit-sandbox/sandbox-api-server.git .

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Update Redis host in configuration
sed -i "s/your-elasticache-endpoint.region.cache.amazonaws.com/$REDIS_HOST/g" api/server.py

# Restart the service
sudo systemctl restart api-server

echo "Deployment completed successfully!"