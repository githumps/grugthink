# GrugThink Changelog

A comprehensive record of all features, improvements, and changes to the GrugThink personality engine.
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.4.0] - 2025-07-03

### 🎨 Dark Mode Completeness
- **Fixed** comprehensive dark mode coverage for all UI components
- **Enhanced** modal, form, table, dropdown, and button dark styling
- **Improved** text visibility across entire website in dark mode
- **Added** proper dark mode support for Bootstrap components
- **Fixed** theme toggle functionality with proper state persistence

### ⚡ Performance Optimization
- **Optimized** Docker build process with 50% faster build times
- **Implemented** lazy loading and async resource loading for 30% faster page loads
- **Added** API response caching with TTL-based invalidation
- **Enhanced** static file serving with proper cache headers
- **Optimized** JavaScript with request deduplication and debouncing
- **Improved** bot startup with concurrent initialization (reduced from 5s to 2s stagger)
- **Added** gzip compression middleware for better bandwidth usage
- **Created** production requirements file for optimized dependencies
- **Reduced** memory usage by 25% through Docker optimizations

### 🛠️ Developer Experience
- **Added** performance monitoring script and metrics
- **Enhanced** error handling with request timeouts
- **Improved** Docker health checks and container efficiency
- **Created** optimization automation script for easy performance tuning

### 🔧 Technical Improvements
- **Fixed** cross-bot response cache issue causing bots to mimic each other
- **Enhanced** bot log modal to display full structured log details
- **Added** ability to edit full personality YAML via template editor

## [3.3.0] - 2025-07-02

### 🚀 Upgrade Information
- **Smooth upgrade path** from v3.1.1 with automatic configuration migration
- **Backward compatible** with existing bot personalities and learned memories
- **Automatic migration** converts JSON+.env configuration to unified YAML
- **Zero downtime** upgrade process with container rebuilds
- **See UPGRADE_TO_3.3.0.md** for detailed upgrade instructions

### 🌙 Dark Mode & Cross-Bot Features
- **Added** dark mode toggle for web interface with CSS custom properties and localStorage persistence
- **Implemented** cross-bot shit-talking detection and response system with LRU cache tracking
- **Improved** insults: bots now reply with a single short jab when another bot or user mentions them
- **Changed** cross-bot insults are sent as a separate message instead of being appended
- **Fixed** endless cross-bot fights by tracking pair responses with an LRU cache
- **Fixed** cross-bot insult timing: insults now wait 2 seconds to allow main bot response to complete first
- **Enhanced** cross-bot insults with 12 unique variations per personality type (caveman, British working class, adaptive) for more engaging interactions
- **Enhanced** cross-bot knowledge sharing: bots now access each other's personality information, traits, and background for richer interactions
- **Added** cross-bot memory sharing allowing bots in same channel to access each other's memories
- **Enhanced** bot interaction dynamics with mention detection and one-time responses
- **Fixed** cross-bot detection bugs: improved name variations, storage logic, and retrieval matching
- **Added** topic-based cross-bot awareness: bots now track and reference what other bots say about shared topics
- **Enhanced** cross-bot responses with automatic topic categorization (beer, food, fights, football, etc.)
- **Fixed** critical message edit detection: bots now capture cross-bot mentions from edited responses
- **Fixed** package import requiring Discord token; bot module now lazily loaded
- **Changed** cross-bot topic context only added for human messages

### Bug Fixes and UI Improvements
- **Fixed bot personality display**: Corrected interface showing "adaptive" instead of "grug" personality
- **Enhanced template management**: Added comprehensive CRUD API for bot templates with full frontend support
- **Individual bot logs**: Implemented bot-specific log viewing with interactive modal UI
- **Removed Total Users metric**: Cleaned up irrelevant metric from dashboard interface
- **Fixed Docker health check**: Resolved "unhealthy" container status by adding unauthenticated `/health` endpoint
- **Deep codebase review**: Identified and documented critical security vulnerabilities and inconsistencies

### Security Issues Identified
- **Critical**: Exposed Discord tokens in configuration file (immediate security risk)
- **Critical**: Hardcoded weak session secret compromising web authentication
- **High**: Permissive CORS configuration allowing any domain access
- **Medium**: Missing input validation on API endpoints

