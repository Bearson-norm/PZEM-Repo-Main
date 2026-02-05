#!/bin/bash
# Quick Fix Script untuk Update Frontend di VPS
# Script ini akan update dashboard.html secara manual jika deployment gagal
# Usage: ./quick-fix-vps.sh

set -e

echo "🔧 Quick Fix: Update Frontend di VPS"
echo "====================================="
echo ""

VPS_DEPLOY_DIR="/opt/pzem-monitoring"
DASHBOARD_FILE="${VPS_DEPLOY_DIR}/dashboard/templates/dashboard.html"

# Detect docker-compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ ERROR: docker-compose not found"
    exit 1
fi

cd "${VPS_DEPLOY_DIR}" || {
    echo "❌ ERROR: Cannot access ${VPS_DEPLOY_DIR}"
    exit 1
}

echo "📍 Working directory: ${VPS_DEPLOY_DIR}"
echo ""

# Check current state
if [ -f "${DASHBOARD_FILE}" ]; then
    CURRENT_FUNCTIONS=$(grep -c "updateLocationPanels" "${DASHBOARD_FILE}" 2>/dev/null || echo "0")
    CURRENT_SIZE=$(wc -c < "${DASHBOARD_FILE}")
    CURRENT_LINES=$(wc -l < "${DASHBOARD_FILE}")
    
    echo "📄 Current dashboard.html:"
    echo "   - Size: ${CURRENT_SIZE} bytes"
    echo "   - Lines: ${CURRENT_LINES}"
    echo "   - updateLocationPanels: ${CURRENT_FUNCTIONS} occurrences"
    echo ""
    
    if [ "${CURRENT_FUNCTIONS}" -gt 0 ]; then
        echo "✅ File sudah memiliki fungsi baru!"
        echo "   Jika frontend masih belum ter-update:"
        echo "   1. Clear browser cache (Ctrl+Shift+R atau Ctrl+F5)"
        echo "   2. Restart dashboard: ${DOCKER_COMPOSE} restart dashboard"
        exit 0
    fi
else
    echo "❌ ERROR: dashboard.html tidak ditemukan!"
    exit 1
fi

# Try git pull if .git exists
if [ -d ".git" ]; then
    echo "📥 Mencoba pull dari git..."
    if git pull origin main 2>/dev/null || git pull origin master 2>/dev/null; then
        echo "✅ Git pull berhasil"
        
        # Check again
        NEW_FUNCTIONS=$(grep -c "updateLocationPanels" "${DASHBOARD_FILE}" 2>/dev/null || echo "0")
        if [ "${NEW_FUNCTIONS}" -gt 0 ]; then
            echo "✅ File ter-update dari git!"
            echo "🔄 Restarting dashboard..."
            ${DOCKER_COMPOSE} restart dashboard
            sleep 3
            echo "✅ Update selesai!"
            exit 0
        fi
    else
        echo "⚠️  Git pull gagal atau tidak ada perubahan"
    fi
fi

# If still outdated, provide manual instructions
echo ""
echo "⚠️  File masih outdated setelah git pull"
echo ""
echo "📝 SOLUSI MANUAL:"
echo ""
echo "Opsi 1: Download dari GitHub (Paling Mudah)"
echo "--------------------------------------------"
echo "cd ${VPS_DEPLOY_DIR}/dashboard/templates"
echo "cp dashboard.html dashboard.html.backup"
echo "curl -o dashboard.html https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html"
echo "cd ${VPS_DEPLOY_DIR}"
echo "${DOCKER_COMPOSE} restart dashboard"
echo ""
echo "Opsi 2: Copy via SCP dari Local Machine"
echo "----------------------------------------"
echo "# Dari local machine (Windows dengan Git Bash atau WSL):"
echo "scp pzem-monitoring/V9-Docker/dashboard/templates/dashboard.html foom@YOUR_VPS_IP:${VPS_DEPLOY_DIR}/dashboard/templates/"
echo "# Lalu di VPS:"
echo "cd ${VPS_DEPLOY_DIR}"
echo "${DOCKER_COMPOSE} restart dashboard"
echo ""
echo "Opsi 3: Edit Manual (Tidak Disarankan)"
echo "----------------------------------------"
echo "File harus memiliki minimal 2600+ lines dan fungsi updateLocationPanels"
echo ""
echo "Setelah update, verifikasi:"
echo "  grep -c 'updateLocationPanels' ${DASHBOARD_FILE}"
echo "  # Output harus > 0"
echo ""
