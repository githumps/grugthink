# Deployment Guide

This guide covers deploying GrugThink in production environments.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **2GB RAM minimum** (4GB recommended for multiple bots)
- **500MB disk space** plus storage for bot data
- **Discord Application** with bot tokens
- **API Keys** (optional): Gemini AI, Google Search

## Quick Deployment

### 1. Configuration

```bash
# Clone the repository
git clone https://github.com/githumps/grugthink.git
cd grugthink

# Create configuration file
cp grugthink_config.yaml.example grugthink_config.yaml
```

**GrugThink uses a single YAML configuration file** - no .env files needed!

Edit `grugthink_config.yaml` with your settings:

```yaml
api_keys:
  discord:
    tokens:
    - id: '1'
      name: "My Production Bot"
      token: "YOUR_DISCORD_BOT_TOKEN"
      active: true
  gemini:
    primary: "YOUR_GEMINI_API_KEY"  # For AI responses
  google_search:
    api_key: "YOUR_GOOGLE_API_KEY"  # For web search
    cse_id: "YOUR_CSE_ID"

environment:
  # Discord OAuth for web dashboard
  DISCORD_CLIENT_ID: "YOUR_DISCORD_APP_CLIENT_ID"
  DISCORD_CLIENT_SECRET: "YOUR_DISCORD_APP_CLIENT_SECRET" 
  DISCORD_REDIRECT_URI: "https://yourdomain.com/callback"
  
  # Who can access the dashboard
  TRUSTED_USER_IDS: "YOUR_DISCORD_USER_ID"
  
  # Bot settings
  LOG_LEVEL: "INFO"
  GRUGBOT_VARIANT: "prod"

bot_configs:
  production-grug:
    bot_id: production-grug
    name: "Production Grug Bot"
    discord_token_id: '1'  # References token above
    template_id: pure_grug
    force_personality: grug
```

### 2. Deploy

```bash
# Start the service
docker-compose up -d

# Check logs
docker logs grugthink

# Access web dashboard
open http://localhost:8080
```

## Production Configuration

### Environment Variables

Configure through `docker-compose.yml` or environment:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `GRUGBOT_DATA_DIR` | Data storage directory | `/data` |
| `LOAD_EMBEDDER` | Enable ML embeddings (true/false) | `true` |

### Security Considerations

1. **Secure Token Storage**: Store Discord tokens in `grugthink_config.yaml` with restricted file permissions
2. **Network Security**: Use reverse proxy (nginx) for HTTPS in production
3. **Data Encryption**: Mount `/data` volume with encryption for sensitive bot data
4. **Access Control**: Restrict web dashboard access using firewall rules

### Resource Requirements

| Deployment | RAM | CPU | Storage |
|------------|-----|-----|---------|
| Single Bot | 1GB | 1 vCPU | 200MB |
| Multiple Bots (2-5) | 2GB | 2 vCPU | 500MB |
| High Volume (5+) | 4GB | 4 vCPU | 1GB |

## Scaling

### Horizontal Scaling

For high-volume deployments, run multiple instances:

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  grugthink-1:
    image: grugthink:latest
    ports: ["8080:8080"]
    environment:
      - INSTANCE_ID=1
  
  grugthink-2:
    image: grugthink:latest
    ports: ["8081:8080"]
    environment:
      - INSTANCE_ID=2
```

### Load Balancing

Use nginx for load balancing multiple instances:

```nginx
upstream grugthink {
    server localhost:8080;
    server localhost:8081;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://grugthink;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Monitoring

### Health Checks

Monitor service health using built-in endpoints:

```bash
# Health check
curl http://localhost:8080/health

# Bot status
curl http://localhost:8080/api/system/stats
```

### Logs

Access logs for debugging:

```bash
# Follow logs in real-time
docker logs -f grugthink

# View specific timeframe
docker logs grugthink --since="2025-01-01T10:00:00"
```

### Metrics

The dashboard provides real-time metrics:
- Bot status and uptime
- Message processing rates
- Personality evolution statistics
- Resource usage

## Backup and Recovery

### Data Backup

```bash
# Backup bot data
docker run --rm -v grugthink_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/grugthink-backup-$(date +%Y%m%d).tar.gz /data

# Restore data
tar xzf grugthink-backup-20250101.tar.gz
docker run --rm -v grugthink_data:/data -v $(pwd):/backup alpine \
  cp -r backup/data/* /data/
```

### Configuration Backup

```bash
# Backup configuration
cp grugthink_config.yaml grugthink_config.yaml.backup
cp bot_configs.json bot_configs.json.backup
```

## Troubleshooting

### Common Issues

**Bot not connecting to Discord**:
- Verify Discord token in `grugthink_config.yaml`
- Check Discord application permissions
- Review logs: `docker logs grugthink`

**Web dashboard not accessible**:
- Ensure port 8080 is not blocked by firewall
- Check container status: `docker ps`
- Verify Docker port mapping

**High memory usage**:
- Disable embeddings with `LOAD_EMBEDDER=false`
- Reduce concurrent bots
- Monitor with `docker stats grugthink`

### Support

For additional support:
- [GitHub Issues](https://github.com/githumps/grugthink/issues)
- [Security Issues](docs/SECURITY.md)
- [Contributing Guide](docs/CONTRIBUTING.md)