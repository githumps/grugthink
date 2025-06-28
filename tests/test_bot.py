import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

# Add the project root to the path to import bot and config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock the config module before bot is imported
mock_config = MagicMock()
mock_config.DISCORD_TOKEN = "fake_token"
mock_config.TRUSTED_USER_IDS = [12345]
mock_config.GRUGBOT_VARIANT = "prod"
mock_config.USE_GEMINI = True
mock_config.CAN_SEARCH = False
mock_config.GOOGLE_API_KEY = None
mock_config.GOOGLE_CSE_ID = None
mock_config.GEMINI_API_KEY = "fake_gemini_key"
mock_config.GEMINI_MODEL = "gemini-pro"
mock_config.OLLAMA_URLS = []
mock_config.OLLAMA_MODELS = []
mock_config.DB_PATH = "test_grug_lore.db"
mock_config.LOG_LEVEL_STR = "INFO"  # Corrected: Use LOG_LEVEL_STR
mock_config.LOAD_EMBEDDER = True

# Global mocks for bot.server_manager and bot.query_model
_mock_bot_db = MagicMock()
_mock_server_manager = MagicMock()
_mock_server_manager.get_server_db.return_value = _mock_bot_db
_mock_query_model = MagicMock()  # Synchronous mock since it's called in executor

# Mock the logger
mock_logger = MagicMock()

with (
    patch.dict(
        "sys.modules",
        {
            "config": mock_config,
            "grug_db": MagicMock(),  # Mock the entire grug_db module
        },
    ),
    patch("bot.server_manager", _mock_server_manager),
    patch("bot.query_model", _mock_query_model),
    patch("grug_structured_logger.get_logger", return_value=mock_logger),
):
    import bot


# Mock Discord Interaction and related objects
@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 12345  # Default to a trusted user
    interaction.user.name = "TestUser"
    interaction.channel = AsyncMock(spec=discord.TextChannel)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.guild_id = 12345  # Add guild_id for server identification
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.name = "Test Guild"
    interaction.guild.id = 12345
    # Add a mock message attribute to the interaction
    interaction.message = AsyncMock(spec=discord.Message)
    interaction.message.content = "Initial message content"
    return interaction


@pytest.fixture
def mock_message():
    message = MagicMock(spec=discord.Message)
    message.author = MagicMock(spec=discord.User)
    message.author.bot = False
    message.content = "This is a test statement."
    return message


@pytest.fixture(autouse=True)
def reset_bot_state():
    # Reset rate limits and cache for each test
    bot.user_cooldowns = {}
    bot.response_cache.cache.clear()

    # Reset mocks for each test to ensure clean state
    _mock_bot_db.reset_mock()
    _mock_server_manager.reset_mock()
    _mock_server_manager.get_server_db.return_value = _mock_bot_db  # Re-establish connection after reset
    _mock_query_model.reset_mock()
    mock_logger.reset_mock()

    # Set default return values after reset
    _mock_query_model.return_value = None  # Default to None unless test overrides
    yield


# Test cases for _handle_verification
@pytest.mark.asyncio
async def test_handle_verification_no_message(mock_interaction):
    mock_interaction.channel.history.return_value.__aiter__.return_value = []
    await bot._handle_verification(mock_interaction)
    mock_interaction.response.send_message.assert_called_once_with("No user message to verify.", ephemeral=True)


@pytest.mark.asyncio
async def test_handle_verification_success(mock_interaction, mock_message):
    mock_interaction.channel.history.return_value.__aiter__.return_value = [mock_message]
    _mock_bot_db.search_facts.return_value = []  # No internal knowledge

    # Mock the executor to return our mock result directly
    async def mock_executor(executor, func, *args):
        return "TRUE - Grug say this true."

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = mock_executor
        await bot._handle_verification(mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=False)
    mock_interaction.followup.send.assert_called_once_with("Grug thinking...", ephemeral=False)
    mock_interaction.followup.send.return_value.edit.assert_called_once_with(
        content="Verification: TRUE - Grug say this true."
    )
    # Logging verification omitted - focus on Discord interactions


@pytest.mark.asyncio
async def test_handle_verification_model_failure(mock_interaction, mock_message):
    mock_interaction.channel.history.return_value.__aiter__.return_value = [mock_message]
    _mock_bot_db.search_facts.return_value = []  # No internal knowledge

    # Mock the executor to return None (failure)
    async def mock_executor(executor, func, *args):
        return None

    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.run_in_executor = mock_executor
        await bot._handle_verification(mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=False)
    mock_interaction.followup.send.assert_called_once_with("Grug thinking...", ephemeral=False)
    # Check that edit was called with one of the error messages
    args, kwargs = mock_interaction.followup.send.return_value.edit.call_args
    assert kwargs["content"] in [
        "Grug no hear truth. Try again.",
        "Grug brain hurt. No can answer.",
        "Truth hide from Grug. Wait little.",
        "Sky spirit silent. Ask later.",
        "Grug smash rock, find no answer.",
    ]


