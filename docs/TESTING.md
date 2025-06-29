# GrugThink Testing Documentation

This document provides comprehensive information about the test suite for the GrugThink Discord bot project.

## Overview

The GrugThink test suite consists of 44 total tests across 4 test categories:
- **43 passing tests** ✅
- **1 skipped test** (conditional database rollback test) ⏭️
- **0 failing tests** 🎯

## Test Categories

### 1. Bot Tests (`tests/test_bot.py`) - 18 tests ✅

Tests the core Discord bot functionality including commands, auto-verification, and personality system integration.

#### Command Tests
- **Verification Commands**: Tests the `/verify` command that analyzes message truthfulness
- **Learn Commands**: Tests the `/learn` command for trusted users to add facts  
- **Knowledge Commands**: Tests the `/what-know` command to display stored facts
- **Help Commands**: Tests the `/help` command to show available commands

#### Auto-Verification Tests
- **Message Detection**: Tests automatic verification when bot is mentioned
- **Rate Limiting**: Tests cooldown mechanisms to prevent spam
- **Bot Interaction**: Tests special handling for Markov bots vs regular bots
- **Content Processing**: Tests handling of short vs long message content

#### Key Features Tested
- Personality engine integration with different response styles
- Trust system for user permissions
- Database interaction for fact storage and retrieval
- Discord interaction patterns (defer, followup, ephemeral messages)
- Error handling and graceful degradation

### 2. Configuration Tests (`tests/test_config.py`) - 13 tests ✅

Tests configuration validation, environment variable handling, and default value assignment.

#### Validation Tests
- **Required Fields**: Tests that missing required environment variables raise appropriate errors
- **URL Validation**: Tests OLLAMA_URL format validation
- **API Key Validation**: Tests format validation for Gemini and Google API keys
- **Model Name Validation**: Tests Ollama model name format requirements

#### Configuration Scenarios
- **Gemini Configuration**: Tests valid configuration with Gemini API
- **Ollama Configuration**: Tests valid configuration with Ollama models
- **Mixed Configurations**: Tests various combinations of API providers
- **Default Values**: Tests that appropriate defaults are applied

#### Features Tested
- Environment variable parsing and validation
- Configuration module reloading for test isolation
- Logging configuration and initial settings
- Search capability detection based on available APIs

### 3. Database Tests (`tests/test_grug_db.py`) - 7 tests ✅ + 1 skipped

Tests the core database functionality for fact storage, retrieval, and vector search capabilities.

#### Core Database Operations
- **Fact Addition**: Tests adding new facts and duplicate detection
- **Fact Retrieval**: Tests getting all stored facts
- **Search Functionality**: Tests semantic search with vector embeddings
- **Index Management**: Tests rebuilding search indexes

#### Advanced Features
- **Transaction Rollback**: Tests database rollback on indexing failures (skipped when semantic search unavailable)
- **Database Lifecycle**: Tests opening, closing, and cleanup operations
- **Error Handling**: Tests graceful handling of invalid database paths

#### Key Testing Patterns
- **Conditional Testing**: Some tests skip when semantic search dependencies unavailable
- **Temporary Databases**: Each test uses isolated temporary database files
- **Mock Integration**: Heavy ML dependencies (FAISS, sentence-transformers) are mocked for CI performance

### 4. Integration Tests (`tests/test_integration.py`) - 6 tests ✅

Tests end-to-end functionality and component integration across the entire system.

#### Discord Integration Tests
- **Verify Command Integration**: Tests complete verification workflow from Discord interaction to response
- **Learn Command Integration**: Tests complete learning workflow with trusted user validation
- **Untrusted User Handling**: Tests rejection of learn commands from non-trusted users
- **Rate Limiting Integration**: Tests rate limiting in realistic scenarios

#### Database Integration Tests
- **Full Database Workflow**: Tests database operations with mocked dependencies
- **Search Integration**: Tests search functionality with deterministic mock embeddings

#### Configuration Integration Tests
- **Complete Config Loading**: Tests configuration loading with realistic environment scenarios
- **Module Reloading**: Tests clean configuration state across test runs

## Test Architecture

### Mocking Strategy

The test suite uses a sophisticated mocking strategy to ensure fast, reliable tests:

#### Personality Engine Mocking
```python
# Direct global variable patching for consistent personality responses
mock_personality_engine = MagicMock()
mock_personality = MagicMock()
mock_personality.name = "Grug"
mock_personality.response_style = "caveman"
mock_personality_engine.get_personality.return_value = mock_personality

with patch.object(bot, '_personality_engine_instance', mock_personality_engine):
    # Test code here
```

#### Discord API Mocking
```python
# Comprehensive Discord object mocking
mock_interaction = AsyncMock(spec=discord.Interaction)
mock_interaction.user.id = 12345
mock_interaction.guild_id = 12345
mock_interaction.response = AsyncMock()
mock_interaction.followup = AsyncMock()
```

#### Database Mocking
```python
# Heavy ML dependencies mocked for performance
if "faiss" not in sys.modules:
    fake_faiss = types.ModuleType("faiss")
    # Custom FAISS implementation for testing
    sys.modules["faiss"] = fake_faiss
```

### Test Isolation

#### Environment Variable Management
- Each test clears relevant environment variables before execution
- Configuration modules are reloaded to ensure clean state
- Monkeypatch fixture ensures proper cleanup

