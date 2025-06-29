# GrugThink – Adaptable Personality Engine

**From Character-Bound Bot to Infinite Personalities**

GrugThink is a Discord truth verification bot that evolves unique personalities for each server. What started as "Grug the Caveman" has transformed into a sophisticated personality engine capable of developing diverse characters that grow and adapt based on community interactions.

## 🧠 What GrugThink Does

### Core Features
- **🔍 Truth Verification**: Analyzes statements and responds with TRUE/FALSE + personality-styled explanations
- **🧬 Personality Evolution**: Develops unique personalities that evolve through server interactions  
- **🤖 Conversational AI**: Responds naturally when mentioned in chat (no slash commands needed)
- **📚 Semantic Memory**: Uses vector search to find relevant facts and context
- **🌐 Web Research**: Searches the internet when internal knowledge isn't sufficient
- **🗃️ Per-Server Knowledge**: Each Discord server gets its own fact database and personality

### Advanced Capabilities
- **🎭 Multiple Personality Templates**: Grug (caveman), Big Rob (norf FC lad), Adaptive (neutral AI)
- **📈 Organic Growth**: Personalities develop speech patterns, choose names, and gain quirks over time
- **🤝 Selective Bot Interaction**: Responds to Markov chain bots while ignoring spam bots
- **🔧 Docker Optimization**: Multiple image variants (401MB lite to 1.31GB full)
- **⚡ Auto-Scaling**: Efficient resource usage with on-demand model loading

## 🎮 How to Interact with GrugThink

### Natural Conversation (Recommended)
Simply mention the bot's name in your message:
```
"Grug, is the earth round?"
"Big Rob, what about Manchester United?"
"@GrugThink Paris is the capital of France"
```

### Slash Commands
- `/verify` - Verify the truthfulness of the last message
- `/learn` - Teach the bot a new fact (trusted users only)
- `/what-know` - See all facts the bot knows in this server
- `/personality` - View personality evolution status and quirks
- `/help` - Show available commands

## 🎭 Personality Examples

### Grug (Caveman)
```
User: "Grug, is water wet?"
Grug: "Grug thinking..." → "🤔 TRUE - Grug touch water, very wet thing!"
```

### Big Rob (norf FC Lad)
```
User: "Big Rob, is football popular in England?"  
Big Rob: "Big Rob thinking..." → "🤔 TRUE - wot i fink: footy is life in england, nuff said"
```

### Adaptive (Evolving AI)
```
User: "What do you think about artificial intelligence?"
Bot: "Adaptive thinking..." → "🤔 TRUE - AI technology is rapidly advancing, that's my assessment."
```

## 🚀 Getting Started

### 🔥 Multi-Bot Container (Recommended)

**Run multiple bots with web dashboard**:
```bash
# Quick start with web management interface
docker-compose up -d

# Access web dashboard at http://localhost:8080
# Create Pure Grug, Pure Big Rob, and Evolution bots
# Manage all bots from one interface
```

See **[MULTIBOT.md](MULTIBOT.md)** for complete multi-bot setup guide.

### Single Bot Deployment

**For Development/Testing (Lightweight)**:
```bash
chmod +x scripts/setup-codex.sh
./scripts/setup-codex.sh
```
*Uses mocked ML dependencies, ~200MB Docker image*

**For Production (Full Features)**:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```
*Includes semantic search, ~1.3GB Docker image*

### Docker Deployment Options

**Multi-Bot Container (Latest)**:
```bash
docker-compose up -d
```

**Single Bot - Lightweight**:
```bash
docker-compose -f examples/docker-compose/single-bot.yml up
```

**Single Bot - Development**:
```bash
docker-compose -f examples/docker-compose/development.yml up
```

**Legacy Deployments**:
```bash
docker-compose -f docker/docker-compose.dev.yml --profile lite up
```

See [DOCKER_OPTIMIZATION.md](DOCKER_OPTIMIZATION.md) for complete optimization guide.

### Manual Setup

1. **Create Virtual Environment**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Discord token and API keys
   ```

4. **Run Tests**:
   ```bash
   PYTHONPATH=. pytest
   ```

5. **Start Bot**:
   ```bash
   # Single bot mode
   python grugthink.py
   
   # Multi-bot container mode
   python grugthink.py multi-bot
   ```

## 🔧 Configuration

### Required Environment Variables
```bash
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key  # OR configure Ollama
TRUSTED_USER_IDS=123456789,987654321  # Discord user IDs for /learn command
```

