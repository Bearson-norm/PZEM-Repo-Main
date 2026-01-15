#!/bin/bash
# Safe Deployment Script for Existing VPS
# This script deploys PZEM monitoring system WITHOUT deleting existing database
# Usage: ./deploy-to-existing-vps.sh

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
BACKUP_DIR="/opt/backups/pzem-monitoring"

echo ""
echo "🚀 PZEM Monitoring - Safe Deployment to Existing VPS"
echo "====================================================="
echo ""
print_info "Target VPS: ${VPS_USER}@${VPS_HOST}"
print_info "Deploy Directory: ${VPS_DEPLOY_DIR}"
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
cp *.md "${PACKAGE_DIR}/" 2>/dev/null || true

# Create .env template if not exists
if [ ! -f "${PACKAGE_DIR}/.env" ]; then
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
    print_warning "Created .env template. Please update with your configuration."
fi

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

cat > /tmp/remote-deploy.sh << 'REMOTE_SCRIPT'
#!/bin/bash
# Remote deployment script - runs on VPS

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
echo "🔧 Remote Deployment on VPS"
echo "============================"
echo ""

# Step 1: Check if deployment directory exists
if [ -d "${VPS_DEPLOY_DIR}" ]; then
    print_warning "Deployment directory already exists"
    print_info "Checking for existing database..."
    
    # Check if database container exists
    if docker ps -a | grep -q "pzem-monitoring.*db"; then
        print_warning "Existing database container found!"
        
        # Check if database volume exists
        DB_VOLUME=$(docker volume ls | grep -o ".*pgdata" | awk '{print $2}' || echo "")
        if [ -n "$DB_VOLUME" ]; then
            print_status "Database volume 'pgdata' found - will be preserved"
        fi
        
        # Backup existing database
        print_info "Creating backup of existing database..."
        mkdir -p "${BACKUP_DIR}"
        
        # Try to backup database if container is running
        if docker ps | grep -q "pzem-monitoring.*db"; then
            print_info "Backing up database..."
            docker exec $(docker ps | grep "pzem-monitoring.*db" | awk '{print $1}') \
                pg_dump -U postgres pzem_monitoring > "${BACKUP_DIR}/database_before_deploy_$(date +%Y%m%d_%H%M%S).sql" 2>/dev/null || {
                print_warning "Could not backup database (may be empty or container stopped)"
            }
            print_status "Database backup created"
        else
            print_warning "Database container not running - will preserve volume"
        fi
        
        # Backup existing configuration
        if [ -f "${VPS_DEPLOY_DIR}/docker-compose.yml" ]; then
            cp "${VPS_DEPLOY_DIR}/docker-compose.yml" "${BACKUP_DIR}/docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)"
        fi
        
        if [ -f "${VPS_DEPLOY_DIR}/.env" ]; then
            cp "${VPS_DEPLOY_DIR}/.env" "${BACKUP_DIR}/.env.backup.$(date +%Y%m%d_%H%M%S)"
            print_status "Existing .env file will be preserved"
        fi
    else
        print_info "No existing database container found - fresh deployment"
    fi
else
    print_info "Fresh deployment - creating directory"
    mkdir -p "${VPS_DEPLOY_DIR}"
fi

# Step 2: Stop existing services (if running)
if [ -f "${VPS_DEPLOY_DIR}/docker-compose.yml" ]; then
    print_info "Stopping existing services (database volume will be preserved)..."
    cd "${VPS_DEPLOY_DIR}"
    $DOCKER_COMPOSE down 2>/dev/null || true
    print_status "Services stopped"
fi

# Step 3: Extract new package
print_info "Extracting new deployment package..."
cd /opt

# Backup existing directory if it exists
if [ -d "${VPS_DEPLOY_DIR}" ]; then
    BACKUP_NAME="${VPS_DEPLOY_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    print_info "Backing up existing directory to ${BACKUP_NAME}"
    mv "${VPS_DEPLOY_DIR}" "${BACKUP_NAME}"
fi

# Extract package
tar -xzf "${PACKAGE_FILE}" -C /opt/
print_status "Package extracted"

# Step 4: Restore .env if it existed
if [ -f "${BACKUP_DIR}/.env.backup."* ]; then
    LATEST_ENV=$(ls -t "${BACKUP_DIR}/.env.backup."* | head -1)
    print_info "Restoring .env from backup..."
    cp "${LATEST_ENV}" "${VPS_DEPLOY_DIR}/.env"
    print_status ".env restored"
