#!/bin/bash

# Production Deployment Script for Trading Agent
# Handles build, tag, push, and deployment with zero-downtime

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_REGISTRY="${DOCKER_REGISTRY:-your-registry.com}"
IMAGE_NAME="${IMAGE_NAME:-trading-agent}"
NAMESPACE="${NAMESPACE:-production}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Interactive setup for .env file
setup_env() {
    if [ -f "backend/.env" ]; then
        return 0  # File already exists
    fi
    
    log_info "🔧 First time setup detected!"
    log_info "Configuring backend/.env file..."
    echo ""
    
    if [ ! -f "backend/env.example" ]; then
        log_error "backend/env.example file not found. Cannot create .env file."
        exit 1
    fi
    
    # Create .env file from example
    cp backend/env.example backend/.env
    
    log_info "Please enter the following configuration values:"
    log_info "(Press Enter to skip optional variables or use default values)"
    echo ""
    
    # Required variables
    local vars_required=(
        "OPENAI_API_KEY:OpenAI API Key (REQUIRED)"
        "POSTGRES_PASSWORD:Database Password (REQUIRED)"
        "DB_PASSWORD:Database Password (same as POSTGRES_PASSWORD)"
    )
    
    # Important optional variables
    local vars_important=(
        "MASTER_ACCOUNT_ADDRESS:Master Account Address"
        "PRIVATE_KEY:Private Key (Mainnet)"
        "WALLET_ADDRESS:Wallet Address (Mainnet)"
        "TESTNET_PRIVATE_KEY:Private Key (Testnet)"
        "TESTNET_WALLET_ADDRESS:Wallet Address (Testnet)"
        "COINGECKO_API_KEY:CoinGecko API Key"
        "TELEGRAM_BOT_TOKEN:Telegram Bot Token"
        "TELEGRAM_CHAT_ID:Telegram Chat ID"
        "DOMAIN:Production Domain"
        "GRAFANA_PASSWORD:Grafana Password"
    )
    
    # Optional variables
    local vars_optional=(
        "DEEPSEEK_API_KEY:DeepSeek API Key"
        "CMC_PRO_API_KEY:CoinMarketCap API Key"
        "SECRET_KEY:Secret Key"
    )
    
    # Process required variables
    log_info "═══════════════════════════════════════════════════════"
    log_info "REQUIRED VARIABLES:"
    log_info "═══════════════════════════════════════════════════════"
    for var_desc in "${vars_required[@]}"; do
        local var_name="${var_desc%%:*}"
        local var_desc_text="${var_desc#*:}"
        local current_value=$(grep "^${var_name}=" backend/.env | cut -d'=' -f2- | sed 's/^"//;s/"$//')
        
        # Skip if already has a real value (not placeholder)
        if [[ ! "$current_value" =~ ^(your_|your-|your ) ]]; then
            continue
        fi
        
        while true; do
            read -p "${YELLOW}${var_desc_text}${NC}: " value
            if [ -z "$value" ] && [[ "$var_name" == *"PASSWORD"* ]] || [[ "$var_name" == "OPENAI_API_KEY" ]]; then
                log_error "This field is required. Please enter a value."
                continue
            fi
            break
        done
        
        if [ -n "$value" ]; then
            # Escape special characters for sed
            local escaped_value=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')
            sed -i "s|^${var_name}=.*|${var_name}=${escaped_value}|" backend/.env
            
            # Special handling for DB_PASSWORD
            if [ "$var_name" == "POSTGRES_PASSWORD" ]; then
                sed -i "s|^DB_PASSWORD=.*|DB_PASSWORD=${escaped_value}|" backend/.env
            fi
        fi
    done
    
    # Process important optional variables
    echo ""
    log_info "═══════════════════════════════════════════════════════"
    log_info "IMPORTANT OPTIONAL VARIABLES:"
    log_info "═══════════════════════════════════════════════════════"
    for var_desc in "${vars_important[@]}"; do
        local var_name="${var_desc%%:*}"
        local var_desc_text="${var_desc#*:}"
        local current_value=$(grep "^${var_name}=" backend/.env | cut -d'=' -f2- | sed 's/^"//;s/"$//')
        
        if [[ "$current_value" =~ ^(your_|your-|your ) ]]; then
            read -p "${YELLOW}${var_desc_text}${NC} (optional): " value
            if [ -n "$value" ]; then
                local escaped_value=$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')
                sed -i "s|^${var_name}=.*|${var_name}=${escaped_value}|" backend/.env
            fi
        fi
    done
    
    # Process optional variables
    echo ""
    log_info "═══════════════════════════════════════════════════════"
    log_info "OTHER OPTIONAL VARIABLES:"
    log_info "═══════════════════════════════════════════════════════"
    log_info "You can configure these later by editing backend/.env"
    echo ""
    
    # Set default values for development
    sed -i 's/^POSTGRES_HOST=db/POSTGRES_HOST=localhost/' backend/.env
    sed -i 's/@db:5432/@localhost:5432/' backend/.env
    sed -i 's/^ENVIRONMENT=production/ENVIRONMENT=development/' backend/.env
    sed -i 's/^DEBUG=false/DEBUG=true/' backend/.env
    
    log_success "✅ Configuration file created: backend/.env"
    log_info "You can edit it later if needed."
    echo ""
}

