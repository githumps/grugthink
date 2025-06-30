# GrugThink Changelog

A comprehensive record of all features, improvements, and changes to the GrugThink personality engine.
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Major Simplification
- **Unified architecture**: Removed single-bot deployment methods, simplified to multi-bot Docker only
- **Streamlined Docker**: Single Dockerfile and docker-compose.yml for all deployments
- **Documentation cleanup**: Removed redundant docs, focused on essential guides
- **Project structure**: Cleaned up directories and removed unnecessary complexity

### Fixed
- **Memory isolation**: Fixed critical bug where multiple Discord bot instances shared memories by implementing unique database paths based on Discord token hash
- **Command truncation**: Fixed `/what-know` command getting cut off by implementing proper Discord embed field limits (1024 characters)
- **Logging timestamps**: Added timestamps to log output for better debugging
- **Bot deletion bug**: Fixed critical issue where deleting bot configs via web interface didn't stop running bot instances, causing persistent double responses

### Changed
- Database paths now include token hash for isolation (e.g., `grug_lore_a1b2c3d4e5f6.db`)
- `/what-know` command now shows "Facts (Showing X of Y)" when truncated
- Log format now includes timestamps: `YYYY-MM-DD HH:MM:SS - module - LEVEL - message`
- Bot deletion via web interface now properly awaits bot shutdown before removing config
- Single Docker deployment method with web dashboard management

### Technical
- Consolidated Docker structure: removed single-bot, lite, optimized variants
- Simplified project structure and removed redundant examples
- Updated `src/grugthink/config.py` to generate unique database paths
- Rewrote `/what-know` command truncation logic in `src/grugthink/bot.py`
- Enhanced logging configuration with timestamp formatting
- Fixed async/await bug in `bot_manager.py` delete_bot function
- Updated API server to properly await bot deletion
- All tests passing (43 passed, 1 skipped)

- Updated documentation for moved test files
- Fixed broken documentation links in README.md
- Added module docstrings to remaining test modules

## [3.2.0] - 2025-06-30

### 🔧 Fixed: Memory Isolation
- **Fixed** memory sharing between bots in same Discord server
- **Updated** bot architecture to use server-specific databases per Discord guild
- **Enhanced** single/multi-bot compatibility with proper fallbacks

### 📊 Enhanced: Command Interface
- **Improved** `/what-know` command with smart pagination for large memory lists
- **Added** Discord message limit handling for memory display
- **Enhanced** fact truncation with personality-appropriate messages

### 🎨 Fixed: Web Dashboard
- **Fixed** navbar/sidebar overlap in multi-bot web interface
- **Added** user display and logout functionality in navigation
- **Enhanced** CSS layout with proper spacing and responsive design

### 🐳 Fixed: Docker Container
- **Fixed** FastAPI import errors preventing container startup
- **Added** missing dependencies for session middleware
- **Updated** OAuth configuration for custom domains

### 🔐 Enhanced: Authentication
- **Fixed** Discord OAuth redirect URI handling for custom domains
- **Added** automatic login redirect for unauthenticated users
- **Enhanced** session management and user info display

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
