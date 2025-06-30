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
YOU MUST update docs/CLAUDELOG.md at the end of each change Claude does, keep it detailed.
YOU MUST update docs/CHANGELOG.md at the end of each change Claude does, keep it brief.
YOU MUST update CLAUDE.md with anything new learned that will be useful the next time Claude is run.
YOU MUST ensure any new code has proper tests that pass.
YOU MUST ensure the project will successfully work in Docker.
YOU MUST ensure all documentation is updated with new project details.
**YOU MUST run `ruff check . --fix && ruff format .` and fix ALL linting errors before finishing any task to ensure GitHub Actions pass.**

## Project Structure

### Core Files
- `src/grugthink/bot.py` - Main Discord bot implementation
- `src/grugthink/config.py` - Configuration management and validation
- `src/grugthink/grug_db.py` - Database and vector search functionality
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

### Test Environment Setup
- Global mocks in `conftest.py` replace FAISS, sentence-transformers, and torch
- `requirements-ci.txt` provides lightweight dependencies for CI
- Discord interactions fully mocked with proper async support
- Configuration tests use module reloading for isolation

### Running Tests
```bash
# Run all tests
PYTHONPATH=. pytest

# Run with coverage
PYTHONPATH=. pytest --cov=src --cov-report=html

# Run specific test
PYTHONPATH=. pytest tests/test_bot.py -v
```

## Development Commands

### Complete Test and Lint Cycle
```bash
# MANDATORY: Full development check (run in activated python3.11 venv)
# This MUST be run before finishing any task to ensure GitHub Actions pass
ruff check . --fix
ruff format .
PYTHONPATH=. pytest
```

### Docker Development
```bash
# Build and run container
docker-compose up -d --build

# View logs
docker logs -f grugthink

# Access web dashboard
open http://localhost:8080
```

## Critical Learnings - Bot Isolation & Discord Limits

### Database Isolation for Multi-Instance Bots
**Problem**: Multiple Discord bot instances sharing the same database files cause memory contamination.

**Solution**: Create unique database paths based on Discord token hash:
```python
def _get_unique_db_path():
    if DISCORD_TOKEN:
        import hashlib
        token_hash = hashlib.sha256(DISCORD_TOKEN.encode()).hexdigest()[:12]
        return os.path.join(DATA_DIR, f"grug_lore_{token_hash}.db")
    else:
        return os.path.join(DATA_DIR, "grug_lore.db")
```

### Discord Embed Field Limits
**Critical**: Discord embed fields have a 1024 character limit that must be respected.

**Implementation**: Always count characters when building embed fields:
```python
MAX_FIELD_LENGTH = 950  # Leave margin for formatting
current_length = 0
for item in items:
    item_text = f"{i+1}. {item}"
    if current_length + len(item_text) + 1 > MAX_FIELD_LENGTH:
        break
    current_length += len(item_text) + 1
```

### Bot Deletion Bug Fix
**Critical**: The `delete_bot` function must be async and properly await `stop_bot()`.

**Solution**:
```python
async def delete_bot(self, bot_id: str) -> bool:
    if self.bots[bot_id].config.status == "running":
        await self.stop_bot(bot_id)  # Must await async function
```

### Testing Configuration Changes
When modifying `config.py`, ensure tests account for new behavior:
- Set `GRUGTHINK_MULTIBOT_MODE=true` to skip Discord token validation in tests
- Mock environment variables appropriately for default value testing
- Update assertions to match new configuration patterns