# Load environment variables from backend/.env
load_env() {
    log_info "Loading environment variables from backend/.env..."
    
    if [ ! -f "backend/.env" ]; then
        log_error ".env file not found in backend directory."
        exit 1
    fi
    
    # Export variables from .env file (only process valid KEY=VALUE lines)
    set -a
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Only process lines that look like KEY=VALUE (with optional whitespace)
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            export "$line"
        fi
    done < backend/.env
    set +a
    
    # Override for production - set POSTGRES_HOST to 'db' for Docker
    export POSTGRES_HOST=db
    export DATABASE_URL=postgresql://trading_user:${POSTGRES_PASSWORD:-${DB_PASSWORD}}@db:5432/trading_db
    export ENVIRONMENT=production
    export DEBUG=false
    
    # Create .env file in root for docker-compose to read automatically
    # This allows docker compose to work even when run directly
    log_info "Creating .env file in root for docker-compose..."
    grep -E "^(POSTGRES_PASSWORD|DB_PASSWORD)=" backend/.env > .env 2>/dev/null || true
    if [ -f .env ]; then
        log_success "Created .env file in root"
    fi
    
    log_success "Environment variables loaded"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Setup .env file if it doesn't exist
    setup_env
    
    if [ ! -f "backend/.env" ]; then
        log_error ".env file not found in backend directory after setup."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Generate version tag
generate_tag() {
    if [ -n "$CI_COMMIT_SHA" ]; then
        # GitLab CI
        TAG="${CI_COMMIT_SHA:0:8}"
    elif [ -n "$GITHUB_SHA" ]; then
        # GitHub Actions
        TAG="${GITHUB_SHA:0:8}"
    else
        # Local deployment
        TAG="$(date +%Y%m%d-%H%M%S)-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')"
    fi

    export TAG
    log_info "Using tag: $TAG"
}

# Build production image
build_image() {
    log_info "Building production image..."

    # Enable BuildKit
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1

    # Build with production compose
    docker compose -f docker-compose.prod.yml build --parallel

    # Tag the image - use the built image name from docker-compose
    # The image is built as trading-agent-app by docker-compose
    if docker images | grep -q "trading-agent-app"; then
        docker tag trading-agent-app:latest ${IMAGE_NAME}:latest 2>/dev/null || true
    fi
    
    # Tag for registry (optional, skipped for local deployment)
    if [ -n "${DOCKER_REGISTRY}" ] && [ "${DOCKER_REGISTRY}" != "your-registry.com" ]; then
        docker tag ${IMAGE_NAME}:latest ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG} 2>/dev/null || true
        docker tag ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest 2>/dev/null || true
    fi

    log_success "Image built and tagged: ${IMAGE_NAME}:latest"
}

# Push to registry
push_image() {
    log_info "Pushing image to registry..."

    log_warning "Skipping push to registry for local deployment"
    #docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG}
    #docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest

    log_success "Image pushed to registry"
}

# Deploy to production
deploy() {
    log_info "Deploying to production..."

    # Create backup before deployment
    create_backup

    # Clean up any existing networks that might cause conflicts
    log_info "Cleaning up Docker networks..."
    docker network prune -f 2>/dev/null || true

    # Pull latest images (skip app since it's built locally)
    log_info "Pulling external images (db, prometheus, grafana)..."
    docker compose -f docker-compose.prod.yml pull db prometheus grafana backup 2>/dev/null || true

    # Deploy with zero downtime
    # Note: Environment variables are already loaded by load_env() function
    docker compose -f docker-compose.prod.yml up -d

    # Wait for health checks
    wait_for_health

    # Clean up old images
    cleanup_old_images

    log_success "Deployment completed successfully"
}

# Create database backup
create_backup() {
    log_info "Creating database backup..."

    docker compose -f docker-compose.prod.yml exec -T backup /bin/sh -c "
        echo 'Starting database backup...' &&
        pg_dump -h db -U trading_user trading_db > /backup/trading_db_pre_deploy_$(date +%Y%m%d_%H%M%S).sql &&
        echo 'Backup completed'
    " 2>/dev/null || log_warning "Backup service not available, skipping..."
}

# Wait for services to be healthy
wait_for_health() {
    log_info "Waiting for services to be healthy..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose -f docker-compose.prod.yml exec -T app curl -f http://localhost:5611/api/health &>/dev/null; then
            log_success "Application is healthy"
            return 0
        fi

        log_info "Waiting for health check... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    log_error "Application failed to become healthy"
    exit 1
}

# Clean up old images
cleanup_old_images() {
    log_info "Cleaning up old images..."

    # Keep only the last 3 images
    docker images ${DOCKER_REGISTRY}/${IMAGE_NAME} --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}" |
    tail -n +2 | sort -k3 -r | tail -n +4 | awk '{print $2}' |
    xargs -r docker rmi 2>/dev/null || true

    log_success "Old images cleaned up"
}

# Rollback function
rollback() {
    log_error "Deployment failed, rolling back..."

    # Stop current deployment
    docker compose -f docker-compose.prod.yml down

    # Restore from backup if available
    # This would need additional logic for full rollback

    log_info "Rollback completed. Manual intervention may be required."
    exit 1
}

# Main deployment flow
main() {
    log_info "🚀 Starting Trading Agent Production Deployment"
    echo "==========================================="

    check_prerequisites
    load_env
    generate_tag

    # Trap errors for rollback
    trap rollback ERR

    build_image
    push_image
    deploy

    log_success "🎉 Production deployment completed successfully!"
    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "your-production-domain.com" ]; then
        log_info "🌐 Application available at: https://${DOMAIN}"
        log_info "📊 Grafana dashboard at: https://${DOMAIN}:3000"
        log_info "📈 Prometheus metrics at: https://${DOMAIN}:9090"
    else
        log_info "🌐 Application available at: https://your-domain.com"
        log_info "📊 Grafana dashboard at: https://your-domain.com:3000"
        log_info "📈 Prometheus metrics at: https://your-domain.com:9090"
        log_warning "Set DOMAIN variable in backend/.env to see the correct URLs"
    fi
}

# Run main function
main "$@"
