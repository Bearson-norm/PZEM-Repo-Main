#!/bin/bash
# ========================================
# PZEM Monitoring VPS Diagnosis Script
# ========================================
# Script untuk troubleshooting masalah monitoring system
#
# Masalah yang ditemukan:
# - Status: Pending (tidak merespons)
# - Response: N/A
# - Uptime 24 jam: 65.93% (sangat rendah)
# - Banyak red/orange bars di grafik monitoring
#
# ========================================

echo "======================================"
echo " PZEM Monitoring VPS Diagnosis Tool"
echo "======================================"
echo ""

# VPS Configuration
VPS_USER="foom"
VPS_HOST="103.31.39.189"
SSH_KEY="${HOME}/.ssh/foom-vps"
VPS_DEPLOY_DIR="/opt/pzem-monitoring"
DASHBOARD_PORT=5000
DOMAIN="pzem.moof-set.web.id"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Check if SSH key exists
echo -e "${YELLOW}[1/10] Checking SSH Key...${NC}"
if [ -f "$SSH_KEY" ]; then
    echo -e "  ${GREEN}✅ SSH key found: $SSH_KEY${NC}"
else
    echo -e "  ${RED}❌ SSH key not found: $SSH_KEY${NC}"
    echo -e "  ${RED}Please ensure your SSH key exists at the correct path${NC}"
    exit 1
fi

# Test SSH Connection
echo -e "\n${YELLOW}[2/10] Testing SSH Connection...${NC}"
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "echo 'SSH OK'" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ SSH connection successful${NC}"
else
    echo -e "  ${RED}❌ SSH connection failed${NC}"
    echo -e "\n  ${YELLOW}Possible causes:${NC}"
    echo -e "  ${YELLOW}- VPS is down or unreachable${NC}"
    echo -e "  ${YELLOW}- Firewall blocking SSH (port 22)${NC}"
    echo -e "  ${YELLOW}- SSH key not authorized on VPS${NC}"
    echo -e "  ${YELLOW}- Network connectivity issues${NC}"
    exit 1
fi

# Check VPS is reachable
echo -e "\n${YELLOW}[3/10] Pinging VPS...${NC}"
if ping -c 3 "$VPS_HOST" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ VPS is reachable${NC}"
else
    echo -e "  ${YELLOW}⚠️  VPS ping failed (may be normal if ICMP blocked)${NC}"
fi

# Check Docker status
echo -e "\n${YELLOW}[4/10] Checking Docker Status...${NC}"
DOCKER_STATUS=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "docker --version && systemctl is-active docker" 2>&1)
echo -e "  ${CYAN}Docker info:${NC}"
echo -e "  ${GRAY}$DOCKER_STATUS${NC}"

if echo "$DOCKER_STATUS" | grep -q "active"; then
    echo -e "  ${GREEN}✅ Docker service is running${NC}"
else
    echo -e "  ${RED}❌ Docker service is not running${NC}"
fi

# Check Docker Containers
echo -e "\n${YELLOW}[5/10] Checking Docker Containers...${NC}"
CONTAINERS=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>&1)
echo -e "${GRAY}$CONTAINERS${NC}"

CONTAINER_COUNT=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "docker ps --filter 'name=pzem' --quiet | wc -l" 2>&1 | tr -d ' ')
echo -e "\n  ${CYAN}Found $CONTAINER_COUNT PZEM containers running${NC}"

if [ "$CONTAINER_COUNT" -lt 3 ]; then
    echo -e "  ${YELLOW}⚠️  Expected 3 containers (dashboard, mqtt-listener, db) but found $CONTAINER_COUNT${NC}"
else
    echo -e "  ${GREEN}✅ All containers are running${NC}"
fi

# Check Container Health
echo -e "\n${YELLOW}[6/10] Checking Container Health...${NC}"
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" << 'EOF'
cd /opt/pzem-monitoring
echo "Dashboard container:"
docker ps --filter "name=dashboard" --format "Status: {{.Status}}"
echo ""
echo "MQTT Listener container:"
docker ps --filter "name=mqtt" --format "Status: {{.Status}}"
echo ""
echo "Database container:"
docker ps --filter "name=db" --format "Status: {{.Status}}"
EOF

# Check Port Accessibility
echo -e "\n${YELLOW}[7/10] Checking Port Accessibility...${NC}"
echo -e "  ${CYAN}Testing port $DASHBOARD_PORT on VPS...${NC}"

PORT_TEST=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "netstat -tlnp 2>/dev/null | grep :$DASHBOARD_PORT || ss -tlnp 2>/dev/null | grep :$DASHBOARD_PORT" 2>&1)
if [ -n "$PORT_TEST" ]; then
    echo -e "  ${GREEN}✅ Port $DASHBOARD_PORT is listening on VPS${NC}"
    echo -e "  ${GRAY}$PORT_TEST${NC}"
