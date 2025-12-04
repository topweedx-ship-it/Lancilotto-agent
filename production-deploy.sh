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

    if [ ! -f ".env.prod" ]; then
        log_error ".env.prod file not found. Copy env.prod.example to .env.prod and configure it."
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

    # Tag the image
    docker tag ${IMAGE_NAME}:latest ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG}
    docker tag ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG} ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest

    log_success "Image built and tagged: ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG}"
}

# Push to registry
push_image() {
    log_info "Pushing image to registry..."

    docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:${TAG}
    docker push ${DOCKER_REGISTRY}/${IMAGE_NAME}:latest

    log_success "Image pushed to registry"
}

# Deploy to production
deploy() {
    log_info "Deploying to production..."

    # Create backup before deployment
    create_backup

    # Pull latest images
    docker compose -f docker-compose.prod.yml pull

    # Deploy with zero downtime
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
    generate_tag

    # Trap errors for rollback
    trap rollback ERR

    build_image
    push_image
    deploy

    log_success "🎉 Production deployment completed successfully!"
    log_info "🌐 Application available at: https://your-domain.com"
    log_info "📊 Grafana dashboard at: https://your-domain.com:3000"
    log_info "📈 Prometheus metrics at: https://your-domain.com:9090"
}

# Run main function
main "$@"
