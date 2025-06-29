# Bot Tests Documentation

This document provides detailed information about the Discord bot functionality tests in `tests/test_bot.py`.

## Overview

The bot tests cover all Discord-related functionality including slash commands, auto-verification, personality integration, and user interaction patterns. These tests ensure the bot behaves correctly in various Discord scenarios.

**Test Count: 18 tests ✅**

## Test Structure

### Fixtures and Setup

#### Mock Configuration
```python
mock_config = MagicMock()
mock_config.DISCORD_TOKEN = "fake_token"
mock_config.TRUSTED_USER_IDS = [12345]
mock_config.GRUGBOT_VARIANT = "prod"
mock_config.USE_GEMINI = True
mock_config.CAN_SEARCH = False
```

#### Environment Setup
```python
os.environ["DISCORD_TOKEN"] = "fake_token"
os.environ["GEMINI_API_KEY"] = "fake_gemini_key"
os.environ["GRUGBOT_VARIANT"] = "prod"
os.environ["FORCE_PERSONALITY"] = "grug"  # Ensures consistent personality
```

#### Discord Mocks
```python
@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 12345  # Default trusted user
    interaction.channel = AsyncMock(spec=discord.TextChannel)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.guild_id = 12345
    return interaction
```

### Personality Engine Mocking Strategy

The key insight for successful bot testing is proper personality engine mocking. The bot uses a cached global instance:

```python
# CORRECT: Direct global variable patching
mock_personality = MagicMock()
mock_personality.name = "Grug"
mock_personality.chosen_name = None
mock_personality.response_style = "caveman"

mock_personality_engine = MagicMock()
mock_personality_engine.get_personality.return_value = mock_personality

with patch.object(bot, '_personality_engine_instance', mock_personality_engine):
    # Test code here
```

## Test Categories

### 1. Verification Command Tests

#### `test_handle_verification_no_message`
**Purpose**: Tests behavior when no user message is available to verify

**Setup**:
- Empty channel history
- Standard interaction mock

**Expected Behavior**:
```python
mock_interaction.response.send_message.assert_called_once_with(
    "No user message to verify.", ephemeral=True
)
```

#### `test_handle_verification_success`
**Purpose**: Tests successful verification workflow

**Setup**:
- Mock message in channel history
- Mock executor returning positive result
- Personality engine returning "Grug" responses

**Flow**:
1. Bot defers response (shows "thinking" state)
2. Bot sends "Grug thinking..." message
3. Bot processes verification in executor
4. Bot edits message with verification result

**Expected Behavior**:
```python
mock_interaction.response.defer.assert_called_once_with(ephemeral=False)
mock_interaction.followup.send.assert_called_once_with("Grug thinking...", ephemeral=False)
mock_interaction.followup.send.return_value.edit.assert_called_once_with(
    content="Verification: TRUE - Grug say this true."
)
```

#### `test_handle_verification_model_failure`
**Purpose**: Tests handling when AI model fails to respond

**Setup**:
- Mock executor returning None (failure)
- Error message from personality engine

**Expected Behavior**:
- Bot shows error message in Grug's style
- Error is logged appropriately

#### `test_handle_verification_rate_limited`
**Purpose**: Tests rate limiting prevents spam

**Setup**:
- User cooldown set to current time
- Standard interaction

**Expected Behavior**:
```python
mock_interaction.response.send_message.assert_called_once_with(
    "Slow down! Wait a few seconds.", ephemeral=True
)
```

### 2. Learn Command Tests

#### `test_learn_trusted_user_success`
**Purpose**: Tests successful fact learning by trusted user

**Setup**:
- User ID 12345 (trusted)
- Valid fact length (>= 5 characters)
- Mock database returning success

**Expected Behavior**:
```python
server_db_mock.add_fact.assert_called_once_with("Grug like big rock.")
mock_interaction.followup.send.assert_called_once_with(
    "Grug learn: Grug like big rock.", ephemeral=True
)
```

#### `test_learn_non_trusted_user`
**Purpose**: Tests rejection of non-trusted users

**Setup**:
- User ID 99999 (not in trusted list)
- Any fact content