### Optional Configuration
```bash
# Disable ML features for lightweight deployment
LOAD_EMBEDDER=False

# Google Search (optional)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# Ollama Configuration (alternative to Gemini)
OLLAMA_URLS=http://localhost:11434
OLLAMA_MODELS=llama3.2:3b

# Force specific personality for all servers (optional)
FORCE_PERSONALITY=grug          # Options: grug, bigrob, adaptive
# FORCE_PERSONALITY=bigrob      # Force Big Rob for all servers (also accepts: big_rob, rob)
# FORCE_PERSONALITY=adaptive    # Force neutral AI for all servers
```

## 🏗️ Architecture

### Personality Engine
- **Templates**: Base personality configurations (speech patterns, backgrounds, traits)
- **Evolution System**: 4-stage progression (Initial → Developing → Established → Evolved)
- **Server Isolation**: Each Discord server develops its own unique personality
- **Forced Personalities**: Use `FORCE_PERSONALITY` to override automatic selection
- **Persistence**: SQLite storage with personality state and evolution tracking

### Technical Stack
- **Framework**: discord.py for Discord integration
- **AI Models**: Gemini API or local Ollama models
- **Search**: Google Custom Search API for web research
- **Database**: SQLite for facts and personality storage
- **Vector Search**: FAISS for semantic fact retrieval
- **Embeddings**: SentenceTransformers for text encoding

### Docker Architecture
| Version | Size | ML Features | Use Case |
|---------|------|-------------|----------|
| **Lite** | 401MB | ❌ Disabled | Production without semantic search |
| **Optimized** | 1.06GB | ✅ Enabled | Production with semantic search |
| **Original** | 1.31GB | ✅ Enabled | Development/full features |

## 🧪 Testing

### Test Coverage
- **Unit Tests**: Core functionality, personality system, configuration
- **Integration Tests**: Discord interactions, database operations
- **CI Optimization**: Lightweight dependencies for fast builds
- **Success Rate**: 44/44 tests passing (100%)

### Run Tests
```bash
# All tests
PYTHONPATH=. pytest

# Specific test categories
PYTHONPATH=. pytest tests/test_bot.py      # Bot functionality
PYTHONPATH=. pytest tests/test_personality.py  # Personality engine
PYTHONPATH=. pytest tests/test_integration.py  # End-to-end tests

# Quick test run
PYTHONPATH=. pytest -q
```

## 📚 Documentation

### Core Guides
- **[MULTIBOT.md](MULTIBOT.md)** - Multi-bot container system with web dashboard
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide for single bots
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Organized project architecture
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development setup and contribution guidelines
- **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting

### Technical References
- **[DOCKER_OPTIMIZATION.md](DOCKER_OPTIMIZATION.md)** - Docker image size optimization
- **[BIG_ROB_EXAMPLES.md](BIG_ROB_EXAMPLES.md)** - Big Rob personality examples
- **[SETUP_COMPARISON.md](SETUP_COMPARISON.md)** - Setup option comparison
- **[CLAUDE.md](CLAUDE.md)** - Development guidelines and commands
- **[CLAUDELOG.md](CLAUDELOG.md)** - Complete development history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the style guide
4. Run tests and linting (`./dev-check.sh`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the **PolyForm Noncommercial License 1.0.0** - see the [LICENSE.md](LICENSE.md) file for details.

### License Summary
- ✅ **Noncommercial use** - Research, education, personal projects
- ✅ **Modify and share** - Create derivatives and share with others
- ✅ **Source available** - Full source code provided
- ❌ **Commercial use** - Not permitted without separate license

All dependencies are licensed under permissive open source licenses (MIT, BSD, Apache 2.0) compatible with noncommercial use.

## 🌟 Features by Version

### v3.0 - Multi-Bot Container System (Latest)
- ✅ **Multiple bot instances** in single container with different personalities
- ✅ **Web dashboard** for post-launch configuration and management
- ✅ **Real-time monitoring** with WebSocket updates and system metrics
- ✅ **Dynamic configuration** with hot-reload and environment variable management
- ✅ **Bot templates** (Pure Grug, Pure Big Rob, Evolution Bot, Lightweight, Ollama)
- ✅ **API management** for Discord tokens, Gemini keys, and Google Search
- ✅ **Process isolation** with independent bot instances and shared resources

### v2.0 - Personality Engine
- ✅ Infinite unique personalities per Discord server
- ✅ Organic personality evolution and name selection
- ✅ Auto-verification on name mention
- ✅ Markov bot interaction support
- ✅ Docker image optimization (3.5GB → 401MB)
- ✅ Big Rob personality with authentic dialect

### v1.0 - Original Grug
- ✅ Truth verification with caveman personality
- ✅ Slash commands and fact learning
- ✅ Semantic search and web research
- ✅ Per-server knowledge bases

---

**Transform your Discord server with an AI that grows and evolves with your community!** 🚀