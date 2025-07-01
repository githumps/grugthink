# GrugThink

**Adaptable Discord Personality Engine**

GrugThink is a Discord bot platform that creates unique, evolving personalities for each Discord server. Built with a modern multi-bot architecture, it supports unlimited bot instances with different personalities through a web-based management interface.

## Features

- **🎭 Adaptive Personalities**: Each Discord server gets a unique bot personality that evolves over time
- **🌐 Web Dashboard**: Manage multiple bot instances through an intuitive web interface
- **🔄 Real-time Management**: Start, stop, configure, and monitor bots without downtime
- **🧠 Knowledge Learning**: Bots learn and remember facts through natural conversation
- **💬 Natural Interaction**: Responds to mentions without requiring slash commands
- **🔒 Secure Configuration**: Token and API key management through encrypted storage
- **📊 Analytics**: Monitor bot performance, interactions, and personality evolution

## Quick Start

1. **Clone and configure**:
```bash
git clone https://github.com/githumps/grugthink.git
cd grugthink
cp grugthink_config.yaml.example grugthink_config.yaml
```

2. **Edit your configuration**:
   Edit `grugthink_config.yaml` and set:
   - **Discord bot tokens** (from Discord Developer Portal)
   - **API keys** (Gemini for AI, Google for search)
   - **Discord OAuth** settings for web dashboard authentication
   - **Trusted user IDs** for dashboard access

3. **Deploy with Docker**:
```bash
docker-compose up -d
```

4. **Access the dashboard**:
   - Open http://localhost:8080 (or your configured domain)
   - Log in with Discord OAuth
   - Create and manage bot instances through the web interface

## Configuration

GrugThink uses a **single YAML configuration file** (`grugthink_config.yaml`) for all settings:

```yaml
api_keys:
  discord:
    tokens:
    - id: '1'
      name: "My Bot"
      token: "YOUR_DISCORD_BOT_TOKEN"
  gemini:
    primary: "YOUR_GEMINI_API_KEY"
  
environment:
  DISCORD_CLIENT_ID: "YOUR_DISCORD_APP_CLIENT_ID"
  DISCORD_CLIENT_SECRET: "YOUR_DISCORD_APP_CLIENT_SECRET"
  TRUSTED_USER_IDS: "YOUR_DISCORD_USER_ID"

bot_configs:
  my-bot:
    discord_token_id: '1'
    template_id: pure_grug
    force_personality: grug
```

**No .env file needed** - everything is managed through the YAML configuration.

## Personality System

GrugThink supports multiple personality templates that evolve based on server interactions:

- **Caveman (Grug)**: "Grug think sky is blue. Grug smart!"
- **British Working Class (Big Rob)**: "yeah mate, that's proper mental innit"
- **Adaptive**: Develops unique personality based on community interaction patterns

Each personality evolves through 4 stages based on usage and interaction patterns.

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment and scaling
- [Contributing Guide](docs/CONTRIBUTING.md) - Development setup and guidelines
- [Security Policy](docs/SECURITY.md) - Security considerations and reporting

## System Requirements

- **Docker & Docker Compose**
- **2GB RAM minimum** (4GB recommended for multiple bots)
- **500MB disk space** (plus storage for bot data)
- **Discord Application** with bot tokens
- **API Keys** (optional): Gemini, Google Search

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   Bot Manager    │    │  Discord Bots   │
│                 │────│                  │────│                 │
│  • Configuration│    │  • Orchestration │    │  • Personalities│
│  • Monitoring   │    │  • API Endpoints │    │  • Knowledge DB │
│  • Real-time UI │    │  • WebSocket     │    │  • Evolution    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## License

GNU General Public License v3.0 - See [LICENSE.md](LICENSE.md) for details.

## Support

- [GitHub Issues](https://github.com/githumps/grugthink/issues) - Bug reports and feature requests
- [Security Policy](docs/SECURITY.md) - Security vulnerability reporting