@pytest.mark.asyncio
async def test_handle_verification_rate_limited(mock_interaction, mock_message):
    bot.user_cooldowns[mock_interaction.user.id] = time.time()  # Set cooldown
    await bot._handle_verification(mock_interaction)
    mock_interaction.response.send_message.assert_called_once_with("Slow down! Wait a few seconds.", ephemeral=True)


# Test cases for learn command
@pytest.mark.asyncio
async def test_learn_trusted_user_success(mock_interaction):
    mock_interaction.user.id = 12345  # Trusted user

    # Mock the get_server_db function directly to return our mock database
    server_db_mock = MagicMock()
    server_db_mock.add_fact.return_value = True

    with patch.object(bot, "get_server_db", return_value=server_db_mock) as mock_get_db:
        await bot.learn.callback(mock_interaction, "Grug like big rock.")

        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_get_db.assert_called_once_with(mock_interaction)
        server_db_mock.add_fact.assert_called_once_with("Grug like big rock.")
        mock_interaction.followup.send.assert_called_once_with("Grug learn: Grug like big rock.", ephemeral=True)
        # Logging verification omitted - focus on Discord interactions


@pytest.mark.asyncio
async def test_learn_non_trusted_user(mock_interaction):
    mock_interaction.user.id = 99999  # Non-trusted user
    await bot.learn.callback(mock_interaction, "Grug like big rock.")
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with("You not trusted to teach Grug.", ephemeral=True)


@pytest.mark.asyncio
async def test_learn_fact_too_short(mock_interaction):
    mock_interaction.user.id = 12345  # Trusted user
    await bot.learn.callback(mock_interaction, "Hi.")
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once_with("Fact too short to be useful.", ephemeral=True)


@pytest.mark.asyncio
async def test_learn_duplicate_fact(mock_interaction):
    mock_interaction.user.id = 12345  # Trusted user

    # Mock the get_server_db function directly to return our mock database
    server_db_mock = MagicMock()
    server_db_mock.add_fact.return_value = False  # Simulate duplicate

    with patch.object(bot, "get_server_db", return_value=server_db_mock) as mock_get_db:
        await bot.learn.callback(mock_interaction, "Grug like big rock.")
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_get_db.assert_called_once_with(mock_interaction)
        server_db_mock.add_fact.assert_called_once_with("Grug like big rock.")
        mock_interaction.followup.send.assert_called_once_with("Grug already know that.", ephemeral=True)


# Test cases for what-grug-know command
@pytest.mark.asyncio
async def test_what_grug_know_no_facts(mock_interaction):
    # Mock the get_server_db function directly to return our mock database
    server_db_mock = MagicMock()
    server_db_mock.get_all_facts.return_value = []

    with patch.object(bot, "get_server_db", return_value=server_db_mock) as mock_get_db:
        await bot.what_grug_know.callback(mock_interaction)
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_get_db.assert_called_once_with(mock_interaction)

        # When no facts, it should send "Grug know nothing in this cave."
        mock_interaction.followup.send.assert_called_once_with("Grug know nothing in this cave.", ephemeral=True)


@pytest.mark.asyncio
async def test_what_grug_know_with_facts(mock_interaction):
    facts = ["Grug hunt mammoth.", "Ugga make good fire."]

    # Mock the get_server_db function directly to return our mock database
    server_db_mock = MagicMock()
    server_db_mock.get_all_facts.return_value = facts

    with patch.object(bot, "get_server_db", return_value=server_db_mock) as mock_get_db:
        await bot.what_grug_know.callback(mock_interaction)
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
        mock_get_db.assert_called_once_with(mock_interaction)

        # Check embed content
        args, kwargs = mock_interaction.followup.send.call_args
        embed = kwargs["embed"]
        assert embed.title == "Grug's Memories (Test Guild)"  # Include server name
        assert embed.description == f"Grug knows {len(facts)} things in this cave:"
        assert embed.fields[0].name == "Facts"
        assert embed.fields[0].value == "1. Grug hunt mammoth.\n2. Ugga make good fire."
        assert kwargs["ephemeral"] is True


# Test cases for grug-help command
@pytest.mark.asyncio
async def test_grug_help(mock_interaction):
    await bot.grug_help.callback(mock_interaction)
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    embed = kwargs["embed"]
    assert embed.title == "Grug Help"
    assert "Here are the things Grug can do:" in embed.description
    assert any(f.name == "/verify" for f in embed.fields)
    assert any(f.name == "/learn" for f in embed.fields)
    assert any(f.name == "/what-grug-know" for f in embed.fields)
    assert any(f.name == "/grug-help" for f in embed.fields)
    assert kwargs["ephemeral"] is True


# Test clean_statement
def test_clean_statement():
    assert bot.clean_statement("hello <@123> world") == "hello world"
    assert bot.clean_statement("check this: http://example.com") == "check this:"
    assert bot.clean_statement("in <#12345> channel") == "in channel"
    assert bot.clean_statement("  extra   spaces  ") == "extra spaces"
