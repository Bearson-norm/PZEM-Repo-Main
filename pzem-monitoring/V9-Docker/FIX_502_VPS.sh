#!/bin/bash
# Comprehensive Fix Script for 502 Bad Gateway on VPS
# This script fixes common issues causing 502 errors

set -e

echo "🔧 Fixing 502 Bad Gateway Error"
echo "==============================="
echo ""

# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found"
    exit 1
fi

# Change to project directory
PROJECT_DIR="/opt/pzem-monitoring"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "⚠️  Project directory not found at $PROJECT_DIR"
    echo "   Trying current directory..."
    PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi

cd "$PROJECT_DIR"
echo "📍 Working directory: $PROJECT_DIR"
echo ""

# Step 1: Check and restart dashboard container
echo "1️⃣ Checking dashboard container..."
if $DOCKER_COMPOSE ps dashboard | grep -q "Up"; then
    echo "   ✅ Dashboard container is running"
    echo "   🔄 Restarting to ensure clean state..."
    $DOCKER_COMPOSE restart dashboard
else
    echo "   ❌ Dashboard container is NOT running!"
    echo "   🚀 Starting dashboard container..."
    $DOCKER_COMPOSE up -d dashboard
fi

echo "   ⏳ Waiting 15 seconds for dashboard to fully start..."
sleep 15
echo ""

# Step 2: Check dashboard logs
echo "2️⃣ Checking dashboard logs (last 30 lines)..."
$DOCKER_COMPOSE logs dashboard --tail=30
echo ""

# Step 3: Test dashboard accessibility
echo "3️⃣ Testing dashboard on localhost:5000..."
MAX_RETRIES=5
RETRY_COUNT=0
DASHBOARD_ACCESSIBLE=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
        echo "   ✅ Dashboard is accessible on localhost:5000"
        curl -s http://localhost:5000/health | head -5
        DASHBOARD_ACCESSIBLE=true
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "   ⏳ Attempt $RETRY_COUNT/$MAX_RETRIES failed. Waiting 5 seconds..."
            sleep 5
        fi
    fi
done

if [ "$DASHBOARD_ACCESSIBLE" = false ]; then
    echo "   ❌ Dashboard is NOT accessible after $MAX_RETRIES attempts"
    echo ""
    echo "   🔍 Checking container status..."
    $DOCKER_COMPOSE ps dashboard
    echo ""
    echo "   🔍 Checking recent logs for errors..."
    $DOCKER_COMPOSE logs dashboard --tail=50 | grep -i "error\|exception\|failed" || echo "   No obvious errors found"
    echo ""
    echo "   ⚠️  Please check the logs above and fix any issues before continuing"
    echo "   You can check logs with: $DOCKER_COMPOSE logs dashboard -f"
    exit 1
fi
echo ""

# Step 4: Check port 5000
echo "4️⃣ Checking if port 5000 is listening..."
if netstat -tuln 2>/dev/null | grep -q ":5000" || ss -tuln 2>/dev/null | grep -q ":5000"; then
    echo "   ✅ Port 5000 is listening"
    netstat -tuln 2>/dev/null | grep ":5000" || ss -tuln 2>/dev/null | grep ":5000"
else
    echo "   ⚠️  Port 5000 not found in listening ports (may be normal if using Docker networking)"
fi
echo ""

# Step 5: Check and fix Nginx configuration
echo "5️⃣ Checking Nginx configuration..."
NGINX_CONFIG="/etc/nginx/sites-available/pzem.moof-set.web.id"
NGINX_ENABLED="/etc/nginx/sites-enabled/pzem.moof-set.web.id"

if [ ! -f "$NGINX_CONFIG" ]; then
    echo "   ⚠️  Nginx config file not found at $NGINX_CONFIG"
    echo "   Searching for config files..."
    sudo find /etc/nginx -name "*pzem*" -o -name "*moof*" 2>/dev/null || echo "   No config files found"
    echo ""
    echo "   Please create Nginx config file manually or use the example:"
    echo "   See: pzem-monitoring/V9-Docker/nginx-config-example.conf"
    exit 1
fi