**Expected Behavior**:
```python
mock_interaction.followup.send.assert_called_once_with(
    "You not trusted to teach Grug.", ephemeral=True
)
```

#### `test_learn_short_fact_trusted_user`
**Purpose**: Tests handling of facts that meet minimum length

**Setup**:
- Trusted user
- Fact with exactly 5 characters ("Hello")
- Proper config mocking for trust check

**Key Details**:
- Uses 5-character fact to test minimum length boundary
- Requires proper config.TRUSTED_USER_IDS mocking
- Tests the complete learn workflow

#### `test_learn_duplicate_fact`
**Purpose**: Tests handling when fact already exists

**Setup**:
- Trusted user
- Mock database returning False (duplicate)

**Expected Behavior**:
```python
mock_interaction.followup.send.assert_called_once_with(
    "Grug already know that.", ephemeral=True
)
```

### 3. Knowledge Display Tests

#### `test_what_know_no_facts`
**Purpose**: Tests display when no facts are stored

**Setup**:
- Empty facts list from database
- Standard personality setup

**Expected Behavior**:
```python
mock_interaction.followup.send.assert_called_once_with(
    "Grug know nothing in this cave.", ephemeral=True
)
```

#### `test_what_know_with_facts`
**Purpose**: Tests facts display formatting

**Setup**:
- Mock facts list: ["Grug hunt mammoth.", "Ugga make good fire."]
- Personality returning "Grug" responses

**Expected Behavior**:
- Embed with title "Grug's Memories (Test Guild)"
- Numbered fact list in embed field
- Ephemeral response

**Embed Structure**:
```python
assert embed.title == "Grug's Memories (Test Guild)"
assert embed.description == f"Grug knows {len(facts)} things in this cave:"
assert embed.fields[0].name == "Facts"
assert embed.fields[0].value == "1. Grug hunt mammoth.\n2. Ugga make good fire."
```

### 4. Help Command Tests

#### `test_help_command`
**Purpose**: Tests help command embed generation

**Expected Behavior**:
- Embed with "Grug Help" title
- Description mentioning available commands
- Fields for each command (/verify, /learn, /what-know, /help)
- Ephemeral response

### 5. Auto-Verification Tests

#### `test_is_bot_mentioned`
**Purpose**: Tests name detection logic for auto-verification

**Test Cases**:
```python
# Direct name mentions
assert bot.is_bot_mentioned("Hey Grug, is the sky blue?", "Grug") is True
assert bot.is_bot_mentioned("grug tell me about the moon", "Grug") is True

# Case insensitive
assert bot.is_bot_mentioned("GRUG what do you think?", "Grug") is True

# Evolved names
assert bot.is_bot_mentioned("Hey Thog, is water wet?", "Thog") is True

# Common nicknames
assert bot.is_bot_mentioned("bot, is this true?", "Grug") is True
assert bot.is_bot_mentioned("grugthink help me", "Grug") is True

# @mentions
assert bot.is_bot_mentioned("Hey <@12345> check this", "Grug") is True

# Non-mentions
assert bot.is_bot_mentioned("This has nothing to do with bots", "Grug") is False
```

#### `test_auto_verification_message_handling`
**Purpose**: Tests on_message event handler for auto-verification

**Setup**:
- Non-bot message mentioning "Grug"
- Mock client and personality engine
- Mock verification handler

**Expected Behavior**:
- `handle_auto_verification` called once

#### `test_auto_verification_rate_limited`
**Purpose**: Tests rate limiting in auto-verification

**Setup**:
- User with active cooldown
- Mock message channel

**Expected Behavior**:
- Rate limit message sent
- Message auto-deleted after 5 seconds

#### `test_auto_verification_short_content`
**Purpose**: Tests handling of short messages in auto-verification

**Setup**:
- Short message content ("Grug hi")
- No rate limiting

**Expected Behavior**:
- Acknowledgment message instead of verification
- "Grug hear you call!" response

#### `test_markov_bot_interaction`
**Purpose**: Tests special handling for Markov bots

**Setup**:
- Bot with "MarkovChain_Bot" name
- Regular bot for comparison
- Mock client and handlers

**Expected Behavior**:
- Markov bot messages processed
- Regular bot messages ignored

