#!/bin/bash
# Safe Deployment Script untuk VPS
# Script ini akan backup database yang ada sebelum deploy

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
VPS_USER="foom"
VPS_HOST="103.31.39.189"
VPS_DOMAIN="pzem.moof-set.web.id"
APP_DIR="/home/foom/pzem-monitoring"
BACKUP_DIR="/home/foom/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PZEM Monitoring - Safe VPS Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Backup existing database
print_info "Step 1: Backup existing database..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
    set -e
    
    # Create backup directory if not exists
    mkdir -p /home/foom/backups
    
    # Check if docker-compose is running
    if [ -f "/home/foom/pzem-monitoring/docker-compose.yml" ]; then
        cd /home/foom/pzem-monitoring
        
        # Check if database container exists and is running
        if docker ps | grep -q "postgres\|db"; then
            echo "Backing up existing database..."
            
            # Get database container name
            DB_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "postgres|db" | head -1)
            
            if [ ! -z "$DB_CONTAINER" ]; then
                # Backup database
                TIMESTAMP=$(date +%Y%m%d_%H%M%S)
                BACKUP_FILE="/home/foom/backups/pzem_db_backup_${TIMESTAMP}.sql"
                
                docker exec $DB_CONTAINER pg_dump -U postgres pzem_monitoring > $BACKUP_FILE 2>/dev/null || \
                docker exec $DB_CONTAINER pg_dumpall -U postgres > $BACKUP_FILE 2>/dev/null || \
                echo "Warning: Could not backup database (might not exist yet)"
                
                if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
                    echo "Database backup created: $BACKUP_FILE"
                    # Compress backup
                    gzip -f "$BACKUP_FILE"
                    echo "Backup compressed: ${BACKUP_FILE}.gz"
                else
                    echo "No database found or backup failed (this is OK for first deployment)"
                fi
            fi
        fi
    else
        echo "No existing docker-compose.yml found (first deployment)"
    fi
ENDSSH

print_info "Database backup completed (if database exists)"
echo ""

# Step 2: Create deployment package
print_info "Step 2: Creating deployment package..."
TEMP_DIR=$(mktemp -d)
DEPLOY_PACKAGE="pzem-deploy-${TIMESTAMP}.tar.gz"

# Create .tar.gz excluding unnecessary files
tar --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='node_modules' \
    --exclude='*.log' \
    --exclude='reports/*.pdf' \
    --exclude='.DS_Store' \
    -czf "${TEMP_DIR}/${DEPLOY_PACKAGE}" .

print_info "Deployment package created: ${DEPLOY_PACKAGE}"
echo ""

# Step 3: Upload to VPS
print_info "Step 3: Uploading files to VPS..."
scp "${TEMP_DIR}/${DEPLOY_PACKAGE}" ${VPS_USER}@${VPS_HOST}:/tmp/

# Cleanup local temp
rm -rf "${TEMP_DIR}"

print_info "Files uploaded successfully"
echo ""

# Step 4: Deploy on VPS
print_info "Step 4: Deploying on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << ENDSSH
    set -e
    
    echo "Extracting deployment package..."
    cd /home/foom
    
    # Create app directory if not exists
    mkdir -p ${APP_DIR}
    
    # Backup existing directory if exists
    if [ -d "${APP_DIR}" ] && [ "$(ls -A ${APP_DIR})" ]; then
        echo "Backing up existing application..."
        mv ${APP_DIR} ${APP_DIR}.backup.${TIMESTAMP}
    fi
    
    # Extract new files
    mkdir -p ${APP_DIR}
    cd ${APP_DIR}
    tar -xzf /tmp/${DEPLOY_PACKAGE}
    
    # Cleanup
    rm /tmp/${DEPLOY_PACKAGE}
    
    echo "Files extracted successfully"
ENDSSH

print_info "Files deployed to VPS"
echo ""

# Step 5: Setup and start services
print_info "Step 5: Setting up and starting services..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
    set -e
    cd /home/foom/pzem-monitoring
    
    # Make scripts executable
    chmod +x *.sh
    chmod +x dashboard/*.py
    chmod +x mqtt/*.py
    
    # Stop existing containers (if any)
    echo "Stopping existing containers..."
    docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true
    
    # Build and start new containers
    echo "Building and starting containers..."
    docker-compose up -d --build || docker compose up -d --build
    
    # Wait for services to start
    echo "Waiting for services to start..."
    sleep 15
    
    # Check service status
    echo ""
    echo "Service Status:"
    docker-compose ps || docker compose ps
ENDSSH

print_info "Services started"
echo ""

# Step 6: Verify deployment
print_info "Step 6: Verifying deployment..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
    cd /home/foom/pzem-monitoring
    
    # Check if containers are running
    echo "Checking container status..."
    if docker-compose ps | grep -q "Up" || docker compose ps | grep -q "Up"; then
        echo "✅ Containers are running"
    else
        echo "❌ Some containers failed to start"
        echo "Checking logs..."
        docker-compose logs --tail=50 || docker compose logs --tail=50
        exit 1
    fi
    
    # Check if dashboard is accessible
    echo "Checking dashboard accessibility..."
    sleep 5
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        echo "✅ Dashboard is accessible"
    else
        echo "⚠️  Dashboard might not be ready yet (check logs)"
    fi
ENDSSH

echo ""
print_info "========================================="
print_info "Deployment Summary"
print_info "========================================="
echo ""
echo "VPS: ${VPS_HOST}"
echo "Domain: ${VPS_DOMAIN}"
echo "App Directory: ${APP_DIR}"
echo "Backup Directory: ${BACKUP_DIR}"
echo ""
echo -e "${GREEN}✅ Deployment completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure Nginx reverse proxy (if needed)"
echo "2. Setup SSL certificate (Let's Encrypt)"
echo "3. Configure firewall rules"
echo ""
echo "Useful commands:"
echo "  SSH: ssh ${VPS_USER}@${VPS_HOST}"
echo "  View logs: ssh ${VPS_USER}@${VPS_HOST} 'cd ${APP_DIR} && docker-compose logs -f'"
echo "  Restart: ssh ${VPS_USER}@${VPS_HOST} 'cd ${APP_DIR} && docker-compose restart'"
echo ""
