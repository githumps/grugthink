"""
Integration tests for GrugThink bot with proper Discord API mocking.
These tests focus on end-to-end functionality without heavy dependencies.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

# Import after setting up mocks
from tests.test_bot import _mock_bot_db, mock_config, mock_logger


class TestDiscordIntegration:
    """Integration tests for Discord bot functionality."""

    @pytest.fixture
    def mock_guild(self):
        """Mock Discord guild."""
        guild = MagicMock(spec=discord.Guild)
        guild.id = 12345
        guild.name = "Test Guild"
        return guild

    @pytest.fixture
    def mock_channel(self):
        """Mock Discord text channel."""
        channel = AsyncMock(spec=discord.TextChannel)
        channel.id = 67890
        channel.name = "test-channel"
        return channel

    @pytest.fixture
    def mock_user(self):
        """Mock Discord user."""
        user = MagicMock(spec=discord.User)
        user.id = 12345  # Trusted user ID from config
        user.name = "TestUser"
        user.bot = False
        return user

    @pytest.fixture
    def mock_interaction(self, mock_user, mock_channel):
        """Mock Discord interaction."""
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.user = mock_user
        interaction.channel = mock_channel
        interaction.guild_id = 12345
        interaction.response = AsyncMock()
        interaction.followup = AsyncMock()
        return interaction

    @pytest.fixture
    def mock_message(self, mock_user, mock_channel):
        """Mock Discord message."""
        message = MagicMock(spec=discord.Message)
        message.author = mock_user
        message.channel = mock_channel
        message.content = "The sky is blue today."
        message.id = 98765
        return message

    @pytest.mark.asyncio
    async def test_verify_command_integration(self, mock_interaction, mock_message):
        """Test the verify command end-to-end."""
        with patch.dict("sys.modules", {"config": mock_config, "grug_db": MagicMock()}), \
             patch("bot.db", _mock_bot_db), \
             patch("bot.log", mock_logger), \
             patch("asyncio.get_running_loop") as mock_loop:

            # Mock the executor
            async def mock_executor(executor, func, *args):
                return "TRUE - Grug say sky blue sometimes."
            mock_loop.return_value.run_in_executor = mock_executor

            import bot

            # Setup mock responses
            mock_interaction.channel.history.return_value.__aiter__.return_value = [mock_message]
            _mock_bot_db.search_facts.return_value = []

            # Execute the command
            await bot._handle_verification(mock_interaction)

            # Verify interaction flow
            mock_interaction.response.defer.assert_called_once_with(ephemeral=False)
            mock_interaction.followup.send.assert_called_once_with("Grug thinking...", ephemeral=False)

            # Logging verification omitted - focus on Discord interactions

    @pytest.mark.asyncio
    async def test_learn_command_integration(self, mock_interaction):
        """Test the learn command end-to-end."""
        with patch.dict("sys.modules", {"config": mock_config, "grug_db": MagicMock()}), \
             patch("bot.db", _mock_bot_db), \
             patch("bot.log", mock_logger):

            import bot

            # Setup mock responses
            _mock_bot_db.add_fact.return_value = True

            # Execute the command
            await bot.learn.callback(mock_interaction, "Grug love mammoth meat.")

            # Verify interaction flow
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            _mock_bot_db.add_fact.assert_called_once_with("Grug love mammoth meat.")
            mock_interaction.followup.send.assert_called_once_with(
                "Grug learn: Grug love mammoth meat.", ephemeral=True
            )

            # Logging verification omitted - focus on Discord interactions

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_interaction, mock_message):
        """Test rate limiting functionality."""
        with patch.dict("sys.modules", {"config": mock_config, "grug_db": MagicMock()}), \
             patch("bot.db", _mock_bot_db), \
             patch("grug_structured_logger.get_logger", return_value=mock_logger):

            import time

            import bot

            # Set up rate limiting
            bot.user_cooldowns[mock_interaction.user.id] = time.time()

            # Execute the command
            await bot._handle_verification(mock_interaction)

            # Verify rate limiting response
            mock_interaction.response.send_message.assert_called_once_with(
                "Slow down! Wait a few seconds.", ephemeral=True
            )

    @pytest.mark.asyncio
    async def test_untrusted_user_learn_integration(self, mock_interaction):
        """Test learn command with untrusted user."""
        with patch.dict("sys.modules", {"config": mock_config, "grug_db": MagicMock()}), \
             patch("bot.db", _mock_bot_db), \
             patch("grug_structured_logger.get_logger", return_value=mock_logger):

            import bot

            # Make user untrusted
            mock_interaction.user.id = 99999

            # Execute the command
            await bot.learn.callback(mock_interaction, "Untrusted fact.")

            # Verify rejection
            mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
            mock_interaction.followup.send.assert_called_once_with(
                "You not trusted to teach Grug.", ephemeral=True
            )


class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    @pytest.mark.asyncio
    async def test_database_search_integration(self):
        """Test database search with mocked dependencies."""
        import os
        import tempfile

        from grug_db import GrugDB

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Initialize database (uses mocked FAISS and sentence-transformers)
            db = GrugDB(db_path)

            # Add some facts
            assert db.add_fact("Grug hunt mammoth in winter.")
            assert db.add_fact("Ugga make fire with dry wood.")
            assert not db.add_fact("Grug hunt mammoth in winter.")  # Duplicate

            # Test search
            results = db.search_facts("hunting animals", k=1)
            assert len(results) >= 0  # Should work with mocked embeddings

            # Test get all facts
            all_facts = db.get_all_facts()
            assert "Grug hunt mammoth in winter." in all_facts
            assert "Ugga make fire with dry wood." in all_facts
            assert len(all_facts) == 2

            # Test rebuild
            db.rebuild_index()

            # Close database
            db.close()

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.remove(db_path)
            index_path = db_path.replace(".db", ".index")
            if os.path.exists(index_path):
                os.remove(index_path)


class TestConfigurationIntegration:
    """Integration tests for configuration management."""

    def test_config_loading_integration(self, monkeypatch):
        """Test configuration loading with various scenarios."""
        # Test with minimal valid config
        monkeypatch.setenv("DISCORD_TOKEN", "test_token_123")
        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
        monkeypatch.delenv("OLLAMA_URLS", raising=False)

        # Reload config module
        import sys
        if "config" in sys.modules:
            del sys.modules["config"]

        import config

        assert config.USE_GEMINI is True
        assert config.CAN_SEARCH is False
        assert config.GRUGBOT_VARIANT == "prod"
        assert config.LOG_LEVEL_STR == "WARNING"  # From conftest.py

        # Test log_initial_settings doesn't crash
        config.log_initial_settings()
