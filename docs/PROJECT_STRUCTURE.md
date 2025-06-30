# GrugThink Project Structure

This document describes the organized project structure following Python packaging best practices.

## 📁 Directory Structure

```
grugthink/
├── 📄 README.md                    # Main project documentation
├── 📄 LICENSE.md                   # Project license
├── 📄 pyproject.toml               # Python project configuration
├── 📄 requirements.txt             # Production dependencies
├── 📄 requirements-dev.txt         # Development dependencies
├── 📄 .env.example                 # Environment variables example
├── 📄 docker-compose.yml           # Main multi-bot deployment
├── 🐍 grugthink.py                 # Main entry point
│
├── 📂 src/grugthink/              # Source code (Python package)
│   ├── 📄 __init__.py             # Package initialization
│   ├── 🤖 bot.py                  # Core Discord bot
│   ├── 🧠 personality_engine.py   # Personality system
│   ├── 🗄️ grug_db.py             # Database and vector search
│   ├── ⚙️ config.py               # Configuration management
│   ├── 📊 grug_structured_logger.py # Logging utilities
│   ├── 🎛️ bot_manager.py          # Multi-bot orchestration
│   ├── 🔧 config_manager.py       # Dynamic configuration
│   ├── 🌐 api_server.py           # REST API and WebSocket
│   └── 📋 main.py                 # Multi-bot container entry
│
├── 📂 docker/                     # Docker configurations
│   ├── 📂 single-bot/
│   │   └── 📄 Dockerfile          # Single bot container
│   ├── 📂 multi-bot/
│   │   ├── 📄 Dockerfile.multibot # Multi-bot container
│   │   └── 📂 web/               # Web dashboard assets
│   │       ├── 📄 index.html
│   │       └── 📂 static/
│   ├── 📂 lite/
│   │   └── 📄 Dockerfile.lite     # Lightweight container
│   ├── 📂 optimized/
│   │   └── 📄 Dockerfile.optimized # Optimized container
│   ├── 📄 docker-compose.multibot.yml
│   ├── 📄 docker-compose.dev.yml
│   └── 📄 docker-compose.yml
│
├── 📂 scripts/                    # Utility scripts
│   ├── 📄 setup.sh               # Full setup script
│   ├── 📄 setup-codex.sh         # Lightweight setup
│   └── 📄 build-docker.sh        # Docker build script
│
├── 📂 tests/                      # Test suite
│   ├── 📄 conftest.py            # Test configuration
│   ├── 📄 pytest.ini             # Pytest settings
│   ├── 🧪 test_bot.py            # Bot functionality tests
│   ├── 🧪 test_config.py         # Configuration tests
│   ├── 🧪 test_grug_db.py        # Database layer tests
│   └── 🧪 test_integration.py    # Integration tests
│
├── 📂 docs/                       # Documentation
│   ├── 📄 README.md              # Main documentation (symlink)
│   ├── 📄 MULTIBOT.md            # Multi-bot container guide
│   ├── 📄 DEPLOYMENT.md          # Deployment guide
│   ├── 📄 CONTRIBUTING.md        # Contribution guidelines
│   ├── 📄 SECURITY.md            # Security policy
│   ├── 📄 CHANGELOG.md           # Version history
│   ├── 📄 PROJECT_STRUCTURE.md   # This file
│   ├── 📄 DOCKER_OPTIMIZATION.md # Docker optimization guide
│   ├── 📄 BIG_ROB_EXAMPLES.md    # Big Rob personality examples
│   ├── 📄 SETUP_COMPARISON.md    # Setup options comparison
│   ├── 📄 CLAUDE.md              # Development guidelines
│   └── 📄 CLAUDELOG.md           # Development history
│
├── 📂 examples/                   # Example configurations
│   ├── 📂 configs/
│   │   └── 📄 grugthink_config.example.yaml
│   ├── 📂 docker-compose/
│   │   ├── 📄 single-bot.yml
│   │   └── 📄 development.yml
│   └── 📂 personalities/
│       └── (custom personality templates)
│
└── 📂 data/                       # Runtime data (gitignored)
    ├── 📄 personalities.db       # Personality storage
    ├── 📄 grug_lore.db          # Facts database
    └── 📂 bot-instances/          # Per-bot data directories
```

## 🏗️ Architecture Overview

### Core Components

