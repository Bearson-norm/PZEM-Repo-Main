#!/bin/bash
# Quick fix script untuk update.sh di VPS
# Copy-paste script ini ke VPS dan jalankan

cd /opt/pzem-monitoring || exit 1

# Backup
cp update.sh update.sh.backup

# Fix line endings dulu
sed -i 's/\r$//' update.sh

# Tambahkan auto-detect setelah line 6 (setelah print_info function)
cat > /tmp/update_fix.txt << 'FIXEOF'
# Detect docker-compose command (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "docker-compose not found. Please install docker-compose first."
    exit 1
fi

FIXEOF

# Insert setelah line 6
sed -i '6r /tmp/update_fix.txt' update.sh

# Replace semua docker-compose dengan $DOCKER_COMPOSE (kecuali yang di comment/echo)
# Hati-hati: hanya replace di command, bukan di string
sed -i 's/docker-compose up/$DOCKER_COMPOSE up/g' update.sh
sed -i 's/docker-compose down/$DOCKER_COMPOSE down/g' update.sh
sed -i 's/docker-compose ps/$DOCKER_COMPOSE ps/g' update.sh
sed -i 's/docker-compose pull/$DOCKER_COMPOSE pull/g' update.sh
sed -i 's/docker-compose build/$DOCKER_COMPOSE build/g' update.sh
sed -i 's/docker-compose exec/$DOCKER_COMPOSE exec/g' update.sh
sed -i 's/docker-compose images/$DOCKER_COMPOSE images/g' update.sh
sed -i 's/docker-compose logs/$DOCKER_COMPOSE logs/g' update.sh

# Fix echo statements yang masih hardcoded
sed -i 's|echo "   - Check logs: docker-compose|echo "   - Check logs: $DOCKER_COMPOSE|g' update.sh
sed -i 's|echo "   - Check status: docker-compose|echo "   - Check status: $DOCKER_COMPOSE|g' update.sh

chmod +x update.sh

echo "✅ update.sh sudah diperbaiki!"
echo "📝 Backup tersimpan di: update.sh.backup"
echo ""
echo "🧪 Test dengan:"
echo "   ./update.sh"











