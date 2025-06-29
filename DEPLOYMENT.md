# GrugThink Deployment Guide

**Deploy your personality-evolving Discord bot to production environments**

This guide covers deploying GrugThink using Docker with multiple optimization options, from lightweight 401MB images to full-featured 1.3GB deployments.

## 🚀 Quick Start: Docker Compose (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- Discord bot token
- Gemini API key or Ollama instance

### Deployment Steps

1. **Clone Repository**:
   ```bash
   git clone https://github.com/githumps/grugthink.git
   cd grugthink
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your tokens and configuration
   ```

3. **Create Data Directory**:
   ```bash
   mkdir grug-data
   ```

4. **Choose Deployment Type**:
   
   **Lightweight (Recommended - 401MB)**:
   ```bash
   docker-compose -f docker-compose.dev.yml --profile lite up -d
   ```
   
   **Production with Semantic Search (1.06GB)**:
   ```bash
   docker-compose -f docker-compose.dev.yml --profile optimized up -d
   ```
   
   **Standard Deployment**:
   ```bash
   docker-compose up -d
   ```

5. **Verify Deployment**:
   ```bash
   docker-compose logs -f
   ```

### Stop and Update
```bash
# Stop bot
docker-compose down

# Update and restart
git pull
docker-compose pull
docker-compose up -d
```

## 🐳 Docker Run (Manual)

If you prefer direct Docker commands:

**Lightweight Version**:
```bash
docker run -d \
  --name grugthink-lite \
  --env-file .env \
  -e LOAD_EMBEDDER=False \
  -v "$(pwd)/grug-data:/data" \
  ghcr.io/githumps/grugthink:latest-lite
```

**Full Version**:
```bash
docker run -d \
  --name grugthink \
  --env-file .env \
  -v "$(pwd)/grug-data:/data" \
  ghcr.io/githumps/grugthink:latest
```

## 🏗️ Build from Source

### Development Build
```bash
# Lightweight build (fast)
docker build -f Dockerfile.lite -t grugthink:lite .

# Optimized build (balanced)
docker build -f Dockerfile.optimized -t grugthink:optimized .

# Full build (complete features)
docker build -f Dockerfile -t grugthink:full .
```

### Size Comparison
```bash
# Build all variants and compare
./build-docker.sh
```

Expected results:
- **Lite**: ~401MB (no ML dependencies)
- **Optimized**: ~1.06GB (ML with cleanup)
- **Original**: ~1.31GB (full development)

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | `your_discord_token_here` |
| `GEMINI_API_KEY` | Gemini API key (OR configure Ollama) | `your_gemini_key_here` |
| `TRUSTED_USER_IDS` | Discord user IDs for `/learn` command | `123456789,987654321` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOAD_EMBEDDER` | `True` | Enable semantic search (set `False` for lite) |
| `GRUGBOT_VARIANT` | `prod` | Bot variant (`prod` or `dev`) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`) |
| `GRUGBOT_DATA_DIR` | `.` | Data directory (use `/data` in Docker) |

### Search and AI Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Search API key (optional) | `your_google_api_key` |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | `your_cse_id` |
| `OLLAMA_URLS` | Ollama server URLs (comma-separated) | `http://localhost:11434` |
| `OLLAMA_MODELS` | Ollama models to use | `llama3.2:3b,mixtral` |

### Example .env File
```bash
# Required
DISCORD_TOKEN=your_discord_token_here
GEMINI_API_KEY=your_gemini_api_key_here
TRUSTED_USER_IDS=123456789,987654321

# Docker configuration
GRUGBOT_DATA_DIR=/data

# Optional features
LOAD_EMBEDDER=True
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id

# Logging
LOG_LEVEL=INFO
GRUGBOT_VARIANT=prod
```

## 🔄 Release Management

### Automated Releases

GrugThink uses GitHub Actions for automated builds and releases:

