# Docker Image Size Optimization Guide

The GrugThink Docker image can be optimized from **3.59GB** down to **~200-300MB** depending on your needs.

## Image Size Comparison

| Version | Size | ML Features | Use Case |
|---------|------|-------------|----------|
| **Lite** | ~200-300MB | ❌ Disabled | Production without semantic search |
| **Optimized** | ~1-2GB | ✅ Enabled | Production with semantic search |
| **Original** | ~3.59GB | ✅ Enabled | Development/full features |

## Quick Start

### 1. Build Size-Optimized Images
```bash
# Build all variants and compare sizes
./build-docker.sh

# Or build individually
docker build -f Dockerfile.lite -t grugthink:lite .           # Smallest
docker build -f Dockerfile.optimized -t grugthink:optimized . # Balanced  
docker build -f Dockerfile -t grugthink:original .            # Original
```

### 2. Run Different Variants
```bash
# Lightweight version (recommended for most deployments)
docker-compose -f docker-compose.dev.yml --profile lite up

# Optimized version (if you need semantic search)
docker-compose -f docker-compose.dev.yml --profile optimized up

# Original version (development)
docker-compose -f docker-compose.dev.yml --profile original up
```

## Optimization Strategies

### 1. Remove Heavy ML Dependencies (Dockerfile.lite)
- **Removes**: `faiss-cpu`, `sentence-transformers`, PyTorch
- **Savings**: ~3GB
- **Trade-off**: No semantic search capabilities
- **Best for**: Most production deployments

### 2. Aggressive Cleanup (Dockerfile.optimized)
- **Removes**: Build artifacts, documentation, cached files
- **Savings**: ~1-1.5GB  
- **Trade-off**: None (same functionality)
- **Best for**: Production with semantic search

### 3. Minimal File Copying
- **Removes**: Unnecessary project files
- **Savings**: ~50-100MB
- **Trade-off**: None
- **Best for**: All deployments

## Environment Variables

Control ML features at runtime:

```bash
# Disable ML features (works with any image)
LOAD_EMBEDDER=False

# Enable ML features (requires optimized/original image)
LOAD_EMBEDDER=True
```

## Implementation Details

### Heavy Dependencies Removed in Lite Version
- `faiss-cpu==1.7.4` (~100-200MB)
- `sentence-transformers>=2.2.2` (~1-2GB including PyTorch)
- Associated ML model files

### Optimizations Applied
1. **Multi-stage builds** - Separate build and runtime environments
2. **Package cleanup** - Remove build tools, caches, docs
3. **File stripping** - Remove debug symbols from binaries
4. **Minimal base images** - Use slim Python images
5. **Selective copying** - Only copy necessary application files

### Graceful Degradation
The application automatically handles missing ML dependencies:
- Database-only fact storage and retrieval
- Personality engine works without semantic search
- All Discord commands function normally
- Reduced memory usage (~100MB vs ~1GB+)

## Recommendations

### For Production
- Use **Dockerfile.lite** for most deployments
- Set `LOAD_EMBEDDER=False` in environment
- Results in ~200-300MB images

### For Development  
- Use **Dockerfile.optimized** if you need semantic search
- Use **Dockerfile** (original) for full development environment

### For CI/CD
- Use lite version for faster builds and deployments
- Existing `requirements-ci.txt` already optimized for this

## Monitoring Image Sizes

```bash
# Check current image sizes
docker images grugthink* --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

# Analyze layer sizes
docker history grugthink:lite
```

This optimization maintains full functionality while dramatically reducing deployment size and resource requirements.