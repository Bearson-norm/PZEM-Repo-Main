#!/bin/bash
# Deploy otomatis dari GitHub Actions — minimal downtime, DB tidak di-restart
set -euo pipefail

VPS_DEPLOY_DIR="/opt/pzem-monitoring"
BACKUP_DIR="/opt/backups/pzem-monitoring"
PACKAGE_FILE="${1:-$(ls -t /tmp/pzem-monitoring-deploy-*.tar.gz 2>/dev/null | head -1)}"

if [ -z "${PACKAGE_FILE}" ] || [ ! -f "${PACKAGE_FILE}" ]; then
  echo "❌ Package deploy tidak ditemukan"
  exit 1
fi

if command -v docker-compose &>/dev/null; then
  DC="docker-compose"
elif docker compose version &>/dev/null; then
  DC="docker compose"
else
  echo "❌ docker compose tidak ditemukan"
  exit 1
fi

echo "🔧 Deploy PZEM — $(date -Iseconds)"
mkdir -p "${VPS_DEPLOY_DIR}" "${BACKUP_DIR}"
cd "${VPS_DEPLOY_DIR}"

# --- Backup ---
if [ -f ".env" ]; then
  cp ".env" "${BACKUP_DIR}/.env.backup.$(date +%Y%m%d_%H%M%S)"
fi
DB_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'db|postgres' | head -1 || true)
if [ -n "${DB_CONTAINER}" ]; then
  docker exec "${DB_CONTAINER}" pg_dump -U postgres pzem_monitoring \
    > "${BACKUP_DIR}/database_backup_$(date +%Y%m%d_%H%M%S).sql" 2>/dev/null || true
fi

# --- Pastikan DB jalan (tanpa recreate) ---
echo "🗄️  Memastikan database running..."
$DC up -d db
for i in $(seq 1 30); do
  if $DC exec -T db pg_isready -U postgres >/dev/null 2>&1; then
    echo "✅ Database ready"
    break
  fi
  sleep 2
  [ "$i" -eq 30 ] && { echo "❌ Database tidak ready"; $DC logs db --tail=20; exit 1; }
done

# --- Stop app saja (nginx akan 502 sebentar — lebih aman daripada extract saat jalan) ---
echo "⏸️  Stop dashboard & mqtt (DB tetap jalan)..."
$DC stop dashboard mqtt-listener 2>/dev/null || true

# --- Update kode ---
echo "📦 Extract ke ${VPS_DEPLOY_DIR}..."
tar -xzf "${PACKAGE_FILE}" -C "${VPS_DEPLOY_DIR}"
chmod +x *.sh 2>/dev/null || true

# --- Build dengan cache (jauh lebih cepat dari --no-cache) ---
echo "🔨 Build image dashboard & mqtt..."
$DC build dashboard mqtt-listener

# --- Start ulang HANYA app layer (bukan db) ---
echo "🚀 Start dashboard & mqtt..."
$DC up -d --no-deps dashboard mqtt-listener

# --- Tunggu dashboard healthy ---
echo "🏥 Menunggu dashboard..."
HEALTH_OK=false
for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:5000/health/live >/dev/null 2>&1; then
    HEALTH_OK=true
    echo "✅ Dashboard live (~$((i * 3))s)"
    break
  fi
  sleep 3
done

if [ "${HEALTH_OK}" != true ]; then
  echo "❌ Dashboard gagal start — log:"
  $DC ps
  $DC logs dashboard --tail=100
  echo "🔄 Coba recovery otomatis..."
  $DC up -d --no-deps dashboard || true
  sleep 15
  if curl -fsS http://127.0.0.1:5000/health/live >/dev/null 2>&1; then
    echo "✅ Recovery berhasil"
  else
    exit 1
  fi
fi

# --- Nginx reload ---
if command -v nginx >/dev/null 2>&1 && sudo nginx -t >/dev/null 2>&1; then
  sudo systemctl reload nginx && echo "✅ Nginx reloaded"
fi

rm -f "${PACKAGE_FILE}"
echo "✅ Deploy selesai — https://pzem.moof-set.web.id/"
