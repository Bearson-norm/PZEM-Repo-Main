#!/bin/bash
# VPS Setup Script - Run this ONCE on the VPS
# This script sets up the environment for PZEM Monitoring

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PZEM Monitoring - VPS Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "Please run as regular user (not root)"
    exit 1
fi

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. Please logout and login again for group changes to take effect."
fi

# Install docker-compose if not installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Installing docker-compose..."
    sudo apt-get install -y docker-compose-plugin
fi

# Install Nginx if not installed
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    sudo apt-get install -y nginx
fi

# Install Certbot for SSL
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Create directories
echo "Creating directories..."
mkdir -p ~/pzem-monitoring
mkdir -p ~/backups
mkdir -p ~/pzem-monitoring/backups

# Setup firewall (UFW)
echo "Configuring firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw --force enable

# Setup Nginx
echo "Setting up Nginx..."
if [ ! -f /etc/nginx/sites-available/pzem.moof-set.web.id ]; then
    sudo cp ~/pzem-monitoring/nginx-pzem.conf /etc/nginx/sites-available/pzem.moof-set.web.id
    sudo ln -sf /etc/nginx/sites-available/pzem.moof-set.web.id /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}VPS Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Deploy application using: ./deploy-to-vps-safe.sh"
echo "2. Setup SSL certificate: sudo certbot --nginx -d pzem.moof-set.web.id"
echo "3. Configure domain DNS to point to this VPS IP"
echo ""
echo "Note: You may need to logout and login again for Docker group changes"
echo ""
