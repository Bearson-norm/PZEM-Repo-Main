#!/bin/bash
# Diagnosa & pulihkan stack PZEM di VPS jika container tidak jalan
# Usage: bash recover-pzem-vps.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  $1${NC}"; }
ok()    { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

if command -v docker-compose &>/dev/null; then
  DC="docker-compose"
elif docker compose version &>/dev/null; then
  DC="docker compose"
else
  fail "docker-compose tidak ditemukan. Install dulu: apt install docker-compose-plugin"
fi

if ! docker info &>/dev/null; then
  fail "Docker daemon tidak jalan. Jalankan: sudo systemctl start docker"
fi

echo ""
echo "🔍 PZEM VPS Recovery"
echo "===================="
echo ""

# --- 1. Cari lokasi project ---
CANDIDATES=(
  "/opt/pzem-monitoring"
  "/opt"
  "/home/foom/pzem-monitoring"
  "$HOME/pzem-monitoring"
)

PROJECT_DIR=""
for dir in "${CANDIDATES[@]}"; do
  if [ -f "${dir}/docker-compose.yml" ] && [ -d "${dir}/dashboard" ]; then
    PROJECT_DIR="$dir"
    break
  fi
done

if [ -z "$PROJECT_DIR" ]; then
  warn "docker-compose.yml tidak ditemukan di lokasi standar."
  info "Mencari di /opt..."
  FOUND=$(find /opt -maxdepth 3 -name 'docker-compose.yml' 2>/dev/null | head -5)
  if [ -n "$FOUND" ]; then
    echo "$FOUND"
    for f in $FOUND; do
      d=$(dirname "$f")
      if [ -d "$d/dashboard" ]; then
        PROJECT_DIR="$d"
        break
      fi
    done
  fi
fi

if [ -z "$PROJECT_DIR" ]; then
  fail "Project PZEM tidak ditemukan. Cek backup di /opt/pzem-monitoring_backup_* atau deploy ulang."
fi

ok "Project ditemukan: $PROJECT_DIR"
cd "$PROJECT_DIR"

# --- 2. Perbaiki struktur jika file tersebar di /opt (bug deploy lama) ---
if [ "$PROJECT_DIR" = "/opt" ] && [ ! -d "/opt/pzem-monitoring" ]; then
  warn "File mungkin tersebar di /opt — buat folder pzem-monitoring..."
  sudo mkdir -p /opt/pzem-monitoring
  for item in dashboard mqtt shared docker-compose.yml start.sh nginx-pzem.conf; do
    [ -e "/opt/$item" ] && sudo mv "/opt/$item" "/opt/pzem-monitoring/" 2>/dev/null || true
  done
  PROJECT_DIR="/opt/pzem-monitoring"
  cd "$PROJECT_DIR"
  ok "File dipindah ke /opt/pzem-monitoring"
fi

# --- 3. Status container saat ini ---
echo ""
info "Container Docker (semua):"
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -iE 'pzem|dashboard|mqtt|postgres|db' || echo "   (tidak ada container PZEM)"

echo ""
info "Volume data:"
docker volume ls | grep -E 'pgdata|reports' || echo "   (volume pgdata belum ada — akan dibuat saat start)"

# --- 4. Pastikan shared/ ada ---
if [ ! -d "./shared" ]; then
  warn "Folder shared/ tidak ada — buat minimal..."
  mkdir -p shared
  echo '# shared module' > shared/__init__.py
fi

# --- 5. Build & start ---
echo ""
info "Membangun & menjalankan stack..."
$DC build
$DC up -d --force-recreate

info "Menunggu database..."
for i in $(seq 1 30); do
  if $DC exec -T db pg_isready -U postgres &>/dev/null; then
    ok "Database ready"
    break
  fi
  sleep 2
  [ "$i" -eq 30 ] && warn "Database belum ready — lanjut cek dashboard..."
done

info "Menunggu dashboard..."
for i in $(seq 1 24); do
  if curl -fsS http://127.0.0.1:5000/health/live &>/dev/null; then
    ok "Dashboard live"
    break
  fi
  sleep 5
  [ "$i" -eq 24 ] && warn "Dashboard belum merespons — cek log di bawah"
done

echo ""
info "Status akhir:"
$DC ps

echo ""
if curl -fsS http://127.0.0.1:5000/health/live &>/dev/null; then
  ok "Backend OK: http://127.0.0.1:5000"
  if command -v nginx &>/dev/null && sudo nginx -t &>/dev/null; then
    sudo systemctl reload nginx && ok "Nginx reloaded"
  fi
  echo ""
  echo "🌐 Coba buka: https://pzem.moof-set.web.id/"
else
  fail "Dashboard masih tidak merespons. Log:"
  $DC logs dashboard --tail=40
fi
