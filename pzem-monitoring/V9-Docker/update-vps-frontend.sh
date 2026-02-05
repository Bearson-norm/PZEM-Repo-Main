#!/bin/bash
# Script untuk update frontend di VPS setelah git pull
# Usage: ./update-vps-frontend.sh

set -e

echo "🔄 Updating Frontend on VPS..."
echo ""

# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ ERROR: docker-compose not found"
    exit 1
fi

# Get current directory (should be in V9-Docker)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📂 Current directory: $(pwd)"
echo ""

# Step 1: Pull latest changes from git (if in git repo)
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes from git..."
    git pull origin main || git pull origin master || echo "⚠️  Git pull failed or not a git repo"
    echo ""
fi

# Step 2: Verify dashboard.html exists and has recent changes
DASHBOARD_HTML="dashboard/templates/dashboard.html"
if [ -f "$DASHBOARD_HTML" ]; then
    echo "✅ Found dashboard.html"
    echo "   Last modified: $(stat -c %y "$DASHBOARD_HTML" 2>/dev/null || stat -f "%Sm" "$DASHBOARD_HTML" 2>/dev/null || echo "Unknown")"
    echo "   File size: $(du -h "$DASHBOARD_HTML" | cut -f1)"
    echo ""
else
    echo "❌ ERROR: dashboard.html not found at $DASHBOARD_HTML"
    exit 1
fi

# Step 3: Restart dashboard container to reload changes
echo "🔄 Restarting dashboard container..."
if $DOCKER_COMPOSE restart dashboard; then
    echo "✅ Dashboard container restarted"
else
    echo "❌ Failed to restart dashboard container"
    exit 1
fi

echo ""
echo "⏳ Waiting for dashboard to be ready..."
sleep 5

# Step 4: Verify dashboard is running
echo "🔍 Verifying dashboard status..."
if $DOCKER_COMPOSE ps dashboard | grep -q "Up"; then
    echo "✅ Dashboard container is running"
else
    echo "❌ Dashboard container is not running"
    echo "Checking logs..."
    $DOCKER_COMPOSE logs --tail=20 dashboard
    exit 1
fi

# Step 5: Check if dashboard is accessible
echo "🏥 Checking dashboard health..."
sleep 3
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Dashboard is accessible"
else
    echo "⚠️  Dashboard health check failed (may still be starting)"
    echo "   Check logs: $DOCKER_COMPOSE logs dashboard"
fi

echo ""
echo "========================================="
echo "✅ Frontend Update Complete!"
echo "========================================="
echo ""
echo "📝 Next steps:"
echo "   1. Clear browser cache (Ctrl+Shift+R or Ctrl+F5)"
echo "   2. Check dashboard at http://your-vps-ip:5000"
echo "   3. Verify changes are visible"
echo ""
echo "🔍 To check if changes are loaded:"
echo "   docker exec \$(docker-compose ps -q dashboard) grep -c 'locationsContainer' /app/templates/dashboard.html"
echo ""
