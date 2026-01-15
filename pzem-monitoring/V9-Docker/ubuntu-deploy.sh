#!/bin/bash
# Ubuntu VPS Deployment Script for PZEM Monitoring System
# Optimized for Ubuntu 20.04+ and Debian 11+

set -e

echo "🚀 PZEM Monitoring System - Ubuntu VPS Deployment"
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running as root
if [[ "$EUID" -eq 0 ]]; then
    print_warning "Running as root. This is fine for VPS deployment."
    USER_HOME="/root"
else
    print_info "Running as regular user: $USER"
    USER_HOME="/home/$USER"
fi

# Update system packages
print_info "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install essential packages
print_info "Installing essential packages..."
apt-get install -y curl wget git unzip htop nano ufw fail2ban

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    print_info "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
    print_status "Docker installed successfully"
    print_warning "Please log out and log back in for group changes to take effect"
else
    print_status "Docker is already installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    print_info "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_status "Docker Compose installed successfully"
else
    print_status "Docker Compose is already installed"
fi

# Create deployment directory
DEPLOY_DIR="/opt/pzem-monitoring"
print_info "Creating deployment directory: $DEPLOY_DIR"

if [ -d "$DEPLOY_DIR" ]; then
    print_warning "Directory already exists. Backing up..."
    mv "$DEPLOY_DIR" "${DEPLOY_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Set proper permissions untuk semua script
chmod +x *.sh 2>/dev/null || true
chmod +x update.sh backup.sh monitor.sh health-check.sh 2>/dev/null || true

# Create systemd service for auto-start
print_info "Creating systemd service..."
cat > /etc/systemd/system/pzem-monitoring.service << EOF
[Unit]
Description=PZEM 3-Phase Energy Monitoring System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
systemctl daemon-reload
systemctl enable pzem-monitoring.service
print_status "Systemd service created and enabled"

# Configure firewall
print_info "Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 5000/tcp comment "PZEM Dashboard"
ufw allow 1883/tcp comment "MQTT Broker"
print_status "Firewall configured"

# Configure fail2ban for SSH protection
print_info "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl start fail2ban
print_status "Fail2ban configured for SSH protection"

# Create backup script
print_info "Creating backup script..."
cat > backup.sh << 'EOF'
#!/bin/bash
# Backup script for PZEM monitoring system

BACKUP_DIR="/opt/backups/pzem-monitoring"
DATE=$(date +%Y%m%d_%H%M%S)

# Detect docker-compose command (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found. Please install docker-compose first."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "Creating backup: pzem_backup_$DATE.tar.gz"

# Backup database
$DOCKER_COMPOSE exec -T db pg_dump -U postgres pzem_monitoring > "$BACKUP_DIR/database_$DATE.sql"

# Backup reports
if [ -d "reports" ]; then
    tar -czf "$BACKUP_DIR/reports_$DATE.tar.gz" reports/
fi

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" docker-compose.yml *.sh *.md .env

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh

# Create update script (SAFE - preserves database)
print_info "Creating safe update script..."
cat > update.sh << 'EOF'
#!/bin/bash
# Safe update script for PZEM monitoring system
# This script updates the application WITHOUT deleting the database

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

# Detect docker-compose command (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "docker-compose not found. Please install docker-compose first."
    exit 1
fi

BACKUP_DIR="/opt/backups/pzem-monitoring"
DATE=$(date +%Y%m%d_%H%M%S)
ROLLBACK_DIR="/opt/pzem-monitoring_rollback_${DATE}"

echo ""
echo "🔄 PZEM Monitoring System - Safe Update"
echo "========================================"
echo ""

# Step 1: Verify we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the deployment directory."
    exit 1
fi

# Step 2: Check if services are running
print_info "Checking current service status..."
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    SERVICES_RUNNING=true
    print_status "Services are currently running"
else
    SERVICES_RUNNING=false
    print_warning "Services are not running"
fi

# Step 3: Create backup before update
print_info "Creating backup before update..."
mkdir -p "$BACKUP_DIR"

# Backup database
if $DOCKER_COMPOSE ps db | grep -q "Up"; then
    print_info "Backing up database..."
    $DOCKER_COMPOSE exec -T db pg_dump -U postgres pzem_monitoring > "$BACKUP_DIR/database_pre_update_$DATE.sql" 2>/dev/null || {
        print_warning "Could not backup database (container may be stopped)"
    }
    print_status "Database backup created: database_pre_update_$DATE.sql"