#### Database Isolation
- Temporary database files created for each test
- Automatic cleanup prevents test interference
- Mock embeddings provide deterministic search results

#### Module State Management
- Global variables reset between tests
- Import caches cleared when needed
- Mock objects reset to prevent state leakage

## Running Tests

### Basic Test Execution
```bash
# Run all tests
PYTHONPATH=. pytest

# Run specific test category
PYTHONPATH=. pytest tests/test_bot.py
PYTHONPATH=. pytest tests/test_config.py
PYTHONPATH=. pytest tests/test_grug_db.py
PYTHONPATH=. pytest tests/test_integration.py

# Run with verbose output
PYTHONPATH=. pytest -v

# Run with brief output
PYTHONPATH=. pytest -q
```

### Development Workflow
```bash
# Complete development check
ruff check . --fix    # Fix linting issues
ruff format .         # Format code
PYTHONPATH=. pytest   # Run all tests
```

### CI/CD Considerations
- Heavy ML dependencies (FAISS, sentence-transformers, torch) are mocked
- Tests run ~75% faster in CI due to mocking strategy
- All tests pass reliably in GitHub Actions environment
- No external service dependencies required

## Test Environment Setup

### Required Environment Variables
```bash
# Minimal required for tests
export DISCORD_TOKEN="fake_token"
export GEMINI_API_KEY="fake_gemini_key"
export FORCE_PERSONALITY="grug"  # Ensures consistent personality in tests
```

### Optional Testing Configuration
```bash
# For testing different scenarios
export GRUGBOT_VARIANT="prod"
export LOG_LEVEL="INFO"
export LOAD_EMBEDDER="True"
```

## Common Testing Patterns

### Async Test Pattern
```python
@pytest.mark.asyncio
async def test_async_function():
    # Setup mocks
    mock_interaction = AsyncMock(spec=discord.Interaction)
    
    # Execute async function
    await bot.some_command(mock_interaction)
    
    # Verify interactions
    mock_interaction.response.defer.assert_called_once()
```

### Configuration Test Pattern
```python
def test_config_scenario(monkeypatch):
    # Clear environment
    monkeypatch.delenv("SOME_VAR", raising=False)
    
    # Set specific config
    monkeypatch.setenv("DISCORD_TOKEN", "test_token")
    
    # Reload config module
    config = _reload_config()
    
    # Assert expected behavior
    assert config.SOME_VALUE == expected_value
```

### Database Test Pattern
```python
def test_database_operation(db_instance):
    # Use fixture-provided temporary database
    result = db_instance.add_fact("Test fact")
    
    # Verify operation
    assert result is True
    assert "Test fact" in db_instance.get_all_facts()
```

## Troubleshooting Tests

### Common Issues

#### Environment Variable Conflicts
- **Problem**: Tests fail due to existing environment variables
- **Solution**: Use monkeypatch to clear variables before setting test values

#### Module Import Caching
- **Problem**: Configuration changes not reflected in tests
- **Solution**: Explicitly delete modules from sys.modules before reimporting

#### Async Test Failures
- **Problem**: AsyncMock not behaving as expected
- **Solution**: Ensure proper spec parameters and await patterns

#### Personality Engine Mocking
- **Problem**: Tests getting wrong personality responses
- **Solution**: Use direct global variable patching instead of function mocking

### Debug Techniques

#### Verbose Test Output
```bash
PYTHONPATH=. pytest -v -s  # Show print statements and verbose output
```

#### Specific Test Debugging
```bash
PYTHONPATH=. pytest tests/test_bot.py::test_specific_function -v --tb=long
```

#### Environment Inspection
```python
# Add to test for debugging
import os
print("Environment:", dict(os.environ))
```

## Test Maintenance

### Adding New Tests

1. **Choose Appropriate Test File**: Add to existing category or create new file
2. **Follow Naming Conventions**: Use descriptive test names with `test_` prefix
3. **Use Existing Patterns**: Follow established mocking and assertion patterns
4. **Ensure Isolation**: Clean up any state changes and use appropriate fixtures

### Updating Tests for New Features

1. **Update Mocks**: Add new methods/attributes to mock objects as needed
2. **Add New Test Cases**: Cover new functionality with comprehensive tests
3. **Update Integration Tests**: Ensure end-to-end workflows still work
4. **Review Mock Strategy**: Consider if new dependencies need mocking

### Performance Considerations

- **Mock Heavy Dependencies**: Keep ML libraries mocked for fast CI runs
- **Use Temporary Resources**: Avoid creating persistent test artifacts
- **Parallel Test Safety**: Ensure tests can run in parallel without conflicts
- **Resource Cleanup**: Always clean up temporary files and database connections

## Security Testing

### Input Validation Tests
- Configuration validation prevents malicious input
- API key format validation ensures security
- URL validation prevents injection attacks

### Permission Testing
- Trust system properly restricts privileged operations
- User ID validation prevents unauthorized access
- Ephemeral message handling protects sensitive information

### Data Protection Tests
- User data logging sanitized (IDs instead of names)
- Content length logging instead of full content
- No secrets logged or committed to repository

---

*This documentation is automatically maintained alongside the test suite. When adding new tests or modifying existing ones, please update this documentation accordingly.*