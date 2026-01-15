#!/bin/bash
# Script untuk troubleshoot dan fix nginx 502 Bad Gateway

echo "🔍 Troubleshooting Nginx 502 Bad Gateway"
echo "=========================================="
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

# 1. Check container status
echo "1️⃣ Checking Docker containers..."
$DOCKER_COMPOSE ps
echo ""

# 2. Check if dashboard container is running
echo "2️⃣ Checking dashboard container..."
if $DOCKER_COMPOSE ps dashboard | grep -q "Up"; then
    echo "✅ Dashboard container is running"
else
    echo "❌ Dashboard container is NOT running!"
    echo "   Attempting to start..."
    $DOCKER_COMPOSE up -d dashboard
    sleep 5
fi
echo ""

# 3. Check dashboard logs for errors
echo "3️⃣ Checking dashboard logs (last 20 lines)..."
$DOCKER_COMPOSE logs dashboard --tail=20
echo ""

# 4. Test if dashboard is accessible from host
echo "4️⃣ Testing dashboard from host (localhost:5000)..."
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Dashboard is accessible on localhost:5000"
    curl -s http://localhost:5000/health | head -3
else
    echo "❌ Dashboard is NOT accessible on localhost:5000"
    echo "   This is the problem! Nginx cannot connect to backend."
fi
echo ""

# 5. Check nginx configuration
echo "5️⃣ Checking nginx configuration..."
if [ -f "/etc/nginx/sites-available/pzem.moof-set.web.id" ]; then
    echo "✅ Nginx config file found"
    echo "   Location: /etc/nginx/sites-available/pzem.moof-set.web.id"
    echo ""
    echo "   Current proxy_pass setting:"
    grep -i "proxy_pass" /etc/nginx/sites-available/pzem.moof-set.web.id || echo "   No proxy_pass found!"
else
    echo "⚠️  Nginx config file not found at expected location"
    echo "   Searching for config files..."
    sudo find /etc/nginx -name "*pzem*" -o -name "*moof*" 2>/dev/null
fi
echo ""

# 6. Check nginx status
echo "6️⃣ Checking nginx status..."
sudo systemctl status nginx --no-pager | head -10
echo ""

# 7. Check nginx error logs
echo "7️⃣ Checking nginx error logs (last 10 lines)..."
sudo tail -10 /var/log/nginx/error.log 2>/dev/null || echo "   Cannot read error log"
echo ""

# 8. Check if port 5000 is listening
echo "8️⃣ Checking if port 5000 is listening..."
if netstat -tuln | grep -q ":5000" || ss -tuln | grep -q ":5000"; then
    echo "✅ Port 5000 is listening"
    netstat -tuln | grep ":5000" || ss -tuln | grep ":5000"
else
    echo "❌ Port 5000 is NOT listening!"
    echo "   Dashboard container may not be running properly"
fi
echo ""

# 9. Suggested fix
echo "🔧 Suggested Fixes:"
echo "==================="
echo ""
echo "If dashboard is NOT accessible on localhost:5000:"
echo "  1. Restart dashboard container:"
echo "     cd /opt/pzem-monitoring"
echo "     $DOCKER_COMPOSE restart dashboard"
echo ""
echo "  2. Check dashboard logs for errors:"
echo "     $DOCKER_COMPOSE logs dashboard -f"
echo ""
echo "If nginx config is wrong, update it:"
echo "  sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id"
echo ""
echo "  Make sure proxy_pass points to:"
echo "    proxy_pass http://127.0.0.1:5000;"
echo "    # atau"
echo "    proxy_pass http://localhost:5000;"
echo ""
echo "  Then reload nginx:"
echo "    sudo nginx -t  # Test config"
echo "    sudo systemctl reload nginx"
echo ""