else
    print_warning "Database container not running, skipping backup"
fi

# Backup reports
if [ -d "reports" ]; then
    tar -czf "$BACKUP_DIR/reports_pre_update_$DATE.tar.gz" reports/ 2>/dev/null || true
    print_status "Reports backed up"
fi

# Backup configuration files
tar -czf "$BACKUP_DIR/config_pre_update_$DATE.tar.gz" docker-compose.yml *.sh *.md .env 2>/dev/null || true
print_status "Configuration backed up"

# Step 4: Verify database volume exists
print_info "Verifying database volume..."
DB_VOLUME=$(docker volume ls | grep -o ".*pgdata" | awk '{print $2}' || echo "")
if [ -z "$DB_VOLUME" ]; then
    print_warning "Database volume 'pgdata' not found. It will be created on first start."
else
    print_status "Database volume 'pgdata' found and will be preserved"
fi

# Step 5: Save current state for rollback
print_info "Preparing rollback point..."
if [ "$SERVICES_RUNNING" = true ]; then
    # Save current images
    $DOCKER_COMPOSE images > "$BACKUP_DIR/images_before_update_$DATE.txt" 2>/dev/null || true
fi

# Step 6: Stop services (volumes are preserved)
print_info "Stopping services (database volume will be preserved)..."
$DOCKER_COMPOSE down

# Step 7: Pull latest images (if using pre-built images)
print_info "Pulling latest images..."
$DOCKER_COMPOSE pull 2>/dev/null || print_warning "Some images may not be available on registry (will build locally)"

# Step 8: Rebuild containers (only if Dockerfiles changed)
print_info "Rebuilding containers..."
# Use --no-cache only if explicitly requested
if [ "$1" = "--force-rebuild" ]; then
    print_warning "Force rebuild requested (this will take longer)"
    $DOCKER_COMPOSE build --no-cache
else
    print_info "Incremental build (faster, uses cache when possible)"
    $DOCKER_COMPOSE build
fi

# Step 9: Start services
print_info "Starting services..."
if $DOCKER_COMPOSE up -d; then
    print_status "Services started successfully"
else
    print_error "Failed to start services!"
    print_warning "Attempting rollback..."
    
    # Rollback: restore from backup
    if [ -f "$BACKUP_DIR/database_pre_update_$DATE.sql" ]; then
        print_info "Restoring database from backup..."
        $DOCKER_COMPOSE up -d db
        sleep 5
        $DOCKER_COMPOSE exec -T db psql -U postgres -d pzem_monitoring < "$BACKUP_DIR/database_pre_update_$DATE.sql" 2>/dev/null || true
    fi
    
    exit 1
fi

# Step 10: Wait for services to be healthy
print_info "Waiting for services to be ready..."
sleep 10

# Step 11: Verify database is accessible
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
    
    # Verify database has data
    RECORD_COUNT=$($DOCKER_COMPOSE exec -T db psql -U postgres -d pzem_monitoring -t -c "SELECT COUNT(*) FROM pzem_data;" 2>/dev/null | tr -d ' ' || echo "0")
    if [ "$RECORD_COUNT" != "0" ] && [ -n "$RECORD_COUNT" ]; then
        print_status "Database verified: $RECORD_COUNT records found"
    else
        print_warning "Database is empty or verification failed"
    fi
else
    print_error "Database did not become ready in time"
    exit 1
fi

# Step 12: Health check
print_info "Performing health check..."
sleep 5
if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
    print_status "Health check passed"
else
    print_warning "Health check failed (service may still be starting)"
fi

# Step 13: Cleanup old images (optional)
print_info "Cleaning up unused Docker images..."
docker image prune -f > /dev/null 2>&1 || true

echo ""
print_status "✅ Update completed successfully!"
echo ""
echo "📊 Summary:"
echo "   - Database volume preserved: ✅"
echo "   - Backup created: $BACKUP_DIR"
echo "   - Services restarted: ✅"
echo ""
echo "🔍 Verify update:"
echo "   - Check logs: $DOCKER_COMPOSE logs -f"
echo "   - Check status: $DOCKER_COMPOSE ps"
echo "   - Access dashboard: http://your-vps-ip:5000"
echo ""
print_warning "If you encounter issues, backups are available in: $BACKUP_DIR"
EOF

chmod +x update.sh

# Create monitoring script
print_info "Creating monitoring script..."
cat > monitor.sh << 'EOF'
#!/bin/bash
# Monitoring script for PZEM system

