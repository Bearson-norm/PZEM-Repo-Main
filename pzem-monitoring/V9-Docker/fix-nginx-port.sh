#!/bin/bash
# Script untuk fix nginx config - ubah port dari 8080 ke 5000

echo "🔧 Fixing Nginx Configuration"
echo "=============================="
echo ""

NGINX_CONFIG="/etc/nginx/sites-available/pzem.moof-set.web.id"

# Backup config dulu
echo "📦 Backing up current config..."
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup created"

# Fix proxy_pass dari 8080 ke 5000
echo ""
echo "🔧 Updating proxy_pass from port 8080 to 5000..."
sudo sed -i 's|proxy_pass http://localhost:8080;|proxy_pass http://127.0.0.1:5000;|g' "$NGINX_CONFIG"
sudo sed -i 's|proxy_pass http://127.0.0.1:8080;|proxy_pass http://127.0.0.1:5000;|g' "$NGINX_CONFIG"

# Verify change
echo ""
echo "✅ Updated config:"
grep "proxy_pass" "$NGINX_CONFIG" || echo "   (run with sudo to see)"

# Test nginx config
echo ""
echo "🧪 Testing nginx configuration..."
if sudo nginx -t; then
    echo "✅ Nginx config is valid"
    echo ""
    echo "🔄 Reloading nginx..."
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded"
    echo ""
    echo "🌐 Test your website now: https://pzem.moof-set.web.id"
else
    echo "❌ Nginx config has errors!"
    echo "   Please check manually: sudo nano $NGINX_CONFIG"
    exit 1
fi











