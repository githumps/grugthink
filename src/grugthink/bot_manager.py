#!/usr/bin/env python3
"""
GrugThink Multi-Bot Manager

Orchestrates multiple Discord bot instances with different personalities
and configurations within a single container.
"""

import asyncio
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands

from .grug_db import GrugServerManager
from .grug_structured_logger import get_logger
from .personality_engine import PersonalityEngine

log = get_logger(__name__)


@dataclass
class BotConfig:
    """Configuration for a single bot instance."""

    bot_id: str
    name: str
    discord_token_id: str  # Reference to token ID in grugthink_config.yaml
    template_id: str = "evolution_bot"  # Template to use for this bot
    personality: Optional[str] = None  # Personality ID from personality configs
    force_personality: Optional[str] = None  # Deprecated, use personality instead
    load_embedder: bool = True
    log_level: str = "DEBUG"
    data_dir: str = None  # Will be set from environment in __post_init__
    trusted_user_ids: Optional[str] = None
    status: str = "stopped"  # stopped, starting, running, stopping, error
    auto_start: Optional[bool] = None  # Whether to auto-start this bot on container startup
    created_at: float = None

    # Override settings (optional)
    override_gemini_key: Optional[str] = None
    override_google_api_key: Optional[str] = None
    override_google_cse_id: Optional[str] = None
    override_ollama_urls: Optional[str] = None
    override_ollama_models: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.data_dir is None:
            # Use environment variable for data directory, fallback to ./data
            self.data_dir = os.getenv("GRUGBOT_DATA_DIR", "./data")


@dataclass
class BotInstance:
    """Runtime instance of a Discord bot."""

    config: BotConfig
    client: Optional[commands.Bot] = None
    personality_engine: Optional[PersonalityEngine] = None
    server_manager: Optional[GrugServerManager] = None
    thread: Optional[threading.Thread] = None
    task: Optional[asyncio.Task] = None
    last_heartbeat: float = None
    forced_personality: Optional[str] = None