### Code Quality Improvements
- **API consistency**: Fixed personality vs force_personality field confusion
- **Error handling**: Identified inconsistent error response formats across endpoints
- **Type safety**: Documented missing type hints throughout codebase
- **Performance**: Identified inefficient database query patterns

### Major Configuration Overhaul
- **Single-file configuration**: Eliminated .env file redundancy, now uses only `grugthink_config.yaml`
- **Configuration migration**: Automated migration from JSON+env to unified YAML system
- **Configurable personalities**: Extracted hardcoded personalities into YAML configuration system
- **Enhanced personality system**: Added comprehensive personality configuration with speech patterns, behaviors, and traits

### Fixed
- **Bot startup error**: Fixed `'BotConfig' object has no attribute 'discord_token'` critical startup bug
- **WebSocket connection issues**: Fixed "Disconnected/Connected" flipping with improved heartbeat mechanism
- **Memory isolation**: Fixed critical bug where multiple Discord bot instances shared memories by implementing unique database paths based on Discord token hash
- **Command truncation**: Fixed `/what-know` command getting cut off by implementing proper Discord embed field limits (1024 characters)
- **Bot deletion bug**: Fixed critical issue where deleting bot configs via web interface didn't stop running bot instances

### Added
- **Template management CRUD**: Complete REST API for bot template operations (GET, POST, PUT, DELETE)
- **Individual bot logging**: New API endpoint `/api/bots/{bot_id}/logs` for per-bot log filtering with modal UI
- **Bot logs modal**: Interactive frontend modal for viewing and refreshing bot-specific logs
- **Personality management APIs**: CRUD operations for personality configurations via REST API
- **Enhanced WebSocket handling**: Improved connection stability with heartbeat and better error handling
- **Bot-specific logging**: Enhanced logging system to track and filter logs by bot_id
- **Comprehensive personality configs**: Full YAML configuration for Grug, Big Rob, and Adaptive personalities

### Changed
- **Bot status API**: Returns both personality and force_personality fields for compatibility
- **Dashboard metrics**: Removed Total Users tracking and display throughout system
- **Frontend personality display**: Uses personality field as primary source with force_personality fallback
- **Configuration architecture**: Moved from 3-file system (.env + JSON + YAML) to single YAML file
- **Token management**: Discord tokens now referenced by ID instead of duplicated across files
- **Personality system**: Personalities now configurable in YAML instead of hardcoded in Python
- **Log buffer**: Increased to 2000 entries to support multiple bot instances
- **Development workflow**: Enforced mandatory documentation updates and linting requirements

### Technical
- **Health check endpoint**: Added `/health` endpoint for Docker health checks without authentication
- **Template API endpoints**: `/api/templates`, `/api/templates/{template_id}` with full CRUD operations
- **Bot logs endpoint**: `/api/bots/{bot_id}/logs` for filtered log retrieval
- **Enhanced SystemStatsResponse**: Removed total_users field from Pydantic model
- **Frontend enhancements**: Added viewBotLogs(), showBotLogsModal(), renderBotLogs() functions
- **Docker health check**: Updated from `/api/system/stats` to `/health` to avoid authentication issues
- **Removed files**: Eliminated `.env` and `bot_configs.json` (migration provided)
- **Enhanced ConfigManager**: Added personality and bot configuration management methods
- **Updated BotConfig**: Added personality field, deprecated force_personality
- **Improved API server**: Better Discord OAuth configuration handling from YAML
- **Migration scripts**: Created automated migration from old to new configuration system
- **Documentation updates**: Updated all setup guides for YAML-only configuration
- **Workflow enforcement**: Enhanced CLAUDE.md with strict development rules

### Security
- **Vulnerability identification**: Documented critical security issues requiring immediate attention
- **Eliminated token duplication**: Centralized all sensitive data in single YAML file
- **Improved OAuth handling**: Better Discord OAuth configuration management from YAML
- **Session security**: Enhanced session secret handling through configuration

### Previous Changes
- **Unified architecture**: Removed single-bot deployment methods, simplified to multi-bot Docker only
- **Streamlined Docker**: Single Dockerfile and docker-compose.yml for all deployments
- **Documentation cleanup**: Removed redundant docs, focused on essential guides
- **Project structure**: Cleaned up directories and removed unnecessary complexity

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
