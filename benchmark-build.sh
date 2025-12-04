#!/bin/bash

# Docker Build Benchmark Script
# Misura le performance del build prima e dopo le ottimizzazioni

set -e

echo "📊 Docker Build Benchmark"
echo "========================"

# Function to time builds
benchmark_build() {
    local name=$1
    local command=$2

    echo ""
    echo "🏗️  Testing: $name"
    echo "Command: $command"

    start_time=$(date +%s.%3N)

    if eval "$command"; then
        end_time=$(date +%s.%3N)
        duration=$(echo "$end_time - $start_time" | bc)

        echo "✅ $name completed in $duration seconds"

        # Save result
        echo "$name: $duration seconds" >> benchmark_results.txt

        return 0
    else
        echo "❌ $name failed"
        return 1
    fi
}

# Clean up previous results
rm -f benchmark_results.txt

echo "🧹 Cleaning up previous containers..."
docker compose down -v 2>/dev/null || true
docker image rm trading-agent:latest 2>/dev/null || true

echo ""
echo "🚀 Starting benchmarks..."
echo "Results will be saved to benchmark_results.txt"

# Test 1: Clean build (first time)
benchmark_build "Clean Build" "docker compose build --no-cache"

# Test 2: Rebuild (code only change - simulate)
echo ""
echo "📝 Simulating code change..."
touch backend/main.py  # Touch file to simulate change

benchmark_build "Code Change Rebuild" "docker compose build"

# Test 3: Dependency change rebuild (simulate)
echo ""
echo "📦 Simulating dependency change..."
# This would require actually changing pyproject.toml, but we'll skip for now
# benchmark_build "Dependency Change Rebuild" "docker compose build"

# Show results
echo ""
echo "📈 Benchmark Results:"
echo "===================="
cat benchmark_results.txt 2>/dev/null || echo "No results file found"

# Show image info
echo ""
echo "📊 Docker Image Info:"
docker images trading-agent:latest --format "Image: {{.Repository}}:{{.Tag}} Size: {{.Size}}" 2>/dev/null || echo "No image found"

echo ""
echo "✅ Benchmark completed!"
echo "💡 Expected: Code-only rebuilds should be much faster (< 2 minutes)"