class BotManager:
    """Manages multiple Discord bot instances."""

    def __init__(self, config_file: str = "bot_configs.json", config_manager=None):
        self.config_file = config_file  # Keep for backward compatibility during migration
        self.config_manager = config_manager
        self.bots: Dict[str, BotInstance] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
        self._migrated = False

        # Load existing configurations
        self._load_configs()

        log.info("BotManager initialized", extra={"config_file": config_file, "loaded_bots": len(self.bots)})

    def _load_configs(self):
        """Load bot configurations from ConfigManager or migrate from JSON."""
        if self.config_manager:
            # Try to load from YAML config first
            bot_configs = self.config_manager.list_bot_configs()

            if bot_configs:
                # Load from YAML
                for bot_id, config_data in bot_configs.items():
                    try:
                        config = BotConfig(**config_data)
                        instance = BotInstance(config=config)
                        self.bots[config.bot_id] = instance
                    except Exception as e:
                        log.error("Failed to load bot config", extra={"bot_id": bot_id, "error": str(e)})

                log.info("Loaded bot configurations from YAML", extra={"count": len(bot_configs)})

            elif os.path.exists(self.config_file):
                # Migrate from JSON
                log.info("No bot configs in YAML, migrating from JSON", extra={"json_file": self.config_file})
                try:
                    migration_map = self.config_manager.migrate_from_json(self.config_file)

                    # Load the migrated configs
                    bot_configs = self.config_manager.list_bot_configs()
                    for bot_id, config_data in bot_configs.items():
                        config = BotConfig(**config_data)
                        instance = BotInstance(config=config)
                        self.bots[config.bot_id] = instance

                    self._migrated = True
                    log.info(
                        "Migration completed",
                        extra={"migrated_count": len(migration_map), "json_file": self.config_file},
                    )

                    # Optionally back up the old JSON file
                    backup_file = self.config_file + ".migrated.backup"
                    os.rename(self.config_file, backup_file)
                    log.info("Backed up old JSON config", extra={"backup_file": backup_file})

                except Exception as e:
                    log.error("Migration failed, falling back to JSON loading", extra={"error": str(e)})
                    self._load_configs_from_json()
        else:
            # No ConfigManager, load from JSON (legacy mode)
            self._load_configs_from_json()

    def _load_configs_from_json(self):
        """Legacy method to load from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    configs = json.load(f)

                for config_data in configs:
                    # Convert old format to new format with dummy token_id
                    if "discord_token" in config_data and "discord_token_id" not in config_data:
                        config_data["discord_token_id"] = "legacy"
                        config_data["template_id"] = "evolution_bot"
                        # Keep the actual token for legacy compatibility
                        config_data["_legacy_discord_token"] = config_data.pop("discord_token")

                    config = BotConfig(**{k: v for k, v in config_data.items() if not k.startswith("_")})
                    instance = BotInstance(config=config)
                    # Store legacy token if present
                    if "_legacy_discord_token" in config_data:
                        instance._legacy_discord_token = config_data["_legacy_discord_token"]
                    self.bots[config.bot_id] = instance

                log.info(
                    "Loaded bot configurations from JSON",
                    extra={"count": len(configs), "bot_ids": list(self.bots.keys())},
                )

            except Exception as e:
                log.error("Failed to load bot configurations", extra={"error": str(e), "config_file": self.config_file})

    def _save_configs(self):
        """Save current bot configurations to ConfigManager."""
        if not self.config_manager:
            log.warning("No ConfigManager available, cannot save bot configs")
            return

        try:
            for bot_instance in self.bots.values():
                config_dict = asdict(bot_instance.config)
                # Remove None values to keep config clean
                config_dict = {k: v for k, v in config_dict.items() if v is not None}

                # Update or add the bot config
                existing_config = self.config_manager.get_bot_config(bot_instance.config.bot_id)
                if existing_config:
                    self.config_manager.update_bot_config(bot_instance.config.bot_id, config_dict)
                else:
                    self.config_manager.add_bot_config(config_dict)

            log.info("Saved bot configurations to YAML", extra={"count": len(self.bots)})

        except Exception as e:
            log.error("Failed to save bot configurations", extra={"error": str(e)})

    def create_bot(self, name: str, discord_token_id: str, **kwargs) -> str:
        """Create a new bot configuration."""
        bot_id = str(uuid.uuid4())

        config = BotConfig(bot_id=bot_id, name=name, discord_token_id=discord_token_id, **kwargs)

        instance = BotInstance(config=config)

        with self._lock:
            self.bots[bot_id] = instance
            self._save_configs()

        log.info(
            "Created new bot", extra={"bot_id": bot_id, "name": name, "force_personality": config.force_personality}
        )

        return bot_id

    async def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot configuration."""
        if bot_id not in self.bots:
            return False

        # Stop the bot if running - must await this!
        if self.bots[bot_id].config.status == "running":
            await self.stop_bot(bot_id)

        with self._lock:
            del self.bots[bot_id]
            # Remove from persistent configuration
            if self.config_manager:
                self.config_manager.remove_bot_config(bot_id)
            else:
                log.warning("No ConfigManager available, bot config may persist in file")

        log.info("Deleted bot", extra={"bot_id": bot_id})
        return True

    def update_bot_config(self, bot_id: str, **kwargs) -> bool:
        """Update bot configuration."""
        if bot_id not in self.bots:
            return False

        instance = self.bots[bot_id]
        config = instance.config

        # Update configuration
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        with self._lock:
            self._save_configs()

        log.info("Updated bot configuration", extra={"bot_id": bot_id, "updated_fields": list(kwargs.keys())})

        return True

    def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a bot."""
        if bot_id not in self.bots:
            return None

        instance = self.bots[bot_id]
        config = instance.config

        # Get the actual personality being used (prefer new 'personality' field)
        actual_personality = getattr(config, "personality", None) or config.force_personality

        # If no explicit personality, try to get it from the template
        if not actual_personality and self.config_manager:
            template_id = getattr(config, "template_id", "evolution_bot")
            template = self.config_manager.get_template(template_id)
            if template:
                template_dict = template if isinstance(template, dict) else template.__dict__
                actual_personality = template_dict.get("personality")

        status = {
            "bot_id": bot_id,
            "name": config.name,
            "status": config.status,
            "personality": actual_personality,  # Current personality
            "force_personality": config.force_personality,  # Deprecated but kept for compatibility
            "template_id": getattr(config, "template_id", "evolution_bot"),
            "discord_token_id": config.discord_token_id,
            "created_at": config.created_at,
            "last_heartbeat": instance.last_heartbeat,
            "guild_count": 0,
            "guild_ids": [],
            "log_level": getattr(config, "log_level", "INFO"),
            "load_embedder": getattr(config, "load_embedder", True),
        }

        # Add runtime info if bot is running
        if instance.client and instance.client.is_ready():
            status["guild_ids"] = [g.id for g in instance.client.guilds]
            status["guild_count"] = len(status["guild_ids"])
            status["latency"] = round(instance.client.latency * 1000, 2)  # ms

        return status

    def list_bots(self) -> List[Dict[str, Any]]:
        """List all bot configurations and their status."""
        return [self.get_bot_status(bot_id) for bot_id in self.bots.keys()]

    async def start_bot(self, bot_id: str) -> bool:
        """Start a specific bot instance."""
        if bot_id not in self.bots:
            log.error("Bot not found", extra={"bot_id": bot_id})
            return False

        instance = self.bots[bot_id]
        config = instance.config

        if config.status == "running":
            log.warning("Bot already running", extra={"bot_id": bot_id})
            return True

        try:
            config.status = "starting"
            log.info("Starting bot", extra={"bot_id": bot_id, "name": config.name})

            # Create bot-specific environment and set it immediately
            bot_env = self._create_bot_environment(config)

            # Set environment variables before importing any bot modules
            original_env = {}
            for key, value in bot_env.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = value

            # Log initial settings for this bot instance
            log.info("Bot starting up", extra={"bot_id": bot_id, "name": config.name})
            if bot_env.get("GEMINI_API_KEY"):
                log.info("Using Gemini for generation", extra={"model": bot_env.get("GEMINI_MODEL", "gemma-3-27b-it")})
            elif bot_env.get("OLLAMA_URLS"):
                log.info(
                    "Using Ollama for generation",
                    extra={"urls": bot_env.get("OLLAMA_URLS"), "models": bot_env.get("OLLAMA_MODELS")},
                )
            if bot_env.get("GOOGLE_API_KEY"):
                log.info("Google Search is enabled.")
            else:
                log.warning("Google Search is disabled. Bot cannot learn new things from the internet.")
            if bot_env.get("TRUSTED_USER_IDS"):
                log.info("Trusted users configured", extra={"users": bot_env.get("TRUSTED_USER_IDS")})
            else:
                log.warning("No trusted users configured. /learn command will be disabled for all.")

            # Initialize bot components
            data_dir = os.path.join(config.data_dir, bot_id)
            os.makedirs(data_dir, exist_ok=True)

            # Initialize personality engine with configured personality (prefer new 'personality' field)
            bot_personality = getattr(config, "personality", None) or config.force_personality
            personality_engine = PersonalityEngine(
                db_path=os.path.join(data_dir, "personalities.db"), forced_personality=bot_personality
            )
            instance.personality_engine = personality_engine

            # Store the personality for this bot instance
            instance.forced_personality = bot_personality

            # Initialize server manager for this bot (each bot gets its own data directory)
            server_manager = GrugServerManager(
                base_db_path=os.path.join(data_dir, "facts.db"), model_name="all-MiniLM-L6-v2"
            )
            instance.server_manager = server_manager

            # Create Discord client
            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.members = True

            client = commands.Bot(command_prefix="/", intents=intents, loop=asyncio.get_running_loop())
            instance.client = client

            # Import and setup bot commands (we'll need to modularize the existing bot.py)
            await self._setup_bot_commands(instance, bot_env)

            # Start the bot in a separate task - get token from environment
            discord_token = bot_env.get("DISCORD_TOKEN")
            if not discord_token:
                raise ValueError(f"No Discord token available for bot {config.bot_id}")
            instance.task = asyncio.create_task(client.start(discord_token))

            # Give it a moment to start
            await asyncio.sleep(2)

            # Check if the task failed
            if instance.task.done():
                exception = instance.task.exception()
                if exception:
                    raise exception

            config.status = "running"
            instance.last_heartbeat = time.time()

            log.info(
                "Bot started successfully",
                extra={"bot_id": bot_id, "name": config.name, "guild_count": len(client.guilds)},
            )

            return True

        except Exception as e:
            config.status = "error"
            log.error("Failed to start bot", extra={"bot_id": bot_id, "error": str(e)})

            # Restore original environment variables on error
            try:
                for key, value in original_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            except Exception:
                pass  # Don't let env cleanup crash the error handling

            return False

    async def stop_bot(self, bot_id: str) -> bool:
        """Stop a specific bot instance."""
        if bot_id not in self.bots:
            return False

        instance = self.bots[bot_id]
        config = instance.config

        if config.status != "running":
            return True

        try:
            config.status = "stopping"
            log.info("Stopping bot", extra={"bot_id": bot_id, "name": config.name})

            # Close Discord client
            if instance.client:
                await instance.client.close()

            # Cancel the task
            if instance.task:
                instance.task.cancel()
                try:
                    await instance.task
                except asyncio.CancelledError:
                    pass

            # Clean up resources
            instance.client = None
            instance.task = None
            instance.last_heartbeat = None

            config.status = "stopped"

            log.info("Bot stopped successfully", extra={"bot_id": bot_id})
            return True

        except Exception as e:
            config.status = "error"
            log.error("Failed to stop bot", extra={"bot_id": bot_id, "error": str(e)})
            return False

    async def restart_bot(self, bot_id: str) -> bool:
        """Restart a specific bot instance."""
        if await self.stop_bot(bot_id):
            await asyncio.sleep(2)  # Brief pause
            return await self.start_bot(bot_id)
        return False

    def _create_bot_environment(self, config: BotConfig) -> Dict[str, str]:
        """Create environment variables for a specific bot."""
        discord_token = None

        # Try to get Discord token from ConfigManager first
        if self.config_manager and config.discord_token_id != "legacy":
            discord_token = self.config_manager.get_discord_token_by_id(config.discord_token_id)
            if not discord_token:
                raise ValueError(f"Discord token with ID '{config.discord_token_id}' not found")

        # If ConfigManager available, use it for environment creation
        if self.config_manager and discord_token:
            template_id = getattr(config, "template_id", "evolution_bot")

            env = self.config_manager.create_bot_env(
                template_id=template_id,
                discord_token=discord_token,
                LOG_LEVEL=config.log_level,
                GRUGBOT_DATA_DIR=os.path.join(config.data_dir, config.bot_id),
                LOAD_EMBEDDER=str(config.load_embedder),
            )

            # Apply bot-specific overrides
            if config.override_gemini_key:
                env["GEMINI_API_KEY"] = config.override_gemini_key
            if config.override_google_api_key:
                env["GOOGLE_API_KEY"] = config.override_google_api_key
            if config.override_google_cse_id:
                env["GOOGLE_CSE_ID"] = config.override_google_cse_id
            if config.override_ollama_urls:
                env["OLLAMA_URLS"] = config.override_ollama_urls
            if config.override_ollama_models:
                env["OLLAMA_MODELS"] = config.override_ollama_models
        else:
            # Legacy mode: create environment manually
            env = {}

            # For legacy tokens, check if bot instance has stored token
            bot_instance = self.bots.get(config.bot_id)
            if bot_instance and hasattr(bot_instance, "_legacy_discord_token"):
                discord_token = bot_instance._legacy_discord_token
            elif not discord_token:
                raise ValueError(f"No Discord token available for bot {config.bot_id}")

            env["DISCORD_TOKEN"] = discord_token
            env["GRUGBOT_DATA_DIR"] = os.path.join(config.data_dir, config.bot_id)
            env["LOG_LEVEL"] = config.log_level
            env["LOAD_EMBEDDER"] = str(config.load_embedder)

            # Legacy API key handling
            if config.override_gemini_key:
                env["GEMINI_API_KEY"] = config.override_gemini_key
            if config.override_google_api_key:
                env["GOOGLE_API_KEY"] = config.override_google_api_key
            if config.override_google_cse_id:
                env["GOOGLE_CSE_ID"] = config.override_google_cse_id
            if config.override_ollama_urls:
                env["OLLAMA_URLS"] = config.override_ollama_urls
            if config.override_ollama_models:
                env["OLLAMA_MODELS"] = config.override_ollama_models

        # Common configuration
        if config.trusted_user_ids:
            env["TRUSTED_USER_IDS"] = config.trusted_user_ids
        elif os.getenv("TRUSTED_USER_IDS"):
            env["TRUSTED_USER_IDS"] = os.getenv("TRUSTED_USER_IDS")

        # Personality configuration (prefer new 'personality' field over deprecated 'force_personality')
        personality = getattr(config, "personality", None) or config.force_personality
        if personality:
            env["FORCE_PERSONALITY"] = personality

        return env

    async def _setup_bot_commands(self, instance: BotInstance, env: Dict[str, str]):
        """Setup Discord commands for a bot instance."""
        client = instance.client

        @client.event
        async def on_ready():
            try:
                # Import and add the GrugThinkBot cog after client is ready
                from .bot import GrugThinkBot

                # Add the GrugThinkBot cog with proper instance
                await client.add_cog(GrugThinkBot(client, instance))

                # Sync commands after adding cog
                await client.tree.sync()

                instance.config.status = "running"  # Update status to running
                instance.last_heartbeat = time.time()
                log.info(
                    "Bot connected to Discord and commands synced",
                    extra={
                        "bot_id": instance.config.bot_id,
                        "bot_name": client.user.name,
                        "guild_count": len(client.guilds),
                    },
                )
            except Exception as e:
                log.error("Error in bot on_ready setup", extra={"bot_id": instance.config.bot_id, "error": str(e)})
                instance.config.status = "error"

    async def start_all_bots(self):
        """Start all configured bots."""
        self.running = True

        for bot_id in self.bots.keys():
            await self.start_bot(bot_id)
            await asyncio.sleep(5)  # Stagger starts to avoid rate limits

    async def stop_all_bots(self):
        """Stop all running bots."""
        self.running = False

        tasks = []
        for bot_id in self.bots.keys():
            if self.bots[bot_id].config.status == "running":
                tasks.append(self.stop_bot(bot_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def monitor_bots(self):
        """Monitor bot health and update heartbeats."""
        while self.running:
            try:
                for bot_id, instance in self.bots.items():
                    if instance.config.status == "running" and instance.client:
                        if instance.client.is_ready():
                            instance.last_heartbeat = time.time()
                        else:
                            # Bot disconnected, attempt restart
                            log.warning("Bot disconnected, attempting restart", extra={"bot_id": bot_id})
                            await self.restart_bot(bot_id)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                log.error("Error in bot monitoring", extra={"error": str(e)})
                await asyncio.sleep(60)  # Wait longer on error
