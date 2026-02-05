#!/bin/bash
# Quick Fix Script untuk 502 Bad Gateway
# Usage: ./QUICK_FIX_502.sh

set -e

echo "🚀 Quick Fix 502 Bad Gateway"
echo "============================="
echo ""

# Detect docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found"
    exit 1
fi

# Change to project directory
cd /opt/pzem-monitoring 2>/dev/null || {
    echo "❌ Cannot access /opt/pzem-monitoring"
    echo "   Please run this script from the project directory"
    exit 1
}

echo "📍 Working directory: $(pwd)"
echo ""

# Step 1: Restart dashboard
echo "1️⃣ Restarting dashboard container..."
$DOCKER_COMPOSE restart dashboard
echo "   ✅ Dashboard restarted"
echo "   ⏳ Waiting 10 seconds for startup..."
sleep 10
echo ""

# Step 2: Check status
echo "2️⃣ Checking container status..."
$DOCKER_COMPOSE ps dashboard
echo ""

# Step 3: Test connection
echo "3️⃣ Testing dashboard connection..."
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "   ✅ Dashboard is accessible on localhost:5000"
    curl -s http://localhost:5000/health | head -3
else
    echo "   ❌ Dashboard is NOT accessible"
    echo ""
    echo "   Checking logs..."
    $DOCKER_COMPOSE logs dashboard --tail=30
    echo ""
    echo "   ⚠️  Please check the logs above for errors"
    exit 1
fi
echo ""

# Step 4: Reload nginx
echo "4️⃣ Reloading nginx..."
if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    echo "   ✅ Nginx reloaded"
else
    echo "   ⚠️  Nginx config has errors. Please check:"
    echo "      sudo nginx -t"
    exit 1
fi
echo ""

# Step 5: Final test
echo "5️⃣ Final verification..."
sleep 2
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "   ✅ All checks passed!"
    echo ""
    echo "🌐 Your website should be accessible now:"
    echo "   https://pzem.moof-set.web.id/"
    echo ""
    echo "If you still see 502 error:"
    echo "  1. Wait 10-30 seconds more"
    echo "  2. Clear browser cache (Ctrl+Shift+R)"
    echo "  3. Check nginx error log: sudo tail -f /var/log/nginx/error.log"
else
    echo "   ⚠️  Dashboard still not accessible"
    echo "   Please check logs: $DOCKER_COMPOSE logs dashboard -f"
    exit 1
fi
