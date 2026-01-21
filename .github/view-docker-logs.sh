#!/bin/bash
# Script untuk melihat logs dari semua container PZEM Monitoring

echo "========================================"
echo "Docker Logs Viewer - PZEM Monitoring"
echo "========================================"
echo ""

# Warna untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function untuk menampilkan log dengan format yang jelas
show_logs() {
    local container_name=$1
    local service_name=$2
    local lines=${3:-100}  # Default 100 lines
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}📋 Logs: ${GREEN}$service_name${NC} (${container_name})"
    echo -e "${BLUE}========================================${NC}"
    docker logs --tail $lines $container_name 2>&1
    echo ""
}

# Check jika container sedang running
if ! docker ps --format "{{.Names}}" | grep -q "pzem-monitoring"; then
    echo -e "${RED}❌ Tidak ada container PZEM Monitoring yang running${NC}"
    echo "Container yang tersedia:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi

# Menu pilihan
echo "Pilih opsi:"
echo "1. Lihat semua logs (terakhir 100 baris)"
echo "2. Lihat logs Dashboard saja"
echo "3. Lihat logs MQTT Listener saja"
echo "4. Lihat logs Database saja"
echo "5. Follow logs (real-time) - Semua"
echo "6. Follow logs Dashboard (real-time)"
echo "7. Follow logs MQTT Listener (real-time)"
echo "8. Custom (pilih jumlah baris)"
echo ""
read -p "Pilihan [1-8]: " choice

case $choice in
    1)
        echo -e "${GREEN}Menampilkan logs terakhir 100 baris dari semua container...${NC}"
        echo ""
        show_logs "pzem-monitoring-db-1" "Database" 100
        show_logs "pzem-monitoring-dashboard-1" "Dashboard" 100
        show_logs "pzem-monitoring-mqtt-listener-1" "MQTT Listener" 100
        ;;
    2)
        show_logs "pzem-monitoring-dashboard-1" "Dashboard" 100
        ;;
    3)
        show_logs "pzem-monitoring-mqtt-listener-1" "MQTT Listener" 100
        ;;
    4)
        show_logs "pzem-monitoring-db-1" "Database" 100
        ;;
    5)
        echo -e "${GREEN}Following logs dari semua container (Ctrl+C to exit)...${NC}"
        docker-compose logs -f 2>/dev/null || docker compose logs -f
        ;;
    6)
        echo -e "${GREEN}Following logs Dashboard (Ctrl+C to exit)...${NC}"
        docker logs -f pzem-monitoring-dashboard-1
        ;;
    7)
        echo -e "${GREEN}Following logs MQTT Listener (Ctrl+C to exit)...${NC}"
        docker logs -f pzem-monitoring-mqtt-listener-1
        ;;
    8)
        read -p "Masukkan jumlah baris yang ingin ditampilkan: " lines
        echo ""
        show_logs "pzem-monitoring-db-1" "Database" $lines
        show_logs "pzem-monitoring-dashboard-1" "Dashboard" $lines
        show_logs "pzem-monitoring-mqtt-listener-1" "MQTT Listener" $lines
        ;;
    *)
        echo -e "${RED}Pilihan tidak valid${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}✅ Selesai${NC}"