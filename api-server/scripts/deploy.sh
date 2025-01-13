#!/bin/bash
set -x  # Print commands and their arguments as they are executed
set -e # Exit on any error
trap 'echo "Error on line $LINENO"' ERR  # Print line number where any error occurs

echo "Starting deployment..."

# Install required packages
sudo apt-get update
sudo apt-get install -y python3-venv

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
git clone https://github.com/jo-yrabbit-sandbox/sandbox-infrastructure.git .
cd api-server

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt || {
    echo "pip install failed with exit code $?"
    exit 1
}

# Update Redis host in configuration
sed -i "s/your-elasticache-endpoint.region.cache.amazonaws.com/$REDIS_HOST/g" api/server.py

# Create systemd service file
sudo tee /etc/systemd/system/api-server.service << EOF
[Unit]
Description=API Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR/current/api-server
Environment="PATH=$APP_DIR/current/api-server/venv/bin"
ExecStart=$APP_DIR/current/api-server/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Make log dir matching gunicorn_config.py
mkdir logs

# Reload systemd, enable and restart service
sudo systemctl daemon-reload
sudo systemctl enable api-server
sudo systemctl restart api-server

echo "Deployment completed successfully!"