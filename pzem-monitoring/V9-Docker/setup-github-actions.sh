#!/bin/bash
# Setup script for GitHub Actions CI/CD
# This script helps setup SSH keys and verify configuration

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

VPS_USER="foom"
VPS_HOST="103.31.39.189"
SSH_KEY_NAME="github_actions_vps"
SSH_KEY_PATH="$HOME/.ssh/${SSH_KEY_NAME}"

echo ""
echo "🔧 GitHub Actions CI/CD Setup"
echo "============================="
echo ""

# Step 1: Check if SSH key exists
if [ -f "${SSH_KEY_PATH}" ]; then
    print_warning "SSH key already exists: ${SSH_KEY_PATH}"
    read -p "Generate new key? (yes/no): " generate_new
    if [ "$generate_new" != "yes" ]; then
        print_info "Using existing SSH key"
    else
        print_info "Backing up existing key..."
        mv "${SSH_KEY_PATH}" "${SSH_KEY_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
        mv "${SSH_KEY_PATH}.pub" "${SSH_KEY_PATH}.pub.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    fi
fi

# Step 2: Generate SSH key if needed
if [ ! -f "${SSH_KEY_PATH}" ] || [ "$generate_new" = "yes" ]; then
    print_info "Generating SSH key..."
    ssh-keygen -t ed25519 -C "github-actions-pzem-monitoring" -f "${SSH_KEY_PATH}" -N ""
    print_status "SSH key generated"
fi

# Step 3: Display public key
echo ""
print_info "Public SSH Key (copy this to GitHub Secrets as VPS_SSH_KEY):"
echo "─────────────────────────────────────────────────────────────"
cat "${SSH_KEY_PATH}"
echo "─────────────────────────────────────────────────────────────"
echo ""

# Step 4: Copy public key to VPS
read -p "Copy public key to VPS automatically? (yes/no): " copy_to_vps
if [ "$copy_to_vps" = "yes" ]; then
    print_info "Copying public key to VPS..."
    
    # Try ssh-copy-id first
    if command -v ssh-copy-id &> /dev/null; then
        ssh-copy-id -i "${SSH_KEY_PATH}.pub" ${VPS_USER}@${VPS_HOST} 2>/dev/null || {
            print_warning "ssh-copy-id failed, trying manual method..."
            
            # Manual method
            cat "${SSH_KEY_PATH}.pub" | ssh ${VPS_USER}@${VPS_HOST} "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
        }
    else
        # Manual method
        print_info "Using manual method..."
        cat "${SSH_KEY_PATH}.pub" | ssh ${VPS_USER}@${VPS_HOST} "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    fi
    
    print_status "Public key copied to VPS"
else
    print_warning "Skipping automatic copy. Please manually add public key to VPS:"
    print_info "  ssh-copy-id -i ${SSH_KEY_PATH}.pub ${VPS_USER}@${VPS_HOST}"
    print_info "  Or manually: cat ${SSH_KEY_PATH}.pub >> ~/.ssh/authorized_keys (on VPS)"
fi

# Step 5: Test SSH connection
echo ""
print_info "Testing SSH connection..."
if ssh -i "${SSH_KEY_PATH}" -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${VPS_USER}@${VPS_HOST} "echo 'SSH connection successful'" 2>/dev/null; then
    print_status "SSH connection test passed"
else
    print_error "SSH connection test failed"
    print_warning "Please verify:"
    print_info "  1. VPS is accessible: ping ${VPS_HOST}"
    print_info "  2. SSH service is running on VPS"
    print_info "  3. Public key is in ~/.ssh/authorized_keys on VPS"
    exit 1
fi

# Step 6: Verify VPS requirements
echo ""
print_info "Checking VPS requirements..."
ssh -i "${SSH_KEY_PATH}" ${VPS_USER}@${VPS_HOST} << 'EOF'
    echo "Checking Docker..."
    if command -v docker &> /dev/null; then
        echo "✅ Docker installed: $(docker --version)"
    else
        echo "❌ Docker not found"
    fi
    
    echo "Checking Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        echo "✅ docker-compose installed: $(docker-compose --version)"
    elif docker compose version &> /dev/null; then
        echo "✅ docker compose installed: $(docker compose version)"
    else
        echo "❌ docker-compose not found"
    fi
    
    echo "Checking Nginx..."
    if command -v nginx &> /dev/null; then
        echo "✅ Nginx installed: $(nginx -v 2>&1)"
    else
        echo "⚠️  Nginx not found (optional for deployment)"
    fi
EOF

# Step 7: Display GitHub Secrets setup instructions
echo ""
print_info "📋 Next Steps - Setup GitHub Secrets:"
echo ""
echo "1. Go to GitHub Repository → Settings → Secrets and variables → Actions"
echo "2. Click 'New repository secret'"
echo "3. Add the following secrets:"
echo ""
echo "   Secret Name: VPS_USER"
echo "   Value: ${VPS_USER}"
echo ""
echo "   Secret Name: VPS_HOST"
echo "   Value: ${VPS_HOST}"
echo ""
echo "   Secret Name: VPS_SSH_KEY"
echo "   Value: (copy the private key shown above)"
echo ""
print_warning "⚠️  IMPORTANT: Copy the private key (entire content including BEGIN/END lines)"
echo ""

# Step 8: Display private key again for easy copy
read -p "Display private key again? (yes/no): " show_key
if [ "$show_key" = "yes" ]; then
    echo ""
    print_info "Private SSH Key (for GitHub Secret VPS_SSH_KEY):"
    echo "─────────────────────────────────────────────────────────────"
    cat "${SSH_KEY_PATH}"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
fi

print_status "Setup completed!"
echo ""
print_info "📚 Documentation: .github/SETUP_CI_CD.md"
echo ""

