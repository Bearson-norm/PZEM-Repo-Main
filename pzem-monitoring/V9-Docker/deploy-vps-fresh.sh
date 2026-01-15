#!/bin/bash
# Fresh Deployment Script for VPS
# Deploys PZEM monitoring system with fresh database
# Usage: ./deploy-vps-fresh.sh

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# VPS Configuration
VPS_USER="foom"
VPS_HOST="103.31.39.189"
VPS_DEPLOY_DIR="/opt/pzem-monitoring"
DOMAIN="pzem.moof-set.web.id"
BACKUP_DIR="/opt/backups/pzem-monitoring"

echo ""
echo "🚀 PZEM Monitoring - Fresh Deployment to VPS"
echo "=============================================="
echo ""
print_info "Target VPS: ${VPS_USER}@${VPS_HOST}"
print_info "Deploy Directory: ${VPS_DEPLOY_DIR}"
print_info "Domain: ${DOMAIN}"
echo ""

# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "docker-compose not found. Please install docker-compose first."
    exit 1
fi

# Step 1: Check if we're in the project directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi

# Step 2: Create deployment package
print_info "Step 1: Creating deployment package..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="pzem-monitoring-deploy-${TIMESTAMP}.tar.gz"

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="${TEMP_DIR}/pzem-monitoring"

mkdir -p "${PACKAGE_DIR}"

# Copy necessary files
print_info "Copying files to package..."
cp -r dashboard "${PACKAGE_DIR}/"
cp -r mqtt "${PACKAGE_DIR}/"
cp docker-compose.yml "${PACKAGE_DIR}/"
cp start.sh "${PACKAGE_DIR}/"
cp nginx-pzem.conf "${PACKAGE_DIR}/" 2>/dev/null || true
cp *.md "${PACKAGE_DIR}/" 2>/dev/null || true

# Create .env template
cat > "${PACKAGE_DIR}/.env" << 'EOF'
# Database Configuration
DB_HOST=db
DB_NAME=pzem_monitoring
DB_USER=postgres
DB_PASS=Admin123

# PLN Tariff Configuration
PLN_TARIFF_CLASS=R1
PLN_PPN_PERCENT=0.11

# MQTT Configuration (update with your broker)
MQTT_BROKER=your-mqtt-broker-ip
MQTT_PORT=1883
MQTT_TOPIC=energy/pzem/data
EOF

print_status "Package created with .env template"

# Create package
cd "${TEMP_DIR}"
tar -czf "${PACKAGE_NAME}" pzem-monitoring/
mv "${PACKAGE_NAME}" "${OLDPWD}/"
cd "${OLDPWD}"

print_status "Package created: ${PACKAGE_NAME}"
rm -rf "${TEMP_DIR}"

# Step 3: Upload to VPS
print_info "Step 2: Uploading package to VPS..."
print_warning "You will be prompted for SSH password (or use SSH key if configured)"

scp "${PACKAGE_NAME}" ${VPS_USER}@${VPS_HOST}:/tmp/

print_status "Package uploaded to VPS"

# Step 4: Create remote deployment script
print_info "Step 3: Creating remote deployment script..."

cat > /tmp/remote-deploy-fresh.sh << 'REMOTE_SCRIPT'
#!/bin/bash
# Remote deployment script - runs on VPS
# This script will DELETE existing database and create fresh deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

VPS_DEPLOY_DIR="/opt/pzem-monitoring"
BACKUP_DIR="/opt/backups/pzem-monitoring"
DOMAIN="pzem.moof-set.web.id"
PACKAGE_FILE=$(ls /tmp/pzem-monitoring-deploy-*.tar.gz | head -1)

# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "docker-compose not found on VPS"
    exit 1
fi

echo ""
echo "🔧 Fresh Deployment on VPS"
echo "=========================="
echo ""
print_warning "⚠️  WARNING: This will DELETE existing database!"
print_warning "⚠️  Make sure you have backups if needed!"
echo ""

