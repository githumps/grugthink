# Contributing to GrugThink

Thank you for your interest in contributing to GrugThink! This guide will help you get started with contributing to our adaptable Discord personality engine.

## Before You Start

*   **Discuss major changes first:** For significant features or architectural changes, please create a GitHub issue to discuss your proposal before starting work. This prevents duplicate effort and ensures alignment with project goals.

## Development Setup

### Quick Setup Options

**Multi-Bot Development (Latest)**:
```bash
# Start multi-bot container for development
docker-compose -f examples/docker-compose/development.yml up -d
# Access web dashboard at http://localhost:8080
```
*Includes web dashboard, live code reload, and multiple bot instances*

**Lightweight Development**:
```bash
chmod +x scripts/setup-codex.sh
./scripts/setup-codex.sh
```
*Uses mocked ML dependencies for fast testing*

**Full Development Environment**:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```
*Includes semantic search capabilities*

### Manual Setup

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/githumps/grugthink.git
    cd grugthink
    ```

2.  **Create Virtual Environment:**
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt -r requirements-dev.txt
    ```

4.  **Configure Environment:**
    ```bash
    cp .env.example .env
    # Edit .env with your test Discord token and set GRUGBOT_VARIANT=dev
    ```

5.  **Run Bot:**
    ```bash
    # Single bot mode
    python grugthink.py
    
    # Multi-bot container mode  
    python grugthink.py multi-bot
    ```

## Testing

Ensure all tests pass before submitting changes:

```bash
# Run all tests
PYTHONPATH=. pytest

# Run specific test categories
PYTHONPATH=. pytest tests/test_bot.py          # Bot functionality
PYTHONPATH=. pytest tests/test_config.py       # Configuration handling
PYTHONPATH=. pytest tests/test_grug_db.py      # Database layer
PYTHONPATH=. pytest tests/test_integration.py  # End-to-end tests

# Quick test run
PYTHONPATH=. pytest -q
```

**Test Coverage**: All 44 tests should pass (100% success rate)

## Code Quality

Maintain code quality with linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix

# Format code
ruff format .

# Complete development check
ruff check . --fix && ruff format . && PYTHONPATH=. pytest
```

## Contributing Process

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Follow existing code patterns and personality engine architecture
- Add comprehensive tests for new functionality
- Update documentation if needed

### 3. Commit Changes
Use clear, descriptive commit messages:
```bash
git add .
git commit -m "feat: Add new personality template system"
git commit -m "fix: Resolve memory leak in response cache"
git commit -m "docs: Update deployment guide with Docker variants"
```

### 4. Test Everything
```bash
# Run full test suite
ruff check . --fix && ruff format . && PYTHONPATH=. pytest
```

### 5. Push Changes
```bash
git push origin feature/your-feature-name
```

### 6. Create Pull Request
- Provide clear description of changes and motivation
- Reference any related issues
- Include test results and any breaking changes

## Development Guidelines

### Multi-Bot Container System
- Test changes in multi-bot environment: `docker-compose -f examples/docker-compose/development.yml up -d`
- Use web dashboard at http://localhost:8080 for testing different bot configurations
- Ensure new features work with both single and multi-bot deployments
- Follow REST API patterns in `src/grugthink/api_server.py` for new endpoints
- Update bot templates in `src/grugthink/config_manager.py` for new personality options

### Personality System
- New personality templates should extend the existing PersonalityTemplate class
- Maintain personality isolation between Discord servers
- Follow evolution stage progression (Initial → Developing → Established → Evolved)

### Code Style
- Follow existing patterns for Discord command handling
- Use personality-aware responses throughout the bot
- Maintain backward compatibility when possible
- Add comprehensive docstrings for new methods

### Testing
- Write unit tests for individual components
- Add integration tests for Discord interactions
- Ensure all new features have test coverage
- Mock heavy dependencies appropriately

### Documentation
- Update relevant .md files for new features
- Include examples in personality documentation
- Update deployment guides for new configuration options

## Types of Contributions

### Features
- New personality templates
- Enhanced evolution mechanics
- Additional Discord commands
- Performance optimizations

### Bug Fixes
- Personality system bugs
- Discord interaction issues
- Memory leaks or performance problems
- Test failures

### Documentation
- API documentation improvements
- Deployment guide updates
- Example additions
- Troubleshooting guides

### Infrastructure
- CI/CD improvements
- Docker optimization
- Dependency updates
- Security enhancements

Thank you for contributing to GrugThink! 🚀