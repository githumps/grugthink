# GrugThink Multi-Bot Container System

**Run Multiple Discord Bots with Different Personalities in a Single Container**

The GrugThink Multi-Bot Container allows you to orchestrate multiple Discord bot instances with different personalities, API keys, and configurations through a single web dashboard.

## 🌟 Features

### Core Capabilities
- **Multiple Bot Instances**: Run Pure Grug, Pure Big Rob, Evolution Bot, and custom personalities simultaneously
- **Web Dashboard**: Post-launch configuration through an intuitive web interface
- **Dynamic Configuration**: Hot-reload environment variables without container restart
- **Real-time Monitoring**: Live bot status, server counts, and activity logs
- **API Management**: Centralized Discord tokens, Gemini keys, and Google Search API management

### Advanced Features
- **Process Isolation**: Each bot runs independently with its own configuration
- **Bot Templates**: Pre-configured setups for different use cases
- **Shared Resources**: Optional shared Gemini/Ollama pools for efficiency
- **Auto-scaling**: Automatic restarts and health monitoring
- **Backup/Restore**: Export and import bot configurations

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/githumps/grugthink.git
cd grugthink

# Start multi-bot container
docker-compose -f docker-compose.multibot.yml up -d

# Visit web dashboard
open http://localhost:8080
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create demo configuration (optional)
python main.py --create-demo

# Start multi-bot container
python main.py
```

## 📊 Web Dashboard

Access the management dashboard at **http://localhost:8080**

### Dashboard Sections

#### 1. **Dashboard** - System Overview
- Total bots, running instances, Discord servers, and users
- Real-time activity log with bot status changes
- System performance metrics

#### 2. **Bot Instances** - Bot Management
- Create, start, stop, restart, and delete bot instances
- Live status monitoring with server counts
- Per-bot configuration and personality settings

#### 3. **Configuration** - API Management
- Add multiple Discord bot tokens
- Configure Gemini API keys (primary, secondary, fallback)
- Set up Google Search API credentials
- Environment variable management

#### 4. **Templates** - Bot Presets
- **Pure Grug**: Caveman personality only, no evolution
- **Pure Big Rob**: norf FC lad personality only  
- **Evolution Bot**: Adaptive personality that evolves per server
- **Lightweight Grug**: Grug without semantic search
- **Ollama Bot**: Uses local Ollama instead of Gemini

#### 5. **Monitoring** - Logs & Analytics
- System logs with filtering and search
- Bot performance metrics
- Error tracking and debugging

## 🎭 Bot Templates

### Pre-configured Templates

| Template | Personality | ML Features | Use Case |
|----------|-------------|-------------|----------|
| **Pure Grug** | Caveman only | Full | Single-personality servers |
| **Pure Big Rob** | norf FC lad only | Full | British football communities |
| **Evolution Bot** | Adaptive | Full | Multi-server personality evolution |
| **Lightweight Grug** | Caveman only | Disabled | Resource-constrained deployments |
| **Multi-Personality** | Random selection | Full | Diverse server personalities |
| **Ollama Bot** | Adaptive | Full | Local AI model usage |

### Creating Custom Templates

Add custom templates to `grugthink_config.yaml`:

```yaml
bot_templates:
  custom_bot:
    name: "Custom Bot"
    description: "My custom personality configuration"
    force_personality: "grug"
    load_embedder: true
    default_gemini_key: true
    custom_env:
      CUSTOM_SETTING: "value"
```

## ⚙️ Configuration Management

### Environment Variables

The system supports dynamic environment variable management:

```yaml
environment:
  LOG_LEVEL: "INFO"
  GRUGBOT_VARIANT: "prod"
  LOAD_EMBEDDER: "True"
  FORCE_PERSONALITY: "grug"  # Optional global override
```

### API Key Management

Configure multiple API keys for redundancy:

```yaml
api_keys:
  gemini:
    primary: "your_primary_gemini_key"
    secondary: "your_backup_gemini_key"
    fallback: "your_fallback_key"
  google_search:
    api_key: "your_google_api_key"
    cse_id: "your_custom_search_engine_id"
  discord:
    tokens:
      - id: "1"
        name: "Main Bot Token"
        token: "your_discord_token_1"
        active: true
      - id: "2"
        name: "Backup Bot Token"
        token: "your_discord_token_2"
        active: true
```

### Discord Token Management

Add multiple Discord tokens through the web interface:

1. Go to **Configuration** tab
2. Enter token name and Discord bot token
3. Token is automatically available for new bot instances
4. Tokens can be reused across multiple bot instances

## 🐳 Docker Deployment

### Standard Deployment

```bash
docker-compose -f docker-compose.multibot.yml up -d
```

### Advanced Deployment (with Redis & PostgreSQL)

```bash
docker-compose -f docker-compose.multibot.yml --profile advanced up -d
```

### Custom Configuration

Mount your configuration files:

```yaml
services:
  grugthink-multibot:
    volumes:
      - ./my-config.yaml:/app/grugthink_config.yaml:rw
      - ./my-bots.json:/app/bot_configs.json:rw
```

## 🔧 API Reference

### Bot Management

```bash
# List all bots
GET /api/bots

# Create new bot
POST /api/bots
{
  "name": "My Bot",
  "template_id": "pure_grug",
  "discord_token": "token_here",
  "gemini_api_key": "optional_key"
}

# Start/stop/restart bot
POST /api/bots/{bot_id}/start
POST /api/bots/{bot_id}/stop
POST /api/bots/{bot_id}/restart

# Delete bot
DELETE /api/bots/{bot_id}
```

### Configuration Management

```bash
# Get configuration
GET /api/config

