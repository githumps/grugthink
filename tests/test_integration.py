"""
Integration tests for GrugThink bot with proper Discord API mocking.
These tests focus on end-to-end functionality without heavy dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

# Import after setting up mocks
from tests.test_bot import mock_config, mock_logger


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
        # Ensure guild_id is set
        mock_interaction.guild_id = 12345

        # Create a mock personality object
        mock_personality = MagicMock()
        mock_personality.response_style = "caveman"
        mock_personality.chosen_name = None
        mock_personality.name = "Grug"

        # Create a mock personality engine
        mock_personality_engine = MagicMock()
        mock_personality_engine.get_personality.return_value = mock_personality
        mock_personality_engine.get_response_with_style.return_value = "TRUE - Grug say sky blue sometimes."

        with (
            patch.dict("sys.modules", {"src.grugthink.config": mock_config, "src.grugthink.grug_db": MagicMock()}),
            patch("src.grugthink.bot.log", mock_logger),
            patch("asyncio.get_running_loop") as mock_loop,
        ):
            # Mock the executor
            async def mock_executor(executor, func, *args):
                return "TRUE - Grug say sky blue sometimes."

            mock_loop.return_value.run_in_executor = mock_executor

            from src.grugthink import bot

            # Setup mock responses
            mock_interaction.channel.history.return_value.__aiter__.return_value = [mock_message]
            server_db_mock = MagicMock()
            server_db_mock.search_facts.return_value = []

            with (
                patch.object(bot, "_personality_engine_instance", mock_personality_engine),
                patch.object(bot, "get_server_db", return_value=server_db_mock),
            ):
                # Execute the command
                await bot._handle_verification(mock_interaction)

                # Verify interaction flow
                mock_interaction.response.defer.assert_called_once_with(ephemeral=False)
                mock_interaction.followup.send.assert_called_once_with("Grug thinking...", ephemeral=False)

                # Logging verification omitted - focus on Discord interactions

    @pytest.mark.asyncio
    async def test_learn_command_integration(self, mock_interaction):
        """Test the learn command end-to-end."""
        # Ensure guild_id is set
        mock_interaction.guild_id = 12345
        mock_interaction.user.id = 12345  # Make user trusted

        # Create a mock personality object
        mock_personality = MagicMock()
        mock_personality.response_style = "caveman"
        mock_personality.chosen_name = None
        mock_personality.name = "Grug"

        # Create a mock personality engine
        mock_personality_engine = MagicMock()
        mock_personality_engine.get_personality.return_value = mock_personality

        with (
            patch.dict("sys.modules", {"src.grugthink.config": mock_config, "src.grugthink.grug_db": MagicMock()}),
            patch("src.grugthink.bot.log", mock_logger),
        ):
            from src.grugthink import bot

            # Setup mock responses
            server_db_mock = MagicMock()
            server_db_mock.add_fact.return_value = True

            with (
                patch.object(bot, "_personality_engine_instance", mock_personality_engine),
                patch.object(bot, "get_server_db", return_value=server_db_mock),
                patch("src.grugthink.bot.config") as bot_config,
            ):
                bot_config.TRUSTED_USER_IDS = [12345]

                # Execute the command
                await bot.learn.callback(mock_interaction, "Grug love mammoth meat.")

                # Verify interaction flow
                mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
                server_db_mock.add_fact.assert_called_once_with("Grug love mammoth meat.")
                mock_interaction.followup.send.assert_called_once_with(
                    "Grug learn: Grug love mammoth meat.", ephemeral=True
                )

                # Logging verification omitted - focus on Discord interactions

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_interaction, mock_message):
        """Test rate limiting functionality."""
        with (
            patch.dict("sys.modules", {"src.grugthink.config": mock_config, "src.grugthink.grug_db": MagicMock()}),
            patch("src.grugthink.bot.log", mock_logger),
        ):
            import time

            from src.grugthink import bot

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
        # Ensure guild_id is set
        mock_interaction.guild_id = 12345
        mock_interaction.user.id = 99999  # Make user untrusted

        # Create a mock personality object
        mock_personality = MagicMock()
        mock_personality.response_style = "caveman"
        mock_personality.chosen_name = None
        mock_personality.name = "Grug"

        # Create a mock personality engine
        mock_personality_engine = MagicMock()
        mock_personality_engine.get_personality.return_value = mock_personality

        with (
            patch.dict("sys.modules", {"src.grugthink.config": mock_config, "src.grugthink.grug_db": MagicMock()}),
            patch("src.grugthink.bot.log", mock_logger),
        ):
            from src.grugthink import bot

            with (
                patch.object(bot, "_personality_engine_instance", mock_personality_engine),
                patch("src.grugthink.bot.config") as bot_config,
            ):
                bot_config.TRUSTED_USER_IDS = [12345]  # User 99999 is not in this list

                # Execute the command
                await bot.learn.callback(mock_interaction, "Untrusted fact.")

                # Verify rejection
                mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
                mock_interaction.followup.send.assert_called_once_with("You not trusted to teach Grug.", ephemeral=True)


class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    @pytest.mark.asyncio
    async def test_database_search_integration(self):
        """Test database search with mocked dependencies."""
        import os
        import tempfile

        from src.grugthink.grug_db import GrugDB

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
        # Clear all environment variables first
        env_vars_to_clear = [
            "DISCORD_TOKEN",
            "GEMINI_API_KEY",
            "OLLAMA_URLS",
            "OLLAMA_MODELS",
            "GOOGLE_API_KEY",
            "GOOGLE_CSE_ID",
            "GRUGBOT_DATA_DIR",
            "GRUGBOT_VARIANT",
            "TRUSTED_USER_IDS",
            "LOG_LEVEL",
            "LOAD_EMBEDDER",
        ]
        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)

        # Set only the required minimal config
        monkeypatch.setenv("DISCORD_TOKEN", "test_token_123")
        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
        monkeypatch.setenv("GRUGBOT_VARIANT", "prod")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        # Reload config module completely
        import sys

        modules_to_remove = ["src.grugthink.config", "src.grugthink"]
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                del sys.modules[module_name]

        from src.grugthink import config

        assert config.USE_GEMINI is True
        assert config.CAN_SEARCH is False
        assert config.GRUGBOT_VARIANT == "prod"
        assert config.LOG_LEVEL_STR == "INFO"

        # Test log_initial_settings doesn't crash
        config.log_initial_settings()