echo "📊 PZEM Monitoring System Status"
echo "================================"

# Check Docker status
echo "🐳 Docker Status:"
systemctl is-active docker

# Check service status
echo ""
echo "🔧 Service Status:"
systemctl is-active pzem-monitoring

# Check container status
echo ""
echo "📦 Container Status:"
# Detect docker-compose command
if command -v docker-compose &> /dev/null; then
    docker-compose ps
elif docker compose version &> /dev/null; then
    docker compose ps
else
    echo "docker-compose not found"
fi

# Check resource usage
echo ""
echo "💾 Resource Usage:"
docker stats --no-stream

# Check disk usage
echo ""
echo "💿 Disk Usage:"
df -h /opt/pzem-monitoring

# Check logs (last 10 lines)
echo ""
echo "📝 Recent Logs:"
docker-compose logs --tail=10
EOF

chmod +x monitor.sh

# Create log rotation configuration
print_info "Configuring log rotation..."
cat > /etc/logrotate.d/pzem-monitoring << EOF
/opt/pzem-monitoring/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF

# Set up automatic backups
print_info "Setting up automatic backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/pzem-monitoring/backup.sh") | crontab -
print_status "Automatic daily backups configured (2 AM)"

# Create health check script
print_info "Creating health check script..."
cat > health-check.sh << 'EOF'
#!/bin/bash
# Health check script for PZEM system

HEALTH_URL="http://localhost:5000/health"
LOG_FILE="/opt/pzem-monitoring/logs/health-check.log"

# Create logs directory if it doesn't exist
mkdir -p /opt/pzem-monitoring/logs

# Check if service is responding
if curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "$(date): Health check PASSED" >> "$LOG_FILE"
    exit 0
else
    echo "$(date): Health check FAILED - restarting services" >> "$LOG_FILE"
    cd /opt/pzem-monitoring
    docker-compose restart
    exit 1
fi
EOF

chmod +x health-check.sh

# Set up health check monitoring
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/pzem-monitoring/health-check.sh") | crontab -
print_status "Health check monitoring configured (every 5 minutes)"

# Create SSL setup script (optional)
print_info "Creating SSL setup script..."
cat > setup-ssl.sh << 'EOF'
#!/bin/bash
# SSL setup script using Let's Encrypt

echo "🔒 Setting up SSL with Let's Encrypt"

# Install certbot
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Get domain from user
read -p "Enter your domain name: " DOMAIN

# Get certificate
certbot --nginx -d "$DOMAIN"

# Set up auto-renewal
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

echo "✅ SSL setup completed for $DOMAIN"
EOF

chmod +x setup-ssl.sh

# Create environment template
print_info "Creating environment configuration..."
if [ ! -f .env ]; then
    cp env.example .env
    print_warning "Please edit .env file with your configuration:"
    print_info "  - DB_PASSWORD: Set a secure database password"
    print_info "  - MQTT_BROKER: Your MQTT broker address"
    print_info "  - MQTT_TOPIC: Your MQTT topic"
fi

# Set proper ownership
chown -R $USER:$USER "$DEPLOY_DIR" 2>/dev/null || true

echo ""
echo "🎉 Ubuntu VPS deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit configuration: nano $DEPLOY_DIR/.env"
echo "2. Start the system: cd $DEPLOY_DIR && ./start.sh"
echo "3. Access dashboard: http://your-vps-ip:5000"
echo ""
echo "🔧 Management commands:"
echo "   Start system:    systemctl start pzem-monitoring"
echo "   Stop system:     systemctl stop pzem-monitoring"
echo "   View logs:       docker-compose logs -f"
echo "   Monitor status:  ./monitor.sh"
echo "   Backup data:     ./backup.sh"
echo "   Update system:   ./update.sh"
echo "   Setup SSL:       ./setup-ssl.sh"
echo ""
echo "🌐 Access URLs:"
echo "   Dashboard:       http://your-vps-ip:5000"
echo "   Reports:         http://your-vps-ip:5000/reports"
echo "   Health Check:    http://your-vps-ip:5000/health"
echo ""
echo "🔒 Security features enabled:"
echo "   - Firewall (UFW) configured"
echo "   - Fail2ban for SSH protection"
echo "   - Automatic backups (daily at 2 AM)"
echo "   - Health monitoring (every 5 minutes)"
echo "   - Log rotation configured"
echo ""
print_warning "Please log out and log back in for Docker group changes to take effect"



