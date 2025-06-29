# Configuration Tests Documentation

This document provides detailed information about the configuration validation tests in `tests/test_config.py`.

## Overview

The configuration tests ensure robust validation of environment variables, proper default value assignment, and secure configuration loading. These tests prevent runtime errors due to misconfiguration and validate security requirements.

**Test Count: 13 tests ✅**

## Test Architecture

### Module Reloading Strategy

Configuration tests require careful module state management because configuration is loaded at import time. The test suite uses a helper function to ensure clean configuration state:

```python
def _reload_config():
    # Remove the config module from cache to force reload
    modules_to_remove = [
        "src.grugthink.config",
        "src.grugthink",
    ]
    for module_name in modules_to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]

    from src.grugthink import config
    return config
```

### Environment Setup Fixture

```python
@pytest.fixture(autouse=True)
def setup_config_env(monkeypatch):
    # Clear all relevant environment variables before each test
    env_vars = [
        "DISCORD_TOKEN", "GEMINI_API_KEY", "OLLAMA_URLS", "OLLAMA_MODELS",
        "GOOGLE_API_KEY", "GOOGLE_CSE_ID", "GRUGBOT_DATA_DIR", 
        "GRUGBOT_VARIANT", "TRUSTED_USER_IDS", "LOG_LEVEL",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    # Set a default minimal valid configuration
    monkeypatch.setenv("DISCORD_TOKEN", "fake_token")
    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")
```

## Test Categories

### 1. Required Configuration Tests

#### `test_missing_discord_token`
**Purpose**: Ensures DISCORD_TOKEN is required

**Setup**:
```python
monkeypatch.delenv("DISCORD_TOKEN")
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Missing DISCORD_TOKEN"):
    _reload_config()
```

**Security Implication**: Prevents bot from starting without Discord authentication

#### `test_missing_llm_config`
**Purpose**: Ensures at least one LLM provider is configured

**Setup**:
```python
monkeypatch.delenv("GEMINI_API_KEY")
monkeypatch.delenv("OLLAMA_URLS", raising=False)
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Missing LLM configuration"):
    _reload_config()
```

**Business Logic**: Bot requires AI capability to function

### 2. URL Validation Tests

#### `test_invalid_ollama_url`
**Purpose**: Validates Ollama server URL format

**Setup**:
```python
monkeypatch.delenv("GEMINI_API_KEY")  # Force Ollama usage
monkeypatch.setenv("OLLAMA_URLS", "not-a-valid-url")
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Invalid OLLAMA_URL"):
    _reload_config()
```

**Validation Logic**: Uses comprehensive regex to validate URL format:
```python
def is_valid_url(url):
    regex = re.compile(
        r"^(?:http)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP address
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)",
        re.IGNORECASE,
    )
    return re.match(regex, url) is not None
```

### 3. Model Validation Tests

#### `test_invalid_ollama_model`
**Purpose**: Validates Ollama model name format

**Setup**:
```python
monkeypatch.delenv("GEMINI_API_KEY")  # Force Ollama usage
monkeypatch.setenv("OLLAMA_URLS", "http://localhost:11434")
monkeypatch.setenv("OLLAMA_MODELS", "invalid/model name")  # Spaces not allowed
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Invalid model name"):
    _reload_config()
```

**Validation Pattern**: Model names must match `^[\w\-\.:]+$`

### 4. API Key Validation Tests

#### `test_invalid_gemini_api_key`
**Purpose**: Validates Gemini API key format

**Setup**:
```python
monkeypatch.setenv("GEMINI_API_KEY", "invalid key with spaces")
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Invalid GEMINI_API_KEY"):
    _reload_config()
```

#### `test_invalid_google_api_key`
**Purpose**: Validates Google Search API key format

**Setup**:
```python
monkeypatch.setenv("GOOGLE_API_KEY", "invalid key with spaces")
monkeypatch.setenv("GOOGLE_CSE_ID", "fake_cse_id")
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Invalid GOOGLE_API_KEY"):
    _reload_config()
```

#### `test_invalid_google_cse_id`
**Purpose**: Validates Google Custom Search Engine ID format

**Setup**:
```python
monkeypatch.setenv("GOOGLE_API_KEY", "fake_api_key")
monkeypatch.setenv("GOOGLE_CSE_ID", "invalid id with spaces")
```

