#!/bin/bash

# Trading Agent Docker Build Script
# Ottimizzato per velocità e caching

set -e

echo "🚀 Building Trading Agent Docker Image..."

# Enable Docker BuildKit for faster builds and better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Function to show build time
start_time=$(date +%s)

# Build with optimizations
echo "📦 Building optimized Docker image..."
docker compose build --parallel

end_time=$(date +%s)
build_time=$((end_time - start_time))

echo "✅ Build completed in $build_time seconds"

# Show image size
image_size=$(docker images trading-agent:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | tail -n 1)
echo "📊 Image size: $image_size"

# Optional: Run tests in container
if [ "$1" = "--test" ]; then
    echo "🧪 Running tests in container..."
    docker run --rm --env-file backend/.env trading-agent:latest uv run python -m pytest backend/test_*.py -v
fi

# Optional: Start services
if [ "$1" = "--up" ]; then
    echo "🏃 Starting services..."
    docker compose up -d
fi

echo "🎉 Done! Use 'docker compose up -d' to start the services."
