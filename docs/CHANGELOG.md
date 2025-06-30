# GrugThink Changelog

A comprehensive record of all features, improvements, and changes to the GrugThink personality engine.

## [Unreleased]

- Updated documentation for moved test files
- Fixed broken documentation links in README.md
- Added module docstrings to remaining test modules

## [3.1.0] - 2025-06-30

### 🐛 Fixed: Multi-Bot Collision Issues
- **Fixed** bot collision where multiple bots responded to single name mention
- **Removed** hardcoded common names causing all bots to respond to "grug"/"grugthink"
- **Enhanced** name filtering to only respond to specific bot name + @mentions
- **Resolved** personality mixing between Big Rob and Grug instances

### 📚 Fixed: Knowledge Learning System
- **Fixed** `/what-know` command not showing learned facts for non-Grug personalities
- **Reworked** knowledge extraction to work with any bot personality
- **Enhanced** fact extraction from bot responses with better filtering
- **Added** contextual storage with personality name prefixes

### 🎭 Enhanced: Big Rob Personality
- **Updated** Big Rob to prefer Carling beer (his absolute favorite)
- **Reduced** Big Rob's verbosity to maximum 2 sentences
- **Added** verbosity personality trait for response length control
- **Improved** British working-class dialect authenticity

### 🎨 UI Improvements
- **Removed** thinking emoji (🤔) from bot responses
- **Cleaned** response formatting for better readability

### 🧪 Development
- **Fixed** all test suite failures (43/43 tests passing)
- **Resolved** line length linting errors
- **Updated** test mocks to match current bot behavior
- **Applied** code formatting across entire codebase

### 🚀 CI/CD Improvements
- **Fixed** GitHub Actions Docker build failure (missing Dockerfile specification)
- **Updated** release workflow to use correct multi-bot Dockerfile path
- **Added** multi-architecture builds (linux/amd64, linux/arm64)
- **Enhanced** Docker build caching for faster CI builds
- **Updated** action versions for better security and compatibility

## [3.0.0] - 2025-06-29

### 🚀 Major: Multi-Bot Container System
- **Added** multi-bot container orchestration with web dashboard
- **Implemented** FastAPI REST API with WebSocket support for real-time updates
- **Created** responsive web dashboard for post-launch configuration
- **Added** dynamic configuration management with hot-reload capabilities
- **Implemented** process isolation for independent bot instances

### 🎛️ Bot Management Platform
- **Added** bot templates: Pure Grug, Pure Big Rob, Evolution Bot, Lightweight, Ollama
- **Implemented** real-time bot monitoring with status indicators
- **Created** centralized Discord token and API key management
- **Added** bot start/stop/restart functionality via web interface
- **Implemented** system metrics dashboard with live updates

### 🔧 Configuration Management
- **Added** YAML-based configuration with file watching
- **Implemented** environment variable management through web interface
- **Created** bot configuration templates and presets
- **Added** backup/restore functionality for bot configurations
- **Enhanced** `.env.example` with comprehensive variable documentation

### 🖥️ Web Dashboard Features
- **Built** responsive Bootstrap-based frontend
- **Added** real-time WebSocket updates for bot status changes
- **Implemented** activity logging with timestamps
- **Created** configuration forms for tokens and API keys
- **Added** bot template selection and creation wizard

### 🐳 Enhanced Docker Support
- **Created** `Dockerfile.multibot` for multi-bot container deployments
- **Added** `docker-compose.multibot.yml` with Redis and PostgreSQL options
- **Implemented** health checks and container monitoring
- **Added** volume mounts for persistent configuration

## [2.0.0] - 2025-06-29

### 🧬 Major: Personality Engine Architecture
- **Transformed** from single-character bot to adaptable personality engine
- **Added** three personality templates: Grug (caveman), Big Rob (norf FC lad), Adaptive (evolving AI)
- **Implemented** organic personality evolution system with 4 progression stages
- **Created** per-server personality isolation and development
- **Added** personality name evolution and quirk development

### 🗣️ Conversational Auto-Verification
- **Added** natural conversation support - mention bot name to verify statements
- **Implemented** intelligent name detection with multiple trigger patterns
- **Enhanced** user experience with personality-aware thinking messages
- **Maintained** existing slash command functionality alongside natural conversation

### 🤖 Selective Bot Interaction
- **Enabled** interaction with Markov chain bots while filtering other bots
- **Added** special bot-to-bot acknowledgment messages
- **Implemented** bot-aware thinking responses for each personality
- **Enhanced** logging for bot interaction monitoring

### 🎭 Big Rob Personality Enhancement
- **Upgraded** Big Rob with authentic norf FC dialect transformation
- **Added** comprehensive word replacements ("what"→"wot", "have"→"av", etc.)
- **Implemented** catchphrases and cultural references ("nuff said", "simple as")
- **Created** regex-based dialect processing system

### 🐳 Docker Optimization
- **Reduced** image size from 3.5GB to 401MB (lite version)
- **Created** three deployment variants: lite (401MB), optimized (1.06GB), full (1.31GB)
- **Added** configurable ML dependency loading via `LOAD_EMBEDDER` flag
- **Implemented** lazy loading for embedding models

### 🧪 Testing Infrastructure Overhaul
- **Achieved** 44/44 tests passing (100% success rate)
- **Added** comprehensive integration tests for Discord functionality
- **Implemented** CI optimization with mocked ML dependencies
- **Created** deterministic embedding mocks for consistent test results

### 📚 Documentation Refresh
- **Rewrote** README.md as comprehensive personality engine guide
- **Updated** DEPLOYMENT.md with Docker optimization options
- **Enhanced** LICENSE formatting to professional markdown
- **Added** detailed architecture and feature documentation

### 🔧 Technical Improvements
- **Fixed** memory leak with LRU cache implementation
- **Removed** models from repository to resolve LFS budget issues
- **Added** external model download system with cache management
- **Enhanced** security logging (user IDs vs names, content lengths vs content)

## [1.0.0] - 2025-06-27

### 🚀 Initial Release
- **Launched** Discord truth verification bot with caveman personality
- **Implemented** SQLite and FAISS vector search for fact storage
- **Added** slash commands: `/verify`, `/learn`, `/what-know`, `/help`
- **Created** semantic search and web research capabilities
- **Established** per-server knowledge bases and fact learning
