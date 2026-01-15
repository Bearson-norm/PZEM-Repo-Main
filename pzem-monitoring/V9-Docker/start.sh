#!/bin/bash
# PZEM 3-Phase Monitoring System Startup Script

echo "🔋 PZEM 3-Phase Energy Monitoring System"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Detect docker-compose command (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found. Please install docker-compose first."
    exit 1
fi

echo "🐳 Starting Docker containers..."
$DOCKER_COMPOSE up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "🔍 Checking service status..."
echo "Database:        $($DOCKER_COMPOSE ps -q db > /dev/null && echo '✅ Running' || echo '❌ Failed')"
echo "Dashboard:       $($DOCKER_COMPOSE ps -q dashboard > /dev/null && echo '✅ Running' || echo '❌ Failed')"
echo "MQTT Listener:   $($DOCKER_COMPOSE ps -q mqtt-listener > /dev/null && echo '✅ Running' || echo '❌ Failed')"

echo ""
echo "🌐 Service URLs:"
echo "Main Dashboard:     http://localhost:5000"
echo "Report Generator:   http://localhost:5000/reports"
echo "System Health:      http://localhost:5000/health"

echo ""
echo "📊 Useful Commands:"
echo "View logs:          $DOCKER_COMPOSE logs -f"
echo "Stop services:      $DOCKER_COMPOSE down"
echo "Restart services:   $DOCKER_COMPOSE restart"
echo "View status:        $DOCKER_COMPOSE ps"

echo ""
echo "✅ System startup complete!"
echo "💡 Tip: Check the logs if services are not responding: $DOCKER_COMPOSE logs -f"
