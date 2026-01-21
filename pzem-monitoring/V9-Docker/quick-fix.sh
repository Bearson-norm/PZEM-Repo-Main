#!/bin/bash
# ========================================
# PZEM Quick Fix Script
# ========================================
# Script untuk fix masalah umum pada PZEM Monitoring System
#
# Usage: ./quick-fix.sh [option]
# Options:
#   restart     - Restart all containers
#   rebuild     - Rebuild and restart
#   clearlog    - Clear logs
#   clearcache  - Clear Docker cache
#   reset       - Full reset (WARNING: stops everything)
#   check       - Check system status
# ========================================

set -e

VPS_DEPLOY_DIR="/opt/pzem-monitoring"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo -e "${RED}❌ ERROR: docker-compose not found${NC}"
    exit 1
fi

show_usage() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  restart     - Restart all containers (quick fix)"
    echo "  rebuild     - Rebuild and restart containers"
    echo "  clearlog    - Clear all logs"
    echo "  clearcache  - Clear Docker cache (images, containers)"
    echo "  reset       - Full reset (WARNING: stops everything)"
    echo "  check       - Check system status"
    echo ""
}

check_status() {
    echo -e "${CYAN}=== Checking System Status ===${NC}"
    
    echo -e "\n${YELLOW}Docker Service:${NC}"
    systemctl is-active docker && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Not Running${NC}"
    
    echo -e "\n${YELLOW}Containers:${NC}"
    cd "$VPS_DEPLOY_DIR"
    $DOCKER_COMPOSE ps
    
    echo -e "\n${YELLOW}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    
    echo -e "\n${YELLOW}Port 5000:${NC}"
    if ss -tlnp | grep -q ":5000"; then
        echo -e "${GREEN}✅ Listening${NC}"
    else
        echo -e "${RED}❌ Not Listening${NC}"
    fi
    
    echo -e "\n${YELLOW}Health Check:${NC}"
    if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Healthy${NC}"
        curl -s http://localhost:5000/health | jq . 2>/dev/null || curl -s http://localhost:5000/health
    else
        echo -e "${RED}❌ Unhealthy${NC}"
    fi
}

restart_containers() {
    echo -e "${CYAN}=== Restarting Containers ===${NC}"
    cd "$VPS_DEPLOY_DIR"
    
    echo -e "${YELLOW}Stopping containers...${NC}"
    $DOCKER_COMPOSE down
    
    echo -e "${YELLOW}Starting containers...${NC}"
    $DOCKER_COMPOSE up -d
    
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 20
    
    echo -e "${GREEN}✅ Restart completed${NC}"
    check_status
}

rebuild_containers() {
    echo -e "${CYAN}=== Rebuilding Containers ===${NC}"
    cd "$VPS_DEPLOY_DIR"
    
    echo -e "${YELLOW}Stopping containers...${NC}"
    $DOCKER_COMPOSE down
    
    echo -e "${YELLOW}Rebuilding images...${NC}"
    $DOCKER_COMPOSE build --no-cache
    
    echo -e "${YELLOW}Starting containers...${NC}"
    $DOCKER_COMPOSE up -d
    
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 20
    
    echo -e "${GREEN}✅ Rebuild completed${NC}"
    check_status
}

clear_logs() {
    echo -e "${CYAN}=== Clearing Logs ===${NC}"
    cd "$VPS_DEPLOY_DIR"
    
    # Truncate log files in containers
    echo -e "${YELLOW}Clearing dashboard logs...${NC}"
    docker exec $(docker ps --filter "name=dashboard" -q) sh -c "truncate -s 0 /app/dashboard.log" 2>/dev/null || true
    
    echo -e "${YELLOW}Clearing MQTT logs...${NC}"
    docker exec $(docker ps --filter "name=mqtt" -q) sh -c "truncate -s 0 /app/mqtt_client.log" 2>/dev/null || true
    
    # Clear Docker logs
    echo -e "${YELLOW}Clearing Docker container logs...${NC}"
    for container in $(docker ps -a --filter "name=pzem" -q); do
        truncate -s 0 $(docker inspect --format='{{.LogPath}}' $container) 2>/dev/null || true
    done
    
    echo -e "${GREEN}✅ Logs cleared${NC}"
}

clear_cache() {
    echo -e "${CYAN}=== Clearing Docker Cache ===${NC}"
    
    echo -e "${YELLOW}Pruning unused images...${NC}"
    docker image prune -a -f
    
    echo -e "${YELLOW}Pruning stopped containers...${NC}"
    docker container prune -f
    
    echo -e "${YELLOW}Pruning unused networks...${NC}"
    docker network prune -f
    
    echo -e "${YELLOW}Pruning build cache...${NC}"
    docker builder prune -f
    
    echo -e "${GREEN}✅ Cache cleared${NC}"
    
    echo -e "\n${CYAN}Disk space saved:${NC}"
    df -h /
}

full_reset() {
    echo -e "${RED}=== WARNING: Full Reset ===${NC}"
    echo -e "${YELLOW}This will:${NC}"
    echo "  - Stop all containers"
    echo "  - Remove all containers"
    echo "  - Clear all logs"
    echo "  - Clear Docker cache"
    echo "  - Rebuild everything"
    echo ""
    echo -e "${RED}Database volumes will be preserved${NC}"
    echo ""
    read -p "Are you sure? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
    
    cd "$VPS_DEPLOY_DIR"
    
    # Backup database first
    echo -e "\n${YELLOW}Backing up database...${NC}"
    BACKUP_DIR="${HOME}/.pzem-backups"
    mkdir -p "$BACKUP_DIR"
    
    DB_CONTAINER=$(docker ps --filter "name=db" -q)
    if [ -n "$DB_CONTAINER" ]; then
        docker exec $DB_CONTAINER pg_dump -U postgres pzem_monitoring > "$BACKUP_DIR/backup_before_reset_$(date +%Y%m%d_%H%M%S).sql" 2>/dev/null || true
        echo -e "${GREEN}✅ Database backed up${NC}"
    fi
    
    echo -e "\n${YELLOW}Stopping all containers...${NC}"
    $DOCKER_COMPOSE down
    
    echo -e "${YELLOW}Removing containers...${NC}"
    docker rm -f $(docker ps -a --filter "name=pzem" -q) 2>/dev/null || true
    
    clear_logs
    clear_cache
    
    echo -e "\n${YELLOW}Rebuilding...${NC}"
    $DOCKER_COMPOSE build --no-cache
    
    echo -e "${YELLOW}Starting...${NC}"
    $DOCKER_COMPOSE up -d
    
    echo -e "${YELLOW}Waiting for services...${NC}"
    sleep 30
    
    echo -e "${GREEN}✅ Full reset completed${NC}"
    check_status
}

# Main
if [ ! -d "$VPS_DEPLOY_DIR" ]; then
    echo -e "${RED}❌ ERROR: Directory not found: $VPS_DEPLOY_DIR${NC}"
    exit 1
fi

case "${1:-}" in
    restart)
        restart_containers
        ;;
    rebuild)
        rebuild_containers
        ;;
    clearlog)
        clear_logs
        ;;
    clearcache)
        clear_cache
        ;;
    reset)
        full_reset
        ;;
    check)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