# Step 1: Backup existing database (if exists)
if [ -d "${VPS_DEPLOY_DIR}" ]; then
    print_info "Existing deployment found - creating backup..."
    mkdir -p "${BACKUP_DIR}"
    
    # Check if database container exists and is running
    if docker ps | grep -q "pzem-monitoring.*db\|.*db.*pzem"; then
        DB_CONTAINER=$(docker ps | grep -E "pzem-monitoring.*db|.*db.*pzem" | awk '{print $1}' | head -1)
        if [ -n "$DB_CONTAINER" ]; then
            print_info "Backing up existing database..."
            docker exec ${DB_CONTAINER} pg_dump -U postgres pzem_monitoring > "${BACKUP_DIR}/database_backup_$(date +%Y%m%d_%H%M%S).sql" 2>/dev/null || {
                print_warning "Could not backup database (may be empty)"
            }
            print_status "Database backup created"
        fi
    fi
    
    # Backup existing configuration
    if [ -f "${VPS_DEPLOY_DIR}/.env" ]; then
        cp "${VPS_DEPLOY_DIR}/.env" "${BACKUP_DIR}/.env.backup.$(date +%Y%m%d_%H%M%S)"
        print_status "Configuration backed up"
    fi
fi

# Step 2: Stop and remove existing services
if [ -d "${VPS_DEPLOY_DIR}" ] && [ -f "${VPS_DEPLOY_DIR}/docker-compose.yml" ]; then
    print_info "Stopping existing services..."
    cd "${VPS_DEPLOY_DIR}"
    $DOCKER_COMPOSE down -v 2>/dev/null || true
    print_status "Existing services stopped and volumes removed"
fi

# Step 3: Remove existing deployment directory
if [ -d "${VPS_DEPLOY_DIR}" ]; then
    print_info "Removing existing deployment directory..."
    BACKUP_NAME="${VPS_DEPLOY_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    mv "${VPS_DEPLOY_DIR}" "${BACKUP_NAME}"
    print_status "Existing directory backed up to ${BACKUP_NAME}"
fi

# Step 4: Extract new package
print_info "Extracting new deployment package..."
cd /opt
tar -xzf "${PACKAGE_FILE}"
print_status "Package extracted"

# Step 5: Setup .env
if [ -f "${BACKUP_DIR}/.env.backup."* ]; then
    LATEST_ENV=$(ls -t "${BACKUP_DIR}/.env.backup."* | head -1)
    print_info "Restoring .env from backup..."
    cp "${LATEST_ENV}" "${VPS_DEPLOY_DIR}/.env"
    print_status ".env restored from backup"
else
    print_warning "No existing .env found. Using template."
    print_info "Please update .env file if needed:"
    print_info "  nano ${VPS_DEPLOY_DIR}/.env"
fi