#### **Source Code (`src/grugthink/`)**
- **Modular Python Package**: Proper Python package structure with `__init__.py`
- **Core Bot (`bot.py`)**: Discord integration and command handling
- **Personality Engine (`personality_engine.py`)**: Multi-personality system
- **Database Layer (`grug_db.py`)**: Vector search and fact storage
- **Multi-Bot System**: Container orchestration and management

#### **Docker Organization (`docker/`)**
- **Single Bot**: Traditional single-instance deployment
- **Multi-Bot**: Container with web dashboard and multiple instances
- **Lite/Optimized**: Size-optimized variants for different use cases
- **Compose Files**: Different deployment scenarios

#### **Documentation (`docs/`)**
- **User Guides**: Setup, deployment, and usage instructions
- **Developer Docs**: Contributing, architecture, and development workflow
- **Reference**: API documentation, examples, and troubleshooting

#### **Examples (`examples/`)**
- **Configuration Templates**: Ready-to-use config files
- **Docker Compose Examples**: Different deployment scenarios
- **Personality Templates**: Custom personality configurations

## 🚀 Entry Points

### Main Entry Point (`grugthink.py`)
```bash
# Single bot mode (default)
python grugthink.py

# Multi-bot container mode
python grugthink.py multi-bot

# With arguments
python grugthink.py multi-bot --api-port 8080
```

### Docker Deployments
```bash
# Multi-bot container (recommended)
docker-compose up

# Single bot
docker-compose -f examples/docker-compose/single-bot.yml up

# Development
docker-compose -f examples/docker-compose/development.yml up
```

### Development Mode
```bash
# Direct Python execution
cd src && python -m grugthink.bot

# With custom Python path
PYTHONPATH=src python -m grugthink.main
```

## 📦 Python Package Structure

The source code follows Python packaging best practices:

```python
# Package imports
from grugthink import PersonalityEngine, GrugDB, BotManager
from grugthink.config import Config
from grugthink.personality_engine import PersonalityTemplate

# Version information
from grugthink import __version__
```

### Key Benefits
- **Clean Imports**: No more relative import issues
- **Testability**: Easier unit testing and mocking
- **Distribution**: Can be packaged as a proper Python package
- **IDE Support**: Better code completion and refactoring
- **Modularity**: Clear separation of concerns

## 🔧 Configuration Management

### Environment Variables
- **Root Level**: `.env` for container-wide settings
- **Examples**: `.env.example` with comprehensive documentation
- **Container**: Environment passed through Docker

### Configuration Files
- **YAML Config**: `grugthink_config.yaml` for complex settings
- **Bot Configs**: `bot_configs.json` for multi-bot instances
- **Examples**: Template configurations in `examples/configs/`

## 🧪 Testing Structure

### Test Organization
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Fixtures**: Shared test data and mocks in `conftest.py`
- **CI/CD**: Optimized for fast continuous integration

### Running Tests
```bash
# All tests
pytest

# Specific module
pytest tests/test_bot.py

# With coverage
pytest --cov=src/grugthink
```

## 📚 Documentation Strategy

### Hierarchical Documentation
1. **README.md**: Quick start and overview
2. **MULTIBOT.md**: Comprehensive multi-bot guide
3. **DEPLOYMENT.md**: Production deployment
4. **Specialized Guides**: Feature-specific documentation

### Cross-References
- Consistent linking between documents
- Clear navigation paths
- Searchable content structure

## 🔄 Migration from Old Structure

### What Changed
- **Python Files**: Moved to `src/grugthink/` package
- **Docker Files**: Organized by deployment type
- **Documentation**: Centralized in `docs/` directory
- **Scripts**: Separated into `scripts/` directory
- **Examples**: New `examples/` directory with templates

### Backward Compatibility
- **Docker Compose**: Updated to reference new structure
- **Entry Points**: `grugthink.py` maintains familiar interface
- **Environment**: Same environment variables work
- **Data**: Existing data directories preserved

### Benefits of New Structure
- **Professional**: Follows Python packaging standards
- **Scalable**: Easier to add new features and components
- **Maintainable**: Clear separation of concerns
- **Testable**: Better testing and CI/CD integration
- **Documented**: Comprehensive documentation organization

---

**The organized structure makes GrugThink more professional, maintainable, and ready for scaling to larger deployments!** 🚀