# Trading Agent Development Makefile
# Ottimizzato per velocità e produttività

.PHONY: help build up down logs clean test backtrack-analysis

# Default target
help:
	@echo "🚀 Trading Agent Development Commands"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build         - Build optimized Docker image with caching"
	@echo "  make up            - Start all services"
	@echo "  make down          - Stop all services"
	@echo "  make restart       - Restart all services"
	@echo ""
	@echo "Development:"
	@echo "  make logs          - Show application logs"
	@echo "  make shell         - Open shell in app container"
	@echo "  make test          - Run tests in container"
	@echo "  make clean         - Clean up containers and images"
	@echo ""
	@echo "Analysis:"
	@echo "  make backtrack-analysis - Run backtrack analysis (30 days)"
	@echo "  make backtrack-7d       - Run backtrack analysis (7 days)"
	@echo ""
	@echo "Quick commands:"
	@echo "  make dev           - Build + up + logs"
	@echo "  make rebuild       - Clean build + up"

# Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Build optimized image
build:
	@echo "📦 Building optimized Docker image..."
	@time docker compose build --parallel
	@echo "✅ Build completed!"
	@docker images trading-agent:latest --format "📊 Image size: {{.Size}}"

# Start services
up:
	@echo "🏃 Starting services..."
	docker compose up -d
	@echo "✅ Services started!"
	@echo "🌐 App: http://localhost:5611"
	@echo "🐘 DB: localhost:5432"

# Stop services
down:
	@echo "🛑 Stopping services..."
	docker compose down

# Restart services
restart: down up

# Show logs
logs:
	docker compose logs -f app

# Open shell in container
shell:
	docker compose exec app bash

# Run tests
test:
	@echo "🧪 Running tests..."
	docker compose exec app uv run python -m pytest backend/test_*.py -v

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker compose down -v
	docker system prune -f
	docker image rm trading-agent:latest 2>/dev/null || true

# Backtrack analysis (default 30 days)
backtrack-analysis:
	@echo "📊 Running backtrack analysis (30 days)..."
	docker compose exec app python backtrack_analysis.py --days 30

# Backtrack analysis (7 days)
backtrack-7d:
	@echo "📊 Running backtrack analysis (7 days)..."
	docker compose exec app python backtrack_analysis.py --days 7

# Development workflow: build + up + logs
dev: build up logs

# Rebuild from scratch
rebuild: clean build up