# Step 6: Make scripts executable
chmod +x ${VPS_DEPLOY_DIR}/*.sh 2>/dev/null || true

# Step 7: Build and start services
print_info "Building containers (this may take a few minutes)..."
cd "${VPS_DEPLOY_DIR}"
$DOCKER_COMPOSE build

print_info "Starting services..."
$DOCKER_COMPOSE up -d

# Step 8: Wait for services to be ready
print_info "Waiting for services to start..."
sleep 15

# Step 9: Verify database
print_info "Verifying database connection..."
MAX_RETRIES=30
RETRY_COUNT=0
DB_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $DOCKER_COMPOSE exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        DB_READY=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ "$DB_READY" = true ]; then
    print_status "Database is ready"
    
    # Check database
    RECORD_COUNT=$($DOCKER_COMPOSE exec -T db psql -U postgres -d pzem_monitoring -t -c "SELECT COUNT(*) FROM pzem_data;" 2>/dev/null | tr -d ' ' || echo "0")
    print_info "Database records: ${RECORD_COUNT} (fresh database)"
else
    print_error "Database did not become ready in time"
    exit 1
fi

# Step 10: Setup Nginx (if not exists)
print_info "Setting up Nginx configuration..."
NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"

if [ ! -f "${NGINX_CONF}" ]; then
    print_info "Creating Nginx configuration..."
    sudo cp "${VPS_DEPLOY_DIR}/nginx-pzem.conf" "${NGINX_CONF}" 2>/dev/null || {
        print_warning "Could not copy nginx config (may need manual setup)"
        print_info "Nginx config template available at: ${VPS_DEPLOY_DIR}/nginx-pzem.conf"
    }
    
    # Create symlink if not exists
    if [ ! -L "/etc/nginx/sites-enabled/${DOMAIN}" ]; then
        sudo ln -s "${NGINX_CONF}" "/etc/nginx/sites-enabled/${DOMAIN}" 2>/dev/null || {
            print_warning "Could not create nginx symlink (may need sudo)"
        }
    fi
    
    # Test nginx config
    if sudo nginx -t 2>/dev/null; then
        print_status "Nginx configuration valid"
        print_info "Reload nginx: sudo systemctl reload nginx"
    else
        print_warning "Nginx configuration test failed - check manually"
    fi
else
    print_info "Nginx configuration already exists"
fi

# Step 11: Health check
print_info "Performing health check..."
sleep 5
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    print_status "Health check passed"
else
    print_warning "Health check failed (service may still be starting)"
fi

# Step 12: Cleanup
print_info "Cleaning up package file..."
rm -f "${PACKAGE_FILE}"

echo ""
print_status "✅ Fresh deployment completed successfully!"
echo ""
echo "📊 Summary:"
echo "   - Deployment directory: ${VPS_DEPLOY_DIR}"
echo "   - Database: Fresh (empty)"
echo "   - Backup location: ${BACKUP_DIR}"
echo "   - Services started: ✅"
echo "   - Domain: ${DOMAIN}"
echo ""
echo "🔍 Verify deployment:"
echo "   - Check status: cd ${VPS_DEPLOY_DIR} && $DOCKER_COMPOSE ps"
echo "   - View logs: cd ${VPS_DEPLOY_DIR} && $DOCKER_COMPOSE logs -f"
echo "   - Access dashboard: http://$(hostname -I | awk '{print $1}'):5000"
echo "   - Domain: http://${DOMAIN} (after nginx setup)"
echo ""
print_warning "⚠️  Next steps:"
echo "   1. Update .env file with your MQTT broker settings"
echo "   2. Setup SSL certificate for ${DOMAIN}:"
echo "      sudo certbot --nginx -d ${DOMAIN}"
echo "   3. Reload nginx: sudo systemctl reload nginx"
echo ""
REMOTE_SCRIPT

# Upload remote script
scp /tmp/remote-deploy-fresh.sh ${VPS_USER}@${VPS_HOST}:/tmp/

# Step 5: Execute remote deployment
print_info "Step 4: Executing deployment on VPS..."
print_warning "⚠️  WARNING: This will DELETE existing database!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    print_error "Deployment cancelled"
    exit 1
fi

ssh ${VPS_USER}@${VPS_HOST} "chmod +x /tmp/remote-deploy-fresh.sh && bash /tmp/remote-deploy-fresh.sh"

# Step 6: Cleanup local files
print_info "Cleaning up local files..."
rm -f "${PACKAGE_NAME}"
rm -f /tmp/remote-deploy-fresh.sh

echo ""
print_status "✅ Deployment process completed!"
echo ""
echo "🌐 Access your system:"
echo "   Dashboard: http://${VPS_HOST}:5000"
echo "   Domain: http://${DOMAIN} (after nginx & SSL setup)"
echo "   Reports: http://${VPS_HOST}:5000/reports"
echo "   Health: http://${VPS_HOST}:5000/health"
echo ""
echo "📋 Next steps:"
echo "   1. SSH to VPS: ssh ${VPS_USER}@${VPS_HOST}"
echo "   2. Update .env: nano ${VPS_DEPLOY_DIR}/.env"
echo "   3. Setup SSL: sudo certbot --nginx -d ${DOMAIN}"
echo "   4. Reload nginx: sudo systemctl reload nginx"
echo "   5. Check status: cd ${VPS_DEPLOY_DIR} && docker-compose ps"
echo ""