echo "   ✅ Nginx config file found: $NGINX_CONFIG"
echo ""

# Check if config has correct proxy_pass
echo "   Checking proxy_pass configuration..."
if grep -q "proxy_pass.*127.0.0.1:5000\|proxy_pass.*localhost:5000\|proxy_pass.*pzem_dashboard" "$NGINX_CONFIG"; then
    echo "   ✅ proxy_pass is configured"
    grep -i "proxy_pass" "$NGINX_CONFIG" | head -3
else
    echo "   ⚠️  proxy_pass not found or incorrect"
    echo "   Current proxy_pass settings:"
    grep -i "proxy_pass" "$NGINX_CONFIG" || echo "   None found!"
fi
echo ""

# Check WebSocket support for Socket.IO
echo "   Checking WebSocket/Socket.IO support..."
if grep -q "/socket.io/" "$NGINX_CONFIG"; then
    echo "   ✅ Socket.IO location block found"
else
    echo "   ⚠️  Socket.IO location block not found"
    echo "   This may cause Socket.IO connection issues"
fi
echo ""

# Step 6: Test Nginx configuration
echo "6️⃣ Testing Nginx configuration..."
if sudo nginx -t 2>&1; then
    echo "   ✅ Nginx configuration is valid"
else
    echo "   ❌ Nginx configuration has errors!"
    echo "   Please fix the errors before continuing:"
    echo "   sudo nano $NGINX_CONFIG"
    echo "   sudo nginx -t"
    exit 1
fi
echo ""

# Step 7: Reload Nginx
echo "7️⃣ Reloading Nginx..."
if sudo systemctl reload nginx; then
    echo "   ✅ Nginx reloaded successfully"
else
    echo "   ❌ Failed to reload Nginx"
    echo "   Trying restart instead..."
    sudo systemctl restart nginx
    sleep 2
    if sudo systemctl is-active --quiet nginx; then
        echo "   ✅ Nginx restarted successfully"
    else
        echo "   ❌ Nginx failed to start"
        echo "   Check status: sudo systemctl status nginx"
        exit 1
    fi
fi
echo ""

# Step 8: Final verification
echo "8️⃣ Final verification..."
sleep 3

# Test dashboard again
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "   ✅ Dashboard is still accessible"
else
    echo "   ⚠️  Dashboard became inaccessible after Nginx reload"
    echo "   Restarting dashboard..."
    $DOCKER_COMPOSE restart dashboard
    sleep 10
fi

# Test through Nginx (if domain is configured)
echo ""
echo "🧪 Testing through Nginx..."
if curl -f -s -k https://pzem.moof-set.web.id/health > /dev/null 2>&1 || \
   curl -f -s http://pzem.moof-set.web.id/health > /dev/null 2>&1; then
    echo "   ✅ Website is accessible through Nginx"
else
    echo "   ⚠️  Website not accessible through domain (may be DNS/SSL issue)"
    echo "   But localhost:5000 should work"
fi
echo ""

# Summary
echo "✅ Fix completed!"
echo ""
echo "📋 Summary:"
echo "   - Dashboard container: $(if $DOCKER_COMPOSE ps dashboard | grep -q "Up"; then echo "✅ Running"; else echo "❌ Not running"; fi)"
echo "   - Dashboard health: $(if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then echo "✅ Accessible"; else echo "❌ Not accessible"; fi)"
echo "   - Nginx status: $(if sudo systemctl is-active --quiet nginx; then echo "✅ Running"; else echo "❌ Not running"; fi)"
echo ""
echo "🌐 Next steps:"
echo "   1. Wait 10-30 seconds for everything to stabilize"
echo "   2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)"
echo "   3. Try accessing: https://pzem.moof-set.web.id/"
echo ""
echo "If you still see 502 errors:"
echo "   1. Check dashboard logs: $DOCKER_COMPOSE logs dashboard -f"
echo "   2. Check Nginx error log: sudo tail -f /var/log/nginx/error.log"
echo "   3. Verify Nginx config: sudo nginx -t"
echo "   4. Check container status: $DOCKER_COMPOSE ps"
echo ""