# Update configuration
PUT /api/config
{
  "key": "environment.LOG_LEVEL",
  "value": "DEBUG"
}

# Add Discord token
POST /api/discord-tokens
{
  "name": "My Bot Token",
  "token": "discord_token_here"
}

# Set API key
POST /api/api-keys
{
  "service": "gemini",
  "key_name": "primary",
  "value": "api_key_here"
}
```

### System Information

```bash
# Get system stats
GET /api/system/stats

# Get logs
GET /api/system/logs
```

## 🔌 WebSocket Updates

Real-time updates are delivered via WebSocket at `/ws`:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data.type, data.data);
};
```

### Event Types

- `bot_status_changed`: Bot started/stopped/error
- `bot_created`: New bot instance created
- `bot_deleted`: Bot instance deleted
- `config_updated`: Configuration changed
- `token_added`: New Discord token added
- `api_key_updated`: API key updated

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   REST API      │    │   Bot Manager   │
│   (Frontend)    │◄──►│   (FastAPI)     │◄──►│   (Orchestrator)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Config Manager  │    │   Bot Instance  │
                       │ (Hot-reload)    │    │   (Discord Bot) │
                       └─────────────────┘    └─────────────────┘
```

### Process Isolation

Each bot instance runs in its own:
- Asyncio task with independent event loop
- Database connection (SQLite per bot)
- Personality engine instance
- Configuration environment
- Data directory (`/data/{bot_id}/`)

### Resource Sharing

Shared components:
- Configuration manager (hot-reload)
- API server (web dashboard)
- Monitoring system
- Optional: Gemini API pool, Redis cache

## 🎯 Use Cases

### 1. Multi-Community Management
Run different personalities for different Discord communities:
- Gaming servers: Grug personality
- UK Football: Big Rob personality  
- Tech communities: Adaptive evolution

### 2. Development & Testing
Test different configurations simultaneously:
- Production bot with full features
- Development bot with debug logging
- Staging bot with experimental features

### 3. High Availability
Multiple bot instances with fallback:
- Primary bot with main Discord token
- Backup bot with secondary token
- Auto-failover on primary bot failure

### 4. Resource Optimization
Optimize resources based on server load:
- Lightweight bots for low-activity servers
- Full-featured bots for active communities
- Shared API keys and rate limiting

## 🔐 Security Considerations

### API Key Management
- API keys stored in encrypted configuration
- Web interface never displays actual key values
- Separate keys per bot instance supported
- Automatic key rotation capabilities

### Bot Isolation
- Each bot instance isolated from others
- Independent database and file systems
- No cross-bot data sharing
- Secure token management

### Network Security
- Web dashboard access control (add authentication)
- HTTPS support for production deployments
- Rate limiting on API endpoints
- Input validation and sanitization

## 🚨 Troubleshooting

### Common Issues

**Bot won't start:**
```bash
# Check logs in web dashboard or:
docker logs grugthink-multibot

# Verify Discord token is valid
# Check API key configuration
```

**Web dashboard not accessible:**
```bash
# Verify port mapping
docker ps

# Check firewall settings
sudo ufw allow 8080
```

**Configuration not saving:**
```bash
# Check file permissions
ls -la grugthink_config.yaml

# Verify volume mounts
docker inspect grugthink-multibot
```

### Debug Mode

Enable debug logging:

```yaml
environment:
  LOG_LEVEL: "DEBUG"
```

Or via API:
```bash
curl -X PUT http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d '{"key": "environment.LOG_LEVEL", "value": "DEBUG"}'
```

## 📈 Scaling & Performance

### Resource Requirements

| Deployment | RAM per Bot | CPU | Storage |
|------------|-------------|-----|---------|
| **Lightweight** | 64MB | 0.1 CPU | 100MB |
| **Standard** | 256MB | 0.2 CPU | 500MB |
| **Full Features** | 512MB | 0.5 CPU | 1GB |

### Scaling Recommendations

- **1-5 bots**: Single container sufficient
- **5-20 bots**: Add Redis for caching
- **20+ bots**: Consider horizontal scaling with load balancer
- **High load**: Use dedicated Gemini API keys per bot

### Performance Optimization

```yaml
# Shared Gemini API pool
global_settings:
  gemini_pool_size: 10
  rate_limit_per_key: 100
  enable_caching: true

# Bot-specific optimizations
bot_templates:
  high_performance:
    load_embedder: false  # Disable for faster startup
    custom_env:
      RATE_LIMIT_REQUESTS: "50"
      CACHE_SIZE: "1000"
```

## 🎉 Getting Started Example

Here's a complete example to get you started:

```bash
# 1. Start the container
docker-compose -f docker-compose.multibot.yml up -d

# 2. Open web dashboard
open http://localhost:8080

# 3. Add your Discord tokens (Configuration tab)
#    - Add your first Discord bot token

# 4. Add API keys (Configuration tab)  
#    - Add your Gemini API key
#    - Optionally add Google Search API

# 5. Create your first bot (Bot Instances tab)
#    - Click "Create Bot"
#    - Choose "Pure Grug" template
#    - Select your Discord token
#    - Click "Create Bot"

# 6. Start the bot
#    - Click the green play button
#    - Watch it connect to Discord servers

# 7. Create more bots with different personalities!
```

## 📚 Next Steps

- Explore advanced templates and customization
- Set up monitoring and alerting
- Configure backup and disaster recovery
- Scale to multiple Discord communities
- Contribute new personality templates

---

**Ready to manage multiple Discord personalities with ease? Start your multi-bot container today!** 🚀