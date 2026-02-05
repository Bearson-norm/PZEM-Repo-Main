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

# 9. Auto-fix attempt
echo "🔧 Attempting Auto-Fix..."
echo "=========================="
echo ""

FIXED=false

# Fix 1: Restart dashboard if not accessible
if ! curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "🔄 Fixing: Restarting dashboard container..."
    cd /opt/pzem-monitoring 2>/dev/null || cd "$(dirname "$0")"
    $DOCKER_COMPOSE restart dashboard
    sleep 10
    echo "   Waiting for dashboard to start..."
    
    # Test again
    if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
        echo "   ✅ Dashboard is now accessible!"
        FIXED=true
    else
        echo "   ⚠️  Dashboard still not accessible. Check logs:"
        echo "      $DOCKER_COMPOSE logs dashboard --tail=30"
    fi
fi

# Fix 2: Check and fix nginx config if needed
NGINX_CONFIG="/etc/nginx/sites-available/pzem.moof-set.web.id"
if [ -f "$NGINX_CONFIG" ]; then
    # Check if proxy_pass is correct
    if ! grep -q "proxy_pass.*127.0.0.1:5000\|proxy_pass.*localhost:5000\|proxy_pass.*pzem_dashboard" "$NGINX_CONFIG"; then
        echo "🔄 Fixing: Updating nginx proxy_pass configuration..."
        sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Try to fix proxy_pass
        if grep -q "upstream pzem_dashboard" "$NGINX_CONFIG"; then
            # Config uses upstream, check if it's correct
            if ! grep -q "server 127.0.0.1:5000" "$NGINX_CONFIG"; then
                echo "   Updating upstream to use 127.0.0.1:5000..."
                sudo sed -i 's/server.*:5000/server 127.0.0.1:5000/' "$NGINX_CONFIG"
            fi
        else
            # Direct proxy_pass, update it
            echo "   Updating proxy_pass to http://127.0.0.1:5000..."
            sudo sed -i 's|proxy_pass http://[^;]*;|proxy_pass http://127.0.0.1:5000;|g' "$NGINX_CONFIG"
        fi
        
        # Test nginx config
        if sudo nginx -t 2>/dev/null; then
            echo "   ✅ Nginx config is valid"
            sudo systemctl reload nginx
            echo "   ✅ Nginx reloaded"
            FIXED=true
        else
            echo "   ⚠️  Nginx config has errors. Please check manually:"
            echo "      sudo nano $NGINX_CONFIG"
        fi
    fi
fi

# Summary
echo ""
if [ "$FIXED" = true ]; then
    echo "✅ Auto-fix completed!"
    echo ""
    echo "🧪 Testing connection..."
    sleep 2
    if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ Dashboard is accessible on localhost:5000"
        echo ""
        echo "🌐 Try accessing your website now:"
        echo "   https://pzem.moof-set.web.id/"
        echo ""
        echo "If still getting 502 error:"
        echo "  1. Wait 10-30 seconds for dashboard to fully start"
        echo "  2. Clear browser cache (Ctrl+Shift+R)"
        echo "  3. Check nginx error log: sudo tail -f /var/log/nginx/error.log"
    else
        echo "⚠️  Dashboard still not accessible. Manual intervention needed."
    fi
else
    echo "⚠️  Auto-fix could not resolve the issue."
    echo ""
    echo "🔧 Manual Fix Required:"
    echo "======================"
    echo ""
    echo "1. Check dashboard logs:"
    echo "   cd /opt/pzem-monitoring"
    echo "   $DOCKER_COMPOSE logs dashboard --tail=50"
    echo ""
    echo "2. Restart dashboard:"
    echo "   $DOCKER_COMPOSE restart dashboard"
    echo ""
    echo "3. Check nginx config:"
    echo "   sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id"
    echo "   # Make sure proxy_pass points to: http://127.0.0.1:5000"
    echo ""
    echo "4. Reload nginx:"
    echo "   sudo nginx -t"
    echo "   sudo systemctl reload nginx"
    echo ""
fi











