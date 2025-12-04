#!/bin/bash

# Database Backup Script for Trading Agent
# Supports both development and production environments

set -e

# Configuration
BACKUP_DIR="./backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=${RETENTION_DAYS:-30}

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Create backup directory
setup_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# Backup database
backup_database() {
    local env_file=".env"
    local compose_file="docker-compose.yml"

    # Check if production environment
    if [ "$ENVIRONMENT" = "production" ] || [ -f ".env.prod" ]; then
        env_file=".env.prod"
        compose_file="docker-compose.prod.yml"
        log_info "Using production configuration"
    fi

    log_info "Starting database backup..."

    # Load environment variables
    if [ -f "$env_file" ]; then
        export $(grep -v '^#' "$env_file" | xargs)
    fi

    # Create backup using Docker
    docker compose -f "$compose_file" exec -T db pg_dump \
        -U trading_user \
        -d trading_db \
        --no-password \
        --format=custom \
        --compress=9 \
        --verbose > "${BACKUP_DIR}/trading_db_${TIMESTAMP}.backup"

    local backup_size=$(du -h "${BACKUP_DIR}/trading_db_${TIMESTAMP}.backup" | cut -f1)
    log_info "Database backup completed: trading_db_${TIMESTAMP}.backup (${backup_size})"
}

# Backup configuration files
backup_configs() {
    log_info "Backing up configuration files..."

    local config_backup="${BACKUP_DIR}/config_${TIMESTAMP}.tar.gz"

    # Create tar archive of important configs
    tar -czf "$config_backup" \
        --exclude='*.log' \
        --exclude='*.tmp' \
        --exclude='node_modules' \
        --exclude='.git' \
        .env* \
        docker-compose*.yml \
        nginx/ \
        monitoring/ \
        2>/dev/null || true

    local config_size=$(du -h "$config_backup" | cut -f1)
    log_info "Configuration backup completed: config_${TIMESTAMP}.tar.gz (${config_size})"
}

# Backup application data
backup_app_data() {
    log_info "Backing up application data..."

    if [ -d "data" ]; then
        local data_backup="${BACKUP_DIR}/data_${TIMESTAMP}.tar.gz"
        tar -czf "$data_backup" data/
        local data_size=$(du -h "$data_backup" | cut -f1)
        log_info "Application data backup completed: data_${TIMESTAMP}.tar.gz (${data_size})"
    else
        log_warning "No application data directory found"
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"

    if [ -f "$backup_file" ]; then
        log_info "Verifying backup: $backup_file"

        # For PostgreSQL custom format, we can check if it's readable
        if [[ "$backup_file" == *.backup ]]; then
            if head -c 1024 "$backup_file" | grep -q "PGDMP"; then
                log_info "Backup verification passed: Valid PostgreSQL dump"
            else
                log_error "Backup verification failed: Invalid PostgreSQL dump"
                return 1
            fi
        fi

        # Check file size
        local size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)
        if [ "$size" -gt 1024 ]; then  # At least 1KB
            log_info "Backup size check passed: $size bytes"
        else
            log_error "Backup size check failed: File too small"
            return 1
        fi
    else
        log_error "Backup file not found: $backup_file"
        return 1
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: ${RETENTION_DAYS} days)..."

    local deleted_count=0

    # Find and delete old backups
    find "$BACKUP_DIR" -name "*.backup" -o -name "*.tar.gz" -mtime +$RETENTION_DAYS -print -delete | while read -r file; do
        log_info "Deleted old backup: $file"
        ((deleted_count++))
    done

    if [ $deleted_count -eq 0 ]; then
        log_info "No old backups to clean up"
    else
        log_info "Cleaned up $deleted_count old backup files"
    fi
}

# Generate backup report
generate_report() {
    local report_file="${BACKUP_DIR}/backup_report_${TIMESTAMP}.txt"

    log_info "Generating backup report..."

    cat > "$report_file" << EOF
Trading Agent Backup Report
===========================
Timestamp: $(date)
Environment: ${ENVIRONMENT:-development}
Retention Days: $RETENTION_DAYS

Backup Files:
$(ls -la "$BACKUP_DIR" | grep -E "\.(backup|tar\.gz|txt)$" | tail -n 10)

Disk Usage:
$(du -sh "$BACKUP_DIR")

Backup Summary:
- Database backup completed
- Configuration backup completed
- Application data backup completed
- Old backups cleaned up
EOF

    log_info "Backup report generated: $report_file"
}

# Send notification (if configured)
send_notification() {
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Trading Agent backup completed successfully - $(date)\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
}

# Main backup function
main() {
    log_info "🚀 Starting Trading Agent Backup"

    setup_backup_dir

    # Perform backups
    backup_database
    backup_configs
    backup_app_data

    # Verify backups
    for backup_file in "${BACKUP_DIR}"/*"${TIMESTAMP}"*; do
        if [ -f "$backup_file" ]; then
            verify_backup "$backup_file"
        fi
    done

    # Cleanup and reporting
    cleanup_old_backups
    generate_report
    send_notification

    log_info "✅ Backup completed successfully"
    log_info "📁 Backup location: $BACKUP_DIR"
}

# Error handling
trap 'log_error "Backup failed with exit code $?"' ERR

# Run main function
main "$@"