**Expected Behavior**:
```python
with pytest.raises(ValueError, match="Invalid GOOGLE_CSE_ID"):
    _reload_config()
```

**Security Note**: All API keys must match pattern `^[\w\-]+$` (alphanumeric, dash, underscore only)

### 5. Valid Configuration Tests

#### `test_valid_config_gemini`
**Purpose**: Tests successful Gemini configuration

**Setup**:
```python
monkeypatch.delenv("OLLAMA_URLS", raising=False)  # Ensure only Gemini
```

**Expected Behavior**:
```python
config = _reload_config()
assert config.USE_GEMINI is True
assert config.CAN_SEARCH is False  # No Google keys by default
```

#### `test_valid_config_ollama`
**Purpose**: Tests successful Ollama configuration

**Setup**:
```python
monkeypatch.delenv("GEMINI_API_KEY", raising=False)
monkeypatch.setenv("OLLAMA_URLS", "http://localhost:11434,http://192.168.1.100:11434")
monkeypatch.setenv("OLLAMA_MODELS", "llama3.2:3b,grug:latest")
```

**Expected Behavior**:
```python
config = _reload_config()
assert config.USE_GEMINI is False
assert config.OLLAMA_URLS == ["http://localhost:11434", "http://192.168.1.100:11434"]
assert config.OLLAMA_MODELS == ["llama3.2:3b", "grug:latest"]
```

**Multi-Server Support**: Tests comma-separated URL and model lists

### 6. Feature Configuration Tests

#### `test_trusted_user_ids`
**Purpose**: Tests trusted user ID parsing

**Setup**:
```python
monkeypatch.setenv("TRUSTED_USER_IDS", "123,456,789")
```

**Expected Behavior**:
```python
config = _reload_config()
assert config.TRUSTED_USER_IDS == [123, 456, 789]
```

**Data Type**: Ensures string IDs converted to integers

### 7. Default Value Tests

#### `test_default_values`
**Purpose**: Tests all default configuration values

**Setup**:
```python
# Ensure all optional env vars are unset to get defaults
monkeypatch.delenv("GRUGBOT_VARIANT", raising=False)
monkeypatch.delenv("LOG_LEVEL", raising=False)
monkeypatch.delenv("TRUSTED_USER_IDS", raising=False)
monkeypatch.delenv("GEMINI_MODEL", raising=False)
monkeypatch.delenv("OLLAMA_MODELS", raising=False)
monkeypatch.delenv("GRUGBOT_DATA_DIR", raising=False)
```

**Expected Defaults**:
```python
config = _reload_config()
assert config.GRUGBOT_VARIANT == "prod"
assert config.LOG_LEVEL_STR == "INFO"
assert config.TRUSTED_USER_IDS == []
assert config.GEMINI_MODEL == "gemini-pro"
assert config.OLLAMA_MODELS == ["llama3.2:3b"]
assert config.DB_PATH.endswith("grug_lore.db")
```

**Database Path Validation**:
```python
# Check that DB_PATH is within the src/grugthink directory  
assert os.path.abspath(os.path.dirname(config.DB_PATH)) == os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../src/grugthink")
)
```

### 8. Case Sensitivity Tests

#### `test_log_level_case_insensitivity`
**Purpose**: Tests log level accepts various cases

**Setup**:
```python
monkeypatch.setenv("LOG_LEVEL", "debug")  # lowercase
```

**Expected Behavior**:
```python
config = _reload_config()
assert config.LOG_LEVEL_STR == "DEBUG"  # normalized to uppercase
```

### 9. Logging Integration Tests

#### `test_log_initial_settings`
**Purpose**: Tests configuration logging doesn't crash

**Setup**:
```python
# Set comprehensive configuration
monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key")
monkeypatch.setenv("GOOGLE_API_KEY", "fake_google_key")
monkeypatch.setenv("GOOGLE_CSE_ID", "fake_cse_id")
monkeypatch.setenv("TRUSTED_USER_IDS", "123")
```

**Expected Behavior**:
```python
config = _reload_config()
config.log_initial_settings()  # Should not raise exception
assert mock_log_info.call_count > 0  # Verify logging occurred
```