1. **Development Builds**: Automatic builds on every push to `main`
2. **Release Candidates**: Tagged pre-releases (`v1.1.0-rc1`)
3. **Stable Releases**: Tagged stable releases (`v1.1.0`)

### Creating a Release

**Pre-release (Beta Testing)**:
```bash
git tag -a v2.1.0-rc1 -m "Release candidate for v2.1.0"
git push origin v2.1.0-rc1
```

**Stable Release**:
```bash
# Ensure main branch is ready
git checkout main
git pull origin main

# Run tests
PYTHONPATH=. pytest

# Create release tag
git tag -a v2.1.0 -m "Release v2.1.0: Enhanced personality system"
git push origin v2.1.0
```

GitHub Actions will automatically:
- Build Docker images for all variants
- Push to GitHub Container Registry
- Create GitHub release with changelogs
- Update `latest` tags

### Image Tags

| Tag Pattern | Description | Example |
|-------------|-------------|---------|
| `latest` | Latest stable release | `ghcr.io/githumps/grugthink:latest` |
| `latest-lite` | Latest lightweight build | `ghcr.io/githumps/grugthink:latest-lite` |
| `latest-optimized` | Latest optimized build | `ghcr.io/githumps/grugthink:latest-optimized` |
| `v2.1.0` | Specific version | `ghcr.io/githumps/grugthink:v2.1.0` |
| `v2.1.0-rc1` | Release candidate | `ghcr.io/githumps/grugthink:v2.1.0-rc1` |

## 🔧 Production Considerations

### Resource Requirements

| Deployment Type | RAM | CPU | Storage | Network |
|-----------------|-----|-----|---------|---------|
| **Lite** | 128MB | 0.1 CPU | 1GB | Low |
| **Optimized** | 1GB | 0.5 CPU | 2GB | Medium |
| **Full** | 2GB | 1 CPU | 3GB | Medium |

### Security

- **Environment Variables**: Store sensitive data in `.env` files, not in code
- **Volume Permissions**: Ensure Docker has write access to data directory
- **Network**: Bot only needs outbound HTTPS access (Discord, APIs)
- **Updates**: Regularly update to latest stable releases

### Monitoring

**Health Check**:
```bash
# Check if bot is responding
docker-compose ps
docker-compose logs --tail 50
```

**Resource Usage**:
```bash
# Monitor resource consumption
docker stats grugthink
```

**Logs**:
```bash
# View logs
docker-compose logs -f grugthink

# Export logs
docker-compose logs grugthink > grugthink.log
```

### Backup and Recovery

**Data Backup**:
```bash
# Backup personality and knowledge data
tar -czf grugthink-backup-$(date +%Y%m%d).tar.gz grug-data/
```

**Restore from Backup**:
```bash
# Stop bot
docker-compose down

# Restore data
tar -xzf grugthink-backup-YYYYMMDD.tar.gz

# Restart bot
docker-compose up -d
```

### Scaling

For multiple servers or high load:

1. **Use lightweight images** to reduce resource usage
2. **Disable semantic search** (`LOAD_EMBEDDER=False`) if not needed
3. **Monitor memory usage** - each server gets its own personality/database
4. **Consider horizontal scaling** with multiple bot instances for different server groups

## 🚨 Troubleshooting

### Common Issues

**Bot won't start**:
```bash
# Check logs for errors
docker-compose logs grugthink

# Verify environment variables
docker-compose config
```

**Permission errors**:
```bash
# Fix data directory permissions
sudo chown -R $(id -u):$(id -g) grug-data/
```

**Memory issues**:
```bash
# Switch to lite version
docker-compose -f docker-compose.dev.yml --profile lite up -d
```

**API rate limits**:
- Check Discord token is valid
- Verify Gemini API key has quota
- Monitor usage in respective dashboards

### Support

- **Documentation**: Check other `.md` files in the repository
- **Issues**: Create GitHub issues for bugs or feature requests
- **Logs**: Always include relevant log output when reporting issues

---

**Ready to deploy your evolving Discord personality? Choose your deployment type and get started!** 🚀