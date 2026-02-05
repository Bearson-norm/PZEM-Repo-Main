#!/bin/bash
# Manual Update Script untuk VPS
# Script ini akan update file dashboard.html secara manual jika deployment otomatis gagal
# Usage: ./manual-update-vps.sh

set -e

echo "🔄 Manual Update Frontend di VPS"
echo "=================================="
echo ""

# Detect docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ ERROR: docker-compose not found"
    exit 1
fi

VPS_DEPLOY_DIR="/opt/pzem-monitoring"
DASHBOARD_FILE="${VPS_DEPLOY_DIR}/dashboard/templates/dashboard.html"

echo "📍 Deployment Directory: ${VPS_DEPLOY_DIR}"
echo ""

# Check if directory exists
if [ ! -d "${VPS_DEPLOY_DIR}" ]; then
    echo "❌ ERROR: Deployment directory not found: ${VPS_DEPLOY_DIR}"
    exit 1
fi

cd "${VPS_DEPLOY_DIR}"

# Check current file
if [ -f "${DASHBOARD_FILE}" ]; then
    CURRENT_SIZE=$(wc -c < "${DASHBOARD_FILE}")
    CURRENT_LINES=$(wc -l < "${DASHBOARD_FILE}")
    CURRENT_FUNCTIONS=$(grep -c "updateLocationPanels" "${DASHBOARD_FILE}" || echo "0")
    
    echo "📄 Current dashboard.html:"
    echo "   - Size: ${CURRENT_SIZE} bytes"
    echo "   - Lines: ${CURRENT_LINES}"
    echo "   - updateLocationPanels: ${CURRENT_FUNCTIONS} occurrences"
    echo "   - Last modified: $(stat -c %y "${DASHBOARD_FILE}" 2>/dev/null || stat -f "%Sm" "${DASHBOARD_FILE}" 2>/dev/null || echo "Unknown")"
    echo ""
    
    if [ "${CURRENT_FUNCTIONS}" -gt 0 ]; then
        echo "✅ File already has new functions!"
        echo "   If frontend still not updated, try:"
        echo "   1. Clear browser cache (Ctrl+Shift+R)"
        echo "   2. Restart dashboard: ${DOCKER_COMPOSE} restart dashboard"
        exit 0
    fi
else
    echo "❌ ERROR: dashboard.html not found!"
    exit 1
fi

# Try to update from git if available
if [ -d ".git" ]; then
    echo "📥 Attempting to pull latest changes from git..."
    git pull origin main || git pull origin master || {
        echo "⚠️  Git pull failed, continuing with manual update..."
    }
    
    # Check if file was updated
    if [ -f "${DASHBOARD_FILE}" ]; then
        NEW_FUNCTIONS=$(grep -c "updateLocationPanels" "${DASHBOARD_FILE}" || echo "0")
        if [ "${NEW_FUNCTIONS}" -gt 0 ]; then
            echo "✅ File updated from git!"
            echo "   - updateLocationPanels: ${NEW_FUNCTIONS} occurrences"
            
            # Restart dashboard
            echo "🔄 Restarting dashboard container..."
            ${DOCKER_COMPOSE} restart dashboard
            sleep 5
            
            echo "✅ Update complete!"
            exit 0
        fi
    fi
fi

# If git didn't work, provide instructions
echo "⚠️  File still outdated after git pull"
echo ""
echo "📝 Manual Update Required:"
echo "   1. Download latest dashboard.html from GitHub:"
echo "      https://raw.githubusercontent.com/YOUR_REPO/main/pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html"
echo ""
echo "   2. Or use SCP to copy from local machine:"
echo "      scp dashboard/templates/dashboard.html foom@YOUR_VPS:/opt/pzem-monitoring/dashboard/templates/"
echo ""
echo "   3. After copying, restart dashboard:"
echo "      cd ${VPS_DEPLOY_DIR}"
echo "      ${DOCKER_COMPOSE} restart dashboard"
echo ""
echo "   4. Verify update:"
echo "      ${DOCKER_COMPOSE} exec dashboard grep -c 'updateLocationPanels' /app/templates/dashboard.html"
echo ""