**Logging Content**: Tests that configuration summary is logged for debugging

## Configuration Validation Logic

### Environment Variable Processing

The configuration module processes environment variables with specific patterns:

```python
# String processing with defaults
GRUGBOT_VARIANT = os.getenv("GRUGBOT_VARIANT", "prod")
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()

# List processing (comma-separated)
OLLAMA_URLS = [url.strip() for url in os.getenv("OLLAMA_URLS", "").split(",") if url.strip()]
OLLAMA_MODELS = [model.strip() for model in os.getenv("OLLAMA_MODELS", "llama3.2:3b").split(",") if model.strip()]

# Integer list processing
TRUSTED_USER_IDS = [int(uid) for uid in os.getenv("TRUSTED_USER_IDS", "").split(",") if uid.strip()]

# Boolean processing
LOAD_EMBEDDER = os.getenv("LOAD_EMBEDDER", "True").lower() == "true"
```

### Validation Patterns

#### URL Validation
- Must start with `http://` or `https://`
- Supports domain names, localhost, and IP addresses
- Optional port numbers
- Validates against regex pattern

#### API Key Validation
- Alphanumeric characters only
- Hyphens and underscores allowed
- No spaces or special characters
- Pattern: `^[\w\-]+$`

#### Model Name Validation
- Alphanumeric characters, hyphens, dots, colons
- Pattern: `^[\w\-\.:]+$`
- Supports versioned models like `llama3.2:3b`

### Derived Configuration

The module calculates derived configuration values:

```python
# LLM provider selection
USE_GEMINI = bool(GEMINI_API_KEY)

# Capability detection
CAN_SEARCH = bool(GOOGLE_API_KEY and GOOGLE_CSE_ID)

# Validation rules
if not USE_GEMINI and not OLLAMA_URLS:
    raise ValueError("Missing LLM configuration")
```

## Common Testing Patterns

### Environment Variable Test Pattern
```python
def test_configuration_scenario(monkeypatch):
    # Clear conflicting variables
    monkeypatch.delenv("VARIABLE_NAME", raising=False)
    
    # Set test scenario
    monkeypatch.setenv("REQUIRED_VAR", "test_value")
    
    # Reload configuration
    config = _reload_config()
    
    # Assert expected behavior
    assert config.COMPUTED_VALUE == expected_result
```

### Validation Error Test Pattern
```python
def test_invalid_configuration(monkeypatch):
    # Set invalid value
    monkeypatch.setenv("VARIABLE_NAME", "invalid-value")
    
    # Expect validation error
    with pytest.raises(ValueError, match="Expected error message"):
        _reload_config()
```

### Default Value Test Pattern
```python
def test_default_values(monkeypatch):
    # Ensure variable is unset
    monkeypatch.delenv("OPTIONAL_VAR", raising=False)
    
    # Load configuration
    config = _reload_config()
    
    # Verify default is applied
    assert config.OPTIONAL_VAR == expected_default
```

## Security Considerations

### Input Validation
- All external input (environment variables) is validated
- Strict patterns prevent injection attacks
- URL validation prevents malicious redirects

### API Key Protection
- Keys validated for format but never logged
- No secrets in error messages or test output
- Secure storage patterns enforced

### Configuration Isolation
- Tests don't interfere with real configuration
- Temporary configuration state per test
- No persistent side effects

## Performance Considerations

- Configuration loaded once per test (via module reload)
- Fast validation using compiled regex patterns
- No external API calls during configuration
- Minimal memory footprint

## Debugging Tips

### Failed Validation Tests
```python
# Add debugging output to see actual vs expected
def test_debug_validation(monkeypatch):
    monkeypatch.setenv("VARIABLE", "test_value")
    config = _reload_config()
    print(f"Actual value: {config.VARIABLE}")  # Debug output
    assert config.VARIABLE == expected_value
```

### Environment Variable Conflicts
```python
# Check current environment state
import os
print("Current environment:", {k: v for k, v in os.environ.items() if 'GRUG' in k})
```

### Module Reload Issues
```python
# Verify module is properly cleared
import sys
print("Loaded modules:", [m for m in sys.modules if 'grugthink' in m])
```

---

*These configuration tests ensure the bot starts with valid, secure configuration and fails fast with clear error messages when misconfigured.*