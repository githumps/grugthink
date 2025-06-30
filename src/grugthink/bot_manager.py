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

from .grug_db import GrugDB
from .grug_structured_logger import get_logger
from .personality_engine import PersonalityEngine

log = get_logger(__name__)


@dataclass
class BotConfig:
    """Configuration for a single bot instance."""

    bot_id: str
    name: str
    discord_token: str
    gemini_api_key: Optional[str] = None
    ollama_urls: Optional[str] = None
    ollama_models: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    force_personality: Optional[str] = None
    load_embedder: bool = True
    log_level: str = "INFO"
    data_dir: str = "./data"
    trusted_user_ids: Optional[str] = None
    status: str = "stopped"  # stopped, starting, running, stopping, error
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class BotInstance:
    """Runtime instance of a Discord bot."""

    config: BotConfig
    client: Optional[commands.Bot] = None
    personality_engine: Optional[PersonalityEngine] = None
    db: Optional[GrugDB] = None
    thread: Optional[threading.Thread] = None
    task: Optional[asyncio.Task] = None
    last_heartbeat: float = None


class BotManager:
    """Manages multiple Discord bot instances."""

    def __init__(self, config_file: str = "bot_configs.json"):
        self.config_file = config_file
        self.bots: Dict[str, BotInstance] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()

        # Load existing configurations
        self._load_configs()

        log.info("BotManager initialized", extra={"config_file": config_file, "loaded_bots": len(self.bots)})

    def _load_configs(self):
        """Load bot configurations from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    configs = json.load(f)

                for config_data in configs:
                    config = BotConfig(**config_data)
                    instance = BotInstance(config=config)
                    self.bots[config.bot_id] = instance

                log.info("Loaded bot configurations", extra={"count": len(configs), "bot_ids": list(self.bots.keys())})

            except Exception as e:
                log.error("Failed to load bot configurations", extra={"error": str(e), "config_file": self.config_file})

    def _save_configs(self):
        """Save current bot configurations to file."""
        try:
            configs = []
            for bot_instance in self.bots.values():
                config_dict = asdict(bot_instance.config)
                configs.append(config_dict)

            with open(self.config_file, "w") as f:
                json.dump(configs, f, indent=2)

            log.info("Saved bot configurations", extra={"count": len(configs), "config_file": self.config_file})

        except Exception as e:
            log.error("Failed to save bot configurations", extra={"error": str(e), "config_file": self.config_file})

    def create_bot(self, name: str, discord_token: str, **kwargs) -> str:
        """Create a new bot configuration."""
        bot_id = str(uuid.uuid4())

        config = BotConfig(bot_id=bot_id, name=name, discord_token=discord_token, **kwargs)

        instance = BotInstance(config=config)

        with self._lock:
            self.bots[bot_id] = instance
            self._save_configs()

        log.info(
            "Created new bot", extra={"bot_id": bot_id, "name": name, "force_personality": config.force_personality}
        )

        return bot_id

    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot configuration."""
        if bot_id not in self.bots:
            return False

        # Stop the bot if running
        if self.bots[bot_id].config.status == "running":
            self.stop_bot(bot_id)

        with self._lock:
            del self.bots[bot_id]
            self._save_configs()

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

        status = {
            "bot_id": bot_id,
            "name": config.name,
            "status": config.status,
            "force_personality": config.force_personality,
            "created_at": config.created_at,
            "last_heartbeat": instance.last_heartbeat,
            "guild_count": 0,
            "user_count": 0,
        }

        # Add runtime info if bot is running
        if instance.client and instance.client.is_ready():
            status["guild_count"] = len(instance.client.guilds)
            status["user_count"] = sum(guild.member_count for guild in instance.client.guilds)
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

            # Initialize bot components
            data_dir = os.path.join(config.data_dir, bot_id)
            os.makedirs(data_dir, exist_ok=True)

            # Initialize personality engine with forced personality
            personality_engine = PersonalityEngine(db_path=os.path.join(data_dir, "personalities.db"))
            instance.personality_engine = personality_engine

            # Initialize database
            db = GrugDB(
                db_path=os.path.join(data_dir, "facts.db"), 
                server_id=bot_id, 
                load_embedder=config.load_embedder
            )
            instance.db = db

            # Create Discord client
            intents = discord.Intents.default()
            intents.message_content = True

            client = commands.Bot(command_prefix="/", intents=intents, loop=asyncio.get_running_loop())
            instance.client = client

            # Import and setup bot commands (we'll need to modularize the existing bot.py)
            await self._setup_bot_commands(instance, bot_env)

            # Start the bot in a separate task
            instance.task = asyncio.create_task(client.start(config.discord_token))

            # Wait for bot to be ready
            await client.wait_until_ready()

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
            except:
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
        env = {}

        # Core configuration
        env["DISCORD_TOKEN"] = config.discord_token
        env["GRUGBOT_DATA_DIR"] = os.path.join(config.data_dir, config.bot_id)
        env["LOG_LEVEL"] = config.log_level
        env["LOAD_EMBEDDER"] = str(config.load_embedder)

        # Optional API keys
        if config.gemini_api_key:
            env["GEMINI_API_KEY"] = config.gemini_api_key
        if config.ollama_urls:
            env["OLLAMA_URLS"] = config.ollama_urls
        if config.ollama_models:
            env["OLLAMA_MODELS"] = config.ollama_models
        if config.google_api_key:
            env["GOOGLE_API_KEY"] = config.google_api_key
        if config.google_cse_id:
            env["GOOGLE_CSE_ID"] = config.google_cse_id
        if config.trusted_user_ids:
            env["TRUSTED_USER_IDS"] = config.trusted_user_ids

        # Personality configuration
        if config.force_personality:
            env["FORCE_PERSONALITY"] = config.force_personality

        return env

    async def _setup_bot_commands(self, instance: BotInstance, env: Dict[str, str]):
        """Setup Discord commands for a bot instance."""
        # Import and add the GrugThinkBot cog
        from .bot import GrugThinkBot
        
        client = instance.client
        
        # Add the GrugThinkBot cog with proper instance
        await client.add_cog(GrugThinkBot(client, instance))

        @client.event
        async def on_ready():
            instance.config.status = "running" # Update status to running
            instance.last_heartbeat = time.time()
            log.info(
                "Bot connected to Discord",
                extra={
                    "bot_id": instance.config.bot_id,
                    "bot_name": client.user.name,
                    "guild_count": len(client.guilds),
                },
            )

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