#### `test_markov_bot_special_responses`
**Purpose**: Tests special responses for Markov bots

**Setup**:
- Markov bot with short content
- Mock channel send

**Expected Behavior**:
- Special acknowledgment mentioning "robot friend"

### 6. Utility Tests

#### `test_clean_statement`
**Purpose**: Tests message cleaning utility

**Test Cases**:
```python
assert bot.clean_statement("hello <@123> world") == "hello world"
assert bot.clean_statement("check this: http://example.com") == "check this:"
assert bot.clean_statement("in <#12345> channel") == "in channel"
assert bot.clean_statement("  extra   spaces  ") == "extra spaces"
```

## Key Testing Patterns

### Async Testing Pattern
```python
@pytest.mark.asyncio
async def test_async_command():
    # Setup
    mock_interaction = create_mock_interaction()
    
    # Execute
    await bot.command_function(mock_interaction)
    
    # Verify
    mock_interaction.response.defer.assert_called_once()
```

### Personality Engine Testing Pattern
```python
def setup_grug_personality():
    mock_personality = MagicMock()
    mock_personality.name = "Grug"
    mock_personality.chosen_name = None
    mock_personality.response_style = "caveman"
    
    mock_engine = MagicMock()
    mock_engine.get_personality.return_value = mock_personality
    return mock_engine

# In test:
with patch.object(bot, '_personality_engine_instance', setup_grug_personality()):
    # Test code
```

### Trust System Testing Pattern
```python
# For trusted user tests
with patch("src.grugthink.bot.config") as mock_config:
    mock_config.TRUSTED_USER_IDS = [12345]
    # Test trusted user functionality

# For untrusted user tests  
mock_interaction.user.id = 99999  # Not in trusted list
# Test rejection behavior
```

## Mock Object Specifications

### Discord Interaction Mock
```python
mock_interaction = AsyncMock(spec=discord.Interaction)
mock_interaction.user = MagicMock(spec=discord.User)
mock_interaction.user.id = 12345
mock_interaction.user.name = "TestUser"
mock_interaction.channel = AsyncMock(spec=discord.TextChannel)
mock_interaction.response = AsyncMock()
mock_interaction.followup = AsyncMock()
mock_interaction.guild_id = 12345
mock_interaction.guild = MagicMock(spec=discord.Guild)
mock_interaction.guild.name = "Test Guild"
```

### Database Mock
```python
server_db_mock = MagicMock()
server_db_mock.add_fact.return_value = True  # or False for duplicates
server_db_mock.get_all_facts.return_value = ["fact1", "fact2"]
server_db_mock.search_facts.return_value = ["relevant fact"]
```

## Common Issues and Solutions

### Issue: Wrong Personality Responses
**Problem**: Tests expect "Grug" but get "Big Rob" or other personalities
**Solution**: Use direct global variable patching:
```python
with patch.object(bot, '_personality_engine_instance', mock_personality_engine):
```

### Issue: Config Not Mocked Properly
**Problem**: Trust checking fails because config.TRUSTED_USER_IDS not mocked
**Solution**: Patch the config module within the test context:
```python
with patch("src.grugthink.bot.config") as mock_config:
    mock_config.TRUSTED_USER_IDS = [12345]
```

### Issue: Async Mock Assertions Fail
**Problem**: AsyncMock methods not asserting correctly
**Solution**: Ensure proper spec and await patterns:
```python
mock_interaction = AsyncMock(spec=discord.Interaction)
await bot.function(mock_interaction)
mock_interaction.response.defer.assert_called_once()
```

### Issue: Environment Variable Conflicts
**Problem**: Previous test environment affects current test
**Solution**: Use proper environment setup in test module:
```python
os.environ["FORCE_PERSONALITY"] = "grug"  # At module level
```

## Performance Considerations

- All heavy dependencies (ML models, Discord client) are mocked
- Tests run in ~0.6 seconds total
- No external API calls or network dependencies
- Temporary database files automatically cleaned up
- Mock objects reset between tests for isolation

---

*These bot tests ensure the Discord integration works correctly across all supported commands and interaction patterns while maintaining proper security and user experience.*