else
    echo -e "  ${RED}❌ Port $DASHBOARD_PORT is NOT listening${NC}"
    echo -e "  ${RED}Dashboard service may not be running properly${NC}"
fi

# Test HTTP Response from VPS (internal)
echo -e "\n${YELLOW}[8/10] Testing HTTP Response (from VPS internal)...${NC}"
HTTP_INTERNAL=$(ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "curl -s -o /dev/null -w '%{http_code}' -m 5 http://localhost:$DASHBOARD_PORT/ || echo 'FAILED'" 2>&1)
if [ "$HTTP_INTERNAL" = "200" ]; then
    echo -e "  ${GREEN}✅ Dashboard responds with HTTP 200 (internal)${NC}"
else
    echo -e "  ${RED}❌ Dashboard not responding (got: $HTTP_INTERNAL)${NC}"
fi

# Test HTTP Response from external
echo -e "\n${YELLOW}[9/10] Testing HTTP Response (from external)...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://$VPS_HOST:$DASHBOARD_PORT/" 2>&1)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "  ${GREEN}✅ Dashboard accessible externally (HTTP $HTTP_CODE)${NC}"
else
    echo -e "  ${RED}❌ Dashboard not accessible externally (got: $HTTP_CODE)${NC}"
    echo -e "\n  ${YELLOW}Possible causes:${NC}"
    echo -e "  ${YELLOW}- Firewall blocking port $DASHBOARD_PORT${NC}"
    echo -e "  ${YELLOW}- Dashboard container not running${NC}"
    echo -e "  ${YELLOW}- Dashboard crashed or error${NC}"
fi

# Test Domain (if configured)
echo -e "\n${YELLOW}[10/10] Testing Domain Access...${NC}"
DOMAIN_CODE=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "https://$DOMAIN" 2>&1)
if [ "$DOMAIN_CODE" = "200" ]; then
    echo -e "  ${GREEN}✅ Domain accessible (HTTPS $DOMAIN_CODE)${NC}"
else
    echo -e "  ${RED}❌ Domain not accessible (got: $DOMAIN_CODE)${NC}"
fi

# Check Recent Logs
echo ""
echo "============================================"
echo " Container Logs (Last 20 lines)"
echo "============================================"

echo -e "\n${YELLOW}--- Dashboard Logs ---${NC}"
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker logs --tail 20 \$(docker ps --filter 'name=dashboard' -q) 2>&1 | tail -20" 2>&1

echo -e "\n${YELLOW}--- MQTT Listener Logs ---${NC}"
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker logs --tail 20 \$(docker ps --filter 'name=mqtt' -q) 2>&1 | tail -20" 2>&1

echo -e "\n${YELLOW}--- Database Logs ---${NC}"
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" "cd $VPS_DEPLOY_DIR && docker logs --tail 20 \$(docker ps --filter 'name=db' -q) 2>&1 | tail -20" 2>&1

# Check VPS Resources
echo -e "\n${YELLOW}--- VPS Resource Usage ---${NC}"
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_HOST" << 'EOF'
echo "Memory Usage:"
free -h | grep -E "Mem|Swap"
echo ""
echo "Disk Usage:"
df -h / | grep -v "Filesystem"
echo ""
echo "CPU Load:"
uptime
EOF

# Summary
echo ""
echo "============================================"
echo " DIAGNOSIS SUMMARY"
echo "============================================"
echo ""
echo -e "${RED}Based on the monitoring screenshot you provided:${NC}"
echo -e "  ${RED}- Status: PENDING (not responding)${NC}"
echo -e "  ${RED}- 24h Uptime: 65.93% (should be >99%)${NC}"
echo -e "  ${RED}- Many red/orange bars in monitoring graph${NC}"
echo ""
echo -e "${YELLOW}Common Causes:${NC}"
echo "  1. Dashboard container crashed or restarting frequently"
echo "  2. Database connection issues"
echo "  3. Memory/resource exhaustion on VPS"
echo "  4. Network connectivity problems"
echo "  5. Firewall blocking external access"
echo ""
echo -e "${YELLOW}Recommended Actions:${NC}"
echo "  1. Check the logs above for errors"
echo "  2. Verify all 3 containers are in 'Up' status"
echo "  3. Check VPS resources: CPU, Memory, Disk"
echo "  4. Test health endpoint: http://$VPS_HOST:$DASHBOARD_PORT/health"
echo "  5. Restart containers if needed: cd $VPS_DEPLOY_DIR && docker-compose restart"
echo ""
echo -e "${CYAN}For detailed fix guides, see:${NC}"
echo "  - .github/DOCKER_STATUS_CHECK_GUIDE.md"
echo "  - pzem-monitoring/V9-Docker/QUICK_FIX_VPS.md"
echo ""
echo "============================================"
