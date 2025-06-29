# Claude Development Guide for GrugThink

## Environment Setup

### Python Environment
This project uses Python 3.11 with a virtual environment:

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### Development Workflow
YOU MUST update CLAUDELOG.md at the end of each change Claude does, keep it detailed.
YOU MUST update CHANGELOG.md at the end of each change Claude does, keep it brief.
YOU MUST update CLAUDE.md with anything new learned that will be useful the next time Claude is run.
YOU MUST ensure any new code has proper tests that pass.
YOU MUST ensure the Github workflows are updated to reflect any changes made.
YOU MUST ensure the project will successfully work in Docker with ALL Dockerfiles (single bot and multi-bot).
YOU MUST ensure the project will build correctly when committed to Github and the automated Github Actions run to build and check.
YOU MUST ensure all documentation and markdown files are updated with new project details such as if new commands exist, etc.
YOU MUST test new features in both single-bot and multi-bot container environments.
**YOU MUST run `ruff check . --fix && ruff format .` and fix ALL linting errors before finishing any task to ensure GitHub Actions pass.**

### Multi-Bot Container Development
When developing new features:
- Test with multi-bot container: `docker-compose -f examples/docker-compose/development.yml up -d`
- Access web dashboard at http://localhost:8080 for testing
- Ensure changes work with both deployment methods
- Update API endpoints in `src/grugthink/api_server.py` if needed
- Add new bot templates to `src/grugthink/config_manager.py` if applicable

### Project Structure (Updated)
Following Python package best practices:
- **Source Code**: `src/grugthink/` - Organized Python package
- **Documentation**: `docs/` - All markdown documentation
- **Docker**: `docker/` - Organized by deployment type
- **Scripts**: `scripts/` - Setup and utility scripts
- **Examples**: `examples/` - Configuration templates and examples
- **Tests**: `tests/` - Comprehensive test suite

#### Linting and Formatting
```bash
# Check for linting issues
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Format code
ruff format .
```

#### Testing
```bash
# Run all tests
PYTHONPATH=. pytest

# Run specific test file
PYTHONPATH=. pytest tests/test_grug_db.py

# Run tests with verbose output
PYTHONPATH=. pytest -v
```

## Project Structure

### Core Files (Updated Structure)
- `src/grugthink/bot.py` - Main Discord bot implementation
- `src/grugthink/config.py` - Configuration management and validation
- `src/grugthink/grug_db.py` - Database and vector search functionality
- `src/grugthink/grug_structured_logger.py` - Logging utilities
- `src/grugthink/personality_engine.py` - Multi-personality system
- `src/grugthink/bot_manager.py` - Multi-bot orchestration
- `src/grugthink/api_server.py` - REST API and web dashboard
- `grugthink.py` - Main entry point

### Test Files
- `tests/test_bot.py` - Discord bot functionality tests
- `tests/test_config.py` - Configuration validation tests  
- `tests/test_grug_db.py` - Database functionality tests
- `tests/test_integration.py` - End-to-end Discord integration tests

### Configuration
- `pyproject.toml` - Ruff linting configuration
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies

## Dependencies

### Heavy Dependencies (for CI consideration)
- `faiss-cpu==1.7.4` - Vector similarity search
- `sentence-transformers>=2.2.2` - Text embeddings
- `torch` - PyTorch (dependency of sentence-transformers)

### Key Libraries
- `discord.py` - Discord API integration
- `google-generativeai` - Gemini API client
- `numpy<2` - Numerical operations (restricted version)

## Testing Notes

### Test Structure
- **Unit tests**: `test_grug_db.py`, `test_config.py`, `test_bot.py`
- **Integration tests**: `test_integration.py` - End-to-end Discord functionality
- **CI optimization**: Heavy dependencies mocked via `conftest.py` and `requirements-ci.txt`

### Test Environment Setup
- Global mocks in `conftest.py` replace FAISS, sentence-transformers, and torch
- `requirements-ci.txt` provides lightweight dependencies for CI
- Discord interactions fully mocked with proper async support
- Configuration tests use module reloading for isolation

### Recent Fixes Applied
- ✅ Logging security: User IDs instead of names, content lengths instead of content
- ✅ Configuration validation: Fixed OLLAMA URL validation and logging level tests  
- ✅ CI optimization: Mocked heavy ML dependencies to speed up pipeline
- ✅ Integration tests: Proper Discord API mocking for end-to-end testing
- ✅ Discord bot mocking: Fixed async executor and database mock connections
- ✅ **ALL TESTS PASSING**: 38/38 tests now pass (100% success rate)

### Running Tests
```bash
# Run all tests (with mocked dependencies)
PYTHONPATH=. pytest                            # 38/38 tests passing ✅

# Run specific test categories  
PYTHONPATH=. pytest tests/test_integration.py  # Integration tests (6/6 passing)
PYTHONPATH=. pytest tests/test_config.py       # Configuration tests (13/13 passing)
PYTHONPATH=. pytest tests/test_grug_db.py      # Database tests (7/7 passing)
PYTHONPATH=. pytest tests/test_bot.py          # Bot tests (12/12 passing)

# Run with brief output
PYTHONPATH=. pytest -q                         # Quick summary
```

### Test Infrastructure Status
- **Unit Tests**: All passing, comprehensive coverage of core functionality
- **Integration Tests**: Full Discord interaction workflows tested
- **CI Optimization**: Heavy dependencies mocked, ~75% faster CI builds
- **Security**: All security logging requirements maintained in tests
- **Documentation**: Complete development history in `CLAUDELOG.md`

## Development Commands

### Complete Test and Lint Cycle
```bash
# MANDATORY: Full development check (run in activated python3.11 venv)
# This MUST be run before finishing any task to ensure GitHub Actions pass
ruff check . --fix
ruff format .
PYTHONPATH=. pytest
```

### Git Workflow
```bash
# Check status before committing
git status
git diff

# Standard commit workflow (tests should pass first)
git add .
git commit -m "Your commit message"
```

## Security Considerations

- User data logging has been sanitized (user IDs instead of names, content lengths instead of content)
- No secrets should be committed to the repository
- Configuration validation prevents invalid API keys and URLs