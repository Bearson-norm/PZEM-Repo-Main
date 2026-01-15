#!/bin/bash
# Script untuk verifikasi setelah update

echo "🔍 Verifying Update..."
echo "======================"
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
echo "1️⃣ Container Status:"
$DOCKER_COMPOSE ps
echo ""

# 2. Check database connection
echo "2️⃣ Database Connection:"
if $DOCKER_COMPOSE exec -T db pg_isready -U postgres > /dev/null 2>&1;
    echo "✅ Database is ready"
else
    echo "❌ Database is not ready"
fi
echo ""

# 3. Check database data
echo "3️⃣ Database Data:"
RECORD_COUNT=$($DOCKER_COMPOSE exec -T db psql -U postgres -d pzem_monitoring -t -c "SELECT COUNT(*) FROM pzem_data;" 2>/dev/null | tr -d ' ' || echo "0")
if [ "$RECORD_COUNT" != "0" ] && [ -n "$RECORD_COUNT" ]; then
    echo "✅ Database has data: $RECORD_COUNT records"
else
    echo "⚠️  Database is empty or cannot be accessed"
fi
echo ""

# 4. Check dashboard health
echo "4️⃣ Dashboard Health:"
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Dashboard is healthy"
    curl -s http://localhost:5000/health | head -5
else
    echo "❌ Dashboard health check failed"
    echo "   Checking logs..."
    $DOCKER_COMPOSE logs dashboard --tail=20
fi
echo ""

# 5. Check recent logs for errors
echo "5️⃣ Recent Logs (checking for errors):"
$DOCKER_COMPOSE logs --tail=10 | grep -i error || echo "   No errors found in recent logs"
echo ""

# 6. Check backup
echo "6️⃣ Backup Status:"
if [ -d "/opt/backups/pzem-monitoring" ]; then
    BACKUP_COUNT=$(ls -1 /opt/backups/pzem-monitoring/*.sql 2>/dev/null | wc -l)
    echo "✅ Backup directory exists: $BACKUP_COUNT backup(s) found"
    ls -lh /opt/backups/pzem-monitoring/*.sql 2>/dev/null | tail -3
else
    echo "⚠️  Backup directory not found"
fi
echo ""

echo "✅ Verification complete!"
echo ""
echo "🌐 Access dashboard: http://$(hostname -I | awk '{print $1}'):5000"