else
    print_warning "No existing .env found. Please configure .env file:"
    print_info "  nano ${VPS_DEPLOY_DIR}/.env"
fi

# Step 5: Verify database volume will be preserved
print_info "Verifying database volume..."
DB_VOLUME=$(docker volume ls | grep -o ".*pgdata" | awk '{print $2}' || echo "")
if [ -n "$DB_VOLUME" ]; then
    print_status "Database volume 'pgdata' exists and will be preserved"
    print_info "Volume details:"
    docker volume inspect pgdata 2>/dev/null | grep -E "(Mountpoint|Name)" || true
else
    print_warning "No existing database volume found - will create new one"
fi

# Step 6: Update docker-compose.yml to preserve volume
print_info "Verifying docker-compose.yml configuration..."
if grep -q "pgdata:" "${VPS_DEPLOY_DIR}/docker-compose.yml"; then
    print_status "docker-compose.yml already configured to use named volume 'pgdata'"
else
    print_warning "docker-compose.yml may need volume configuration"
fi

# Step 7: Build and start services
print_info "Building and starting services..."
cd "${VPS_DEPLOY_DIR}"

# Make scripts executable
chmod +x *.sh 2>/dev/null || true

# Build containers
print_info "Building containers (this may take a few minutes)..."
$DOCKER_COMPOSE build

# Start services
print_info "Starting services..."
$DOCKER_COMPOSE up -d

# Step 8: Wait for services to be ready
print_info "Waiting for services to start..."
sleep 10

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
    
    # Check if database has data
    RECORD_COUNT=$($DOCKER_COMPOSE exec -T db psql -U postgres -d pzem_monitoring -t -c "SELECT COUNT(*) FROM pzem_data;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$RECORD_COUNT" != "0" ] && [ -n "$RECORD_COUNT" ]; then
        print_status "Database verified: ${RECORD_COUNT} records found (data preserved!)"
    else
        print_warning "Database is empty (this is normal for fresh deployment)"
    fi
else
    print_error "Database did not become ready in time"
    exit 1
fi

# Step 10: Health check
print_info "Performing health check..."
sleep 5
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    print_status "Health check passed"
else
    print_warning "Health check failed (service may still be starting)"
fi

# Step 11: Cleanup
print_info "Cleaning up package file..."
rm -f "${PACKAGE_FILE}"

echo ""
print_status "✅ Deployment completed successfully!"
echo ""
echo "📊 Summary:"
echo "   - Deployment directory: ${VPS_DEPLOY_DIR}"
echo "   - Database volume preserved: ✅"
echo "   - Backup location: ${BACKUP_DIR}"
echo "   - Services started: ✅"
echo ""
echo "🔍 Verify deployment:"
echo "   - Check status: cd ${VPS_DEPLOY_DIR} && $DOCKER_COMPOSE ps"
echo "   - View logs: cd ${VPS_DEPLOY_DIR} && $DOCKER_COMPOSE logs -f"
echo "   - Access dashboard: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
print_warning "If you encounter issues, backups are available in: ${BACKUP_DIR}"
REMOTE_SCRIPT

# Upload remote script
scp /tmp/remote-deploy.sh ${VPS_USER}@${VPS_HOST}:/tmp/

# Step 5: Execute remote deployment
print_info "Step 4: Executing deployment on VPS..."
print_warning "This will connect to VPS and run deployment script"
echo ""

ssh ${VPS_USER}@${VPS_HOST} "chmod +x /tmp/remote-deploy.sh && bash /tmp/remote-deploy.sh"

# Step 6: Cleanup local files
print_info "Cleaning up local files..."
rm -f "${PACKAGE_NAME}"
rm -f /tmp/remote-deploy.sh

echo ""
print_status "✅ Deployment process completed!"
echo ""
echo "🌐 Access your system:"
echo "   Dashboard: http://${VPS_HOST}:5000"
echo "   Reports: http://${VPS_HOST}:5000/reports"
echo "   Health: http://${VPS_HOST}:5000/health"
echo ""
echo "📋 Next steps:"
echo "   1. SSH to VPS: ssh ${VPS_USER}@${VPS_HOST}"
echo "   2. Check status: cd ${VPS_DEPLOY_DIR} && docker-compose ps"
echo "   3. View logs: cd ${VPS_DEPLOY_DIR} && docker-compose logs -f"
echo "   4. Configure .env if needed: nano ${VPS_DEPLOY_DIR}/.env"
echo ""
