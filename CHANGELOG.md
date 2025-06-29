# GrugThink Changelog

A comprehensive record of all features, improvements, and changes to the GrugThink personality engine.

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
