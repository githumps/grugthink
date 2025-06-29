#!/bin/bash

# Build script for different Docker image variants
set -e

IMAGE_NAME="grugthink"
TAG_PREFIX="latest"

echo "Building Docker images..."

# Build lightweight version (no ML dependencies)
echo "Building lightweight version..."
docker build -f Dockerfile.lite -t ${IMAGE_NAME}:${TAG_PREFIX}-lite .

# Build optimized version (with ML dependencies but optimized)
echo "Building optimized version..."
docker build -f Dockerfile.optimized -t ${IMAGE_NAME}:${TAG_PREFIX}-optimized .

# Build original version
echo "Building original version..."
docker build -f Dockerfile -t ${IMAGE_NAME}:${TAG_PREFIX} .

echo ""
echo "=== Image Size Comparison ==="
echo "Lightweight (no ML):"
docker images ${IMAGE_NAME}:${TAG_PREFIX}-lite --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
echo ""
echo "Optimized (with ML):"
docker images ${IMAGE_NAME}:${TAG_PREFIX}-optimized --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
echo ""
echo "Original:"
docker images ${IMAGE_NAME}:${TAG_PREFIX} --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

echo ""
echo "=== Recommendations ==="
echo "• Use 'lite' version for production if you don't need semantic search"
echo "• Use 'optimized' version if you need semantic search capabilities"
echo "• Set LOAD_EMBEDDER=False environment variable to disable ML features"