#!/usr/bin/env python3
"""
GrugThink Multi-Bot Container Entry Point

Main entry point for the multi-bot container system. Handles process isolation,
graceful shutdown, and coordination between the API server and bot instances.
"""

import argparse
import asyncio
import os
import signal
import sys
from typing import Any, Dict

from .api_server import APIServer
from .bot_manager import BotManager
from .config_manager import ConfigManager
from .grug_structured_logger import get_logger

log = get_logger(__name__)


class GrugThinkContainer:
    """Main container orchestrator for the multi-bot system."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.bot_manager = BotManager(config_manager=self.config_manager)
        self.api_server = APIServer(self.bot_manager, self.config_manager)

        self.running = False
        self.tasks = []

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        log.info("GrugThink Container initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        log.info("Received shutdown signal", extra={"signal": signum})
        asyncio.create_task(self.shutdown())

    async def start(self, start_bots: bool = True, api_port: int = 8080):
        """Start the container system."""
        try:
            self.running = True
            log.info("Starting GrugThink Container", extra={"start_bots": start_bots, "api_port": api_port})
            print(f"[DEBUG] GrugThink Container starting: start_bots={start_bots}, api_port={api_port}")

            # Start configuration change monitoring
            self.config_manager.add_change_callback(self._on_config_change)

            # Start bot monitoring task
            monitoring_task = asyncio.create_task(self.bot_manager.monitor_bots())
            self.tasks.append(monitoring_task)

            # Start all configured bots if requested
            print(f"[DEBUG] start_bots parameter is: {start_bots}")
            if start_bots:
                print("[DEBUG] About to call _start_configured_bots")
                log.info("About to call _start_configured_bots")
                await self._start_configured_bots()
            else:
                print("[DEBUG] Skipping bot auto-start (start_bots=False)")
                log.info("Skipping bot auto-start (start_bots=False)")

            # Start API server in background
            api_task = asyncio.create_task(self._run_api_server(api_port))
            self.tasks.append(api_task)

            log.info(
                "GrugThink Container started successfully", extra={"api_port": api_port, "auto_start_bots": start_bots}
            )

            # Keep running until shutdown
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            log.error("Error starting container", extra={"error": str(e)})
            await self.shutdown()
            raise

    async def _start_configured_bots(self):
        """Start all bots marked for auto-start in configuration."""
        log.info("_start_configured_bots called - checking for bots to auto-start")
        try:
            bots = self.bot_manager.list_bots()
            log.info(
                "Found bots in configuration",
                extra={"bot_count": len(bots), "bot_ids": [b.get("bot_id") for b in bots]},
            )
            auto_start_bots = []

            for bot in bots:
                # Check auto_start flag first, then fall back to status field
                auto_start_flag = self.config_manager.get_config(f"bot_configs.{bot['bot_id']}.auto_start")
                bot_status = self.config_manager.get_config(f"bot_configs.{bot['bot_id']}.status")

                log.info(
                    "Checking bot for auto-start",
                    extra={"bot_id": bot.get("bot_id"), "auto_start_flag": auto_start_flag, "bot_status": bot_status},
                )

                # Priority: explicit auto_start flag, then status "running"
                should_start = auto_start_flag is True or (auto_start_flag is None and bot_status == "running")

                if should_start:
                    auto_start_bots.append(bot)
                    log.info("Bot marked for auto-start", extra={"bot_id": bot.get("bot_id")})

            if auto_start_bots:
                log.info("Starting configured bots", extra={"count": len(auto_start_bots)})

                for bot in auto_start_bots:
                    try:
                        await self.bot_manager.start_bot(bot["bot_id"])
                        await asyncio.sleep(5)  # Stagger starts
                    except Exception as e:
                        log.error("Failed to start bot", extra={"bot_id": bot["bot_id"], "error": str(e)})
            else:
                log.info("No bots configured for auto-start")

        except Exception as e:
            log.error("Error starting configured bots", extra={"error": str(e)})

    async def _run_api_server(self, port: int):
        """Run the API server."""
        import uvicorn

        config = uvicorn.Config(self.api_server.app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    def _on_config_change(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any], old_env: Dict[str, str], new_env: Dict[str, str]
    ):
        """Handle configuration changes."""
        log.info("Configuration changed", extra={"config_keys": list(new_config.keys()), "env_vars": len(new_env)})

        # TODO: Handle specific configuration changes
        # - Restart bots if their config changed
        # - Update API keys
        # - Reload templates

    async def shutdown(self):
        """Gracefully shutdown the container."""
        if not self.running:
            return

        log.info("Shutting down GrugThink Container")
        self.running = False

        try:
            # Stop all bots
            await self.bot_manager.stop_all_bots()

            # Cancel all background tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Stop configuration manager
            self.config_manager.stop()

            log.info("GrugThink Container shutdown complete")

        except Exception as e:
            log.error("Error during shutdown", extra={"error": str(e)})


async def main():
    """Main entry point."""
    print("[DEBUG] main() function called in grugthink/main.py")
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv

        if os.path.exists(".env"):
            load_dotenv(".env")
            log.info("Loaded environment variables from .env file")
    except ImportError:
        log.warning("python-dotenv not installed, .env file not loaded")

    # Set multi-bot mode flag to skip single-bot config validation
    os.environ["GRUGTHINK_MULTIBOT_MODE"] = "true"

    parser = argparse.ArgumentParser(description="GrugThink Multi-Bot Container")
    parser.add_argument("--no-auto-start", action="store_true", help="Don't automatically start configured bots")
    parser.add_argument("--api-port", type=int, default=8080, help="Port for the management API (default: 8080)")
    parser.add_argument("--create-demo", action="store_true", help="Create demo bot configurations")

    args = parser.parse_args()

    # Create demo configurations if requested
    if args.create_demo:
        await create_demo_configuration()
        return

    # Start the container
    container = GrugThinkContainer()

    try:
        await container.start(start_bots=not args.no_auto_start, api_port=args.api_port)
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt")
    except Exception as e:
        log.error("Container error", extra={"error": str(e)})
        sys.exit(1)
    finally:
        await container.shutdown()


async def create_demo_configuration():
    """Create demonstration bot configurations."""
    log.info("Creating demo configuration")

    config_manager = ConfigManager()
    bot_manager = BotManager(config_manager=config_manager)

    try:
        # Check if we have any Discord tokens configured
        tokens = config_manager.get_discord_tokens()
        if not tokens:
            log.warning("No Discord tokens configured. Add tokens via the web interface or config file.")
            return

        available_token = config_manager.get_available_discord_token()
        if not available_token:
            log.warning("No available Discord tokens found")
            return

        demo_bots = [
            {"name": "Pure Grug Bot", "template": "pure_grug", "description": "Caveman personality only"},
            {"name": "Pure Big Rob Bot", "template": "pure_big_rob", "description": "norf FC lad personality only"},
            {"name": "Evolution Bot", "template": "evolution_bot", "description": "Adaptive personality that evolves"},
        ]

        created_bots = []
        for i, bot_config in enumerate(demo_bots):
            # Use the same token for demo - in practice you'd use different tokens
            bot_id = bot_manager.create_bot(
                name=bot_config["name"],
                discord_token=available_token,  # Same token for demo
                # In production, you'd want separate tokens per bot
            )
            created_bots.append((bot_id, bot_config["name"]))

            log.info(
                "Created demo bot",
                extra={"bot_id": bot_id, "name": bot_config["name"], "template": bot_config["template"]},
            )

        log.info(
            "Demo configuration created",
            extra={"bot_count": len(created_bots), "bots": [name for _, name in created_bots]},
        )

        print("\n🎉 Demo configuration created!")
        print(f"Created {len(created_bots)} demo bots:")
        for bot_id, name in created_bots:
            print(f"  - {name} (ID: {bot_id})")
        print("\nStart the container with: python main.py")
        print("Then visit http://localhost:8080 to manage your bots!")

    except Exception as e:
        log.error("Failed to create demo configuration", extra={"error": str(e)})
        print(f"❌ Failed to create demo configuration: {e}")


if __name__ == "__main__":
    # Set up proper event loop policy for Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
