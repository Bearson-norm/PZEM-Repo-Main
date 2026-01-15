#!/bin/bash
# Setup Nginx and SSL for PZEM Monitoring
# Run this on VPS after deployment
# Usage: ./setup-nginx-ssl.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

DOMAIN="pzem.moof-set.web.id"
DEPLOY_DIR="/opt/pzem-monitoring"
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"

echo ""
echo "🔧 Nginx & SSL Setup for PZEM Monitoring"
echo "========================================"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run with sudo: sudo ./setup-nginx-ssl.sh"
    exit 1
fi

# Step 1: Check if nginx is installed
print_info "Checking Nginx installation..."
if ! command -v nginx &> /dev/null; then
    print_warning "Nginx not found. Installing..."
    apt update
    apt install -y nginx
    print_status "Nginx installed"
else
    print_status "Nginx is installed"
fi

# Step 2: Check if certbot is installed
print_info "Checking Certbot installation..."
if ! command -v certbot &> /dev/null; then
    print_warning "Certbot not found. Installing..."
    apt update
    apt install -y certbot python3-certbot-nginx
    print_status "Certbot installed"
else
    print_status "Certbot is installed"
fi

# Step 3: Copy nginx config
print_info "Setting up Nginx configuration..."
if [ -f "${DEPLOY_DIR}/nginx-pzem.conf" ]; then
    cp "${DEPLOY_DIR}/nginx-pzem.conf" "${NGINX_CONF}"
    print_status "Nginx config copied"
else
    print_error "Nginx config not found at ${DEPLOY_DIR}/nginx-pzem.conf"
    exit 1
fi

# Step 4: Create symlink
print_info "Creating Nginx symlink..."
if [ ! -L "/etc/nginx/sites-enabled/${DOMAIN}" ]; then
    ln -s "${NGINX_CONF}" "/etc/nginx/sites-enabled/${DOMAIN}"
    print_status "Symlink created"
else
    print_info "Symlink already exists"
fi

# Step 5: Test nginx config
print_info "Testing Nginx configuration..."
if nginx -t; then
    print_status "Nginx configuration is valid"
else
    print_error "Nginx configuration test failed"
    exit 1
fi

# Step 6: Reload nginx
print_info "Reloading Nginx..."
systemctl reload nginx
print_status "Nginx reloaded"

# Step 7: Setup SSL
print_info "Setting up SSL certificate..."
print_warning "Make sure DNS is pointing to this server: ${DOMAIN} -> $(hostname -I | awk '{print $1}')"
read -p "Continue with SSL setup? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    # Check if certificate already exists
    if [ -d "/etc/letsencrypt/live/${DOMAIN}" ]; then
        print_warning "SSL certificate already exists"
        read -p "Renew certificate? (yes/no): " renew
        if [ "$renew" = "yes" ]; then
            certbot --nginx -d ${DOMAIN} --force-renewal
            print_status "Certificate renewed"
        else
            print_info "Using existing certificate"
        fi
    else
        certbot --nginx -d ${DOMAIN}
        print_status "SSL certificate obtained"
    fi
    
    # Reload nginx after SSL setup
    systemctl reload nginx
    print_status "Nginx reloaded with SSL"
else
    print_warning "SSL setup skipped. You can run later:"
    print_info "  sudo certbot --nginx -d ${DOMAIN}"
fi

# Step 8: Verify setup
print_info "Verifying setup..."
sleep 2

# Check nginx status
if systemctl is-active --quiet nginx; then
    print_status "Nginx is running"
else
    print_error "Nginx is not running"
    exit 1
fi

# Check if dashboard is accessible
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    print_status "Dashboard is accessible"
else
    print_warning "Dashboard health check failed (may still be starting)"
fi

echo ""
print_status "✅ Nginx & SSL setup completed!"
echo ""
echo "📊 Summary:"
echo "   - Nginx config: ${NGINX_CONF}"
echo "   - Domain: ${DOMAIN}"
echo "   - SSL: $(if [ -d "/etc/letsencrypt/live/${DOMAIN}" ]; then echo '✅ Configured'; else echo '❌ Not configured'; fi)"
echo ""
echo "🌐 Access your system:"
echo "   HTTP:  http://${DOMAIN}"
echo "   HTTPS: https://${DOMAIN} (if SSL configured)"
echo "   Direct: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "📋 Useful commands:"
echo "   - Check nginx status: sudo systemctl status nginx"
echo "   - View nginx logs: sudo tail -f /var/log/nginx/pzem_error.log"
echo "   - Test nginx config: sudo nginx -t"
echo "   - Reload nginx: sudo systemctl reload nginx"
echo "   - Renew SSL: sudo certbot renew"
echo ""
