#!/usr/bin/env python3
"""
GrugThink Management API Server

RESTful API for managing multiple Discord bot instances, configurations,
and monitoring. Provides endpoints for the web dashboard frontend.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from .bot_manager import BotManager
from fastapi import BackgroundTasks, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config_manager import ConfigManager
from .grug_structured_logger import get_logger

log = get_logger(__name__)


# Pydantic models for API requests/responses
class CreateBotRequest(BaseModel):
    name: str
    template_id: str
    discord_token: str
    gemini_api_key: Optional[str] = None
    ollama_urls: Optional[str] = None
    ollama_models: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    trusted_user_ids: Optional[str] = None
    custom_env: Dict[str, str] = {}


class UpdateBotRequest(BaseModel):
    name: Optional[str] = None
    discord_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_urls: Optional[str] = None
    ollama_models: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cse_id: Optional[str] = None
    force_personality: Optional[str] = None
    load_embedder: Optional[bool] = None
    trusted_user_ids: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    key: str
    value: Any


class AddDiscordTokenRequest(BaseModel):
    name: str
    token: str


class SetApiKeyRequest(BaseModel):
    service: str
    key_name: str
    value: str


class BotActionResponse(BaseModel):
    success: bool
    message: str
    bot_id: Optional[str] = None


class SystemStatsResponse(BaseModel):
    total_bots: int
    running_bots: int
    total_guilds: int
    total_users: int
    uptime: float
    memory_usage: float
    api_calls_today: int


class APIServer:
    """FastAPI server for bot management."""

    def __init__(self, bot_manager: BotManager, config_manager: ConfigManager):
        self.bot_manager = bot_manager
        self.config_manager = config_manager
        self.app = FastAPI(
            title="GrugThink Management API",
            description="API for managing multiple Discord bot instances",
            version="2.0.0"
        )

        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Setup routes
        self._setup_routes()

        # Setup static file serving for web dashboard
        try:
            self.app.mount("/static", StaticFiles(directory="web/static"), name="static")
        except:
            log.warning("Static files directory not found, web dashboard may not work")

        # Setup periodic tasks
        self._setup_background_tasks()

        log.info("API Server initialized")

    def _setup_routes(self):
        """Setup FastAPI routes."""

        # Dashboard route
        @self.app.get("/")
        async def dashboard():
            try:
                return FileResponse("web/index.html")
            except:
                return {"message": "GrugThink Management API", "version": "2.0.0"}

        # Bot management routes
        @self.app.get("/api/bots", response_model=List[Dict[str, Any]])
        async def list_bots():
            """List all bot configurations and their status."""
            return self.bot_manager.list_bots()

        @self.app.get("/api/bots/{bot_id}")
        async def get_bot(bot_id: str):
            """Get specific bot status and configuration."""
            bot_status = self.bot_manager.get_bot_status(bot_id)
            if not bot_status:
                raise HTTPException(status_code=404, detail="Bot not found")
            return bot_status

        @self.app.post("/api/bots", response_model=BotActionResponse)
        async def create_bot(request: CreateBotRequest):
            """Create a new bot instance."""
            try:
                # Get template and create environment
                template = self.config_manager.get_template(request.template_id)
                if not template:
                    raise HTTPException(status_code=400, detail=f"Template '{request.template_id}' not found")

                # Create bot environment from template
                bot_env = self.config_manager.create_bot_env(
                    request.template_id,
                    request.discord_token,
                    **request.custom_env
                )

                # Override with specific values if provided
                overrides = {}
                if request.gemini_api_key:
                    overrides["gemini_api_key"] = request.gemini_api_key
                if request.ollama_urls:
                    overrides["ollama_urls"] = request.ollama_urls
                if request.ollama_models:
                    overrides["ollama_models"] = request.ollama_models
                if request.google_api_key:
                    overrides["google_api_key"] = request.google_api_key
                if request.google_cse_id:
                    overrides["google_cse_id"] = request.google_cse_id
                if request.trusted_user_ids:
                    overrides["trusted_user_ids"] = request.trusted_user_ids

                bot_id = self.bot_manager.create_bot(
                    name=request.name,
                    discord_token=request.discord_token,
                    force_personality=template.force_personality,
                    load_embedder=template.load_embedder,
                    **overrides
                )

                await self._broadcast_update("bot_created", {"bot_id": bot_id, "name": request.name})

                return BotActionResponse(
                    success=True,
                    message=f"Bot '{request.name}' created successfully",
                    bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to create bot", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/api/bots/{bot_id}", response_model=BotActionResponse)
        async def update_bot(bot_id: str, request: UpdateBotRequest):
            """Update bot configuration."""
            try:
                updates = {}
                for field, value in request.dict(exclude_unset=True).items():
                    if value is not None:
                        updates[field] = value

                success = self.bot_manager.update_bot_config(bot_id, **updates)
                if not success:
                    raise HTTPException(status_code=404, detail="Bot not found")

                await self._broadcast_update("bot_updated", {"bot_id": bot_id, "updates": list(updates.keys())})

                return BotActionResponse(
                    success=True,
                    message="Bot configuration updated successfully",
                    bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to update bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/bots/{bot_id}", response_model=BotActionResponse)
        async def delete_bot(bot_id: str):
            """Delete a bot instance."""
            try:
                success = self.bot_manager.delete_bot(bot_id)
                if not success:
                    raise HTTPException(status_code=404, detail="Bot not found")

                await self._broadcast_update("bot_deleted", {"bot_id": bot_id})

                return BotActionResponse(
                    success=True,
                    message="Bot deleted successfully",
                    bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to delete bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/bots/{bot_id}/start", response_model=BotActionResponse)
        async def start_bot(bot_id: str, background_tasks: BackgroundTasks):
            """Start a bot instance."""
            try:
                background_tasks.add_task(self._start_bot_task, bot_id)

                return BotActionResponse(
                    success=True,
                    message="Bot start initiated",
                    bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to start bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/bots/{bot_id}/stop", response_model=BotActionResponse)
        async def stop_bot(bot_id: str, background_tasks: BackgroundTasks):
            """Stop a bot instance."""
            try:
                background_tasks.add_task(self._stop_bot_task, bot_id)

                return BotActionResponse(
                    success=True,
                    message="Bot stop initiated",
                    bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to stop bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/bots/{bot_id}/restart", response_model=BotActionResponse)
        async def restart_bot(bot_id: str, background_tasks: BackgroundTasks):
            """Restart a bot instance."""
            try:
                background_tasks.add_task(self._restart_bot_task, bot_id)

                return BotActionResponse(
                    success=True,
                    message="Bot restart initiated",
                    bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to restart bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        # Configuration management routes
        @self.app.get("/api/config")
        async def get_config():
            """Get current configuration."""
            return self.config_manager.get_config()

        @self.app.put("/api/config", response_model=Dict[str, str])
        async def update_config(request: ConfigUpdateRequest):
            """Update configuration value."""
            try:
                self.config_manager.set_config(request.key, request.value)
                await self._broadcast_update("config_updated", {"key": request.key})

                return {"status": "success", "message": "Configuration updated"}

            except Exception as e:
                log.error("Failed to update config", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/templates")
        async def list_templates():
            """List available bot templates."""
            templates = self.config_manager.list_templates()
            return {
                template_id: {
                    "name": template.name,
                    "description": template.description,
                    "force_personality": template.force_personality,
                    "load_embedder": template.load_embedder
                }
                for template_id, template in templates.items()
            }

        @self.app.post("/api/discord-tokens", response_model=Dict[str, str])
        async def add_discord_token(request: AddDiscordTokenRequest):
            """Add a Discord bot token."""
            try:
                token_id = self.config_manager.add_discord_token(request.name, request.token)
                await self._broadcast_update("token_added", {"name": request.name, "token_id": token_id})

                return {"status": "success", "token_id": token_id}

            except Exception as e:
                log.error("Failed to add Discord token", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/discord-tokens")
        async def list_discord_tokens():
            """List Discord tokens (without revealing actual tokens)."""
            tokens = self.config_manager.get_discord_tokens()
            return [
                {
                    "id": token["id"],
                    "name": token["name"],
                    "added_at": token["added_at"],
                    "active": token.get("active", True)
                }
                for token in tokens
            ]

        @self.app.post("/api/api-keys", response_model=Dict[str, str])
        async def set_api_key(request: SetApiKeyRequest):
            """Set API key for a service."""
            try:
                self.config_manager.set_api_key(request.service, request.key_name, request.value)
                await self._broadcast_update("api_key_updated", {
                    "service": request.service,
                    "key_name": request.key_name
                })

                return {"status": "success", "message": f"{request.service} API key updated"}

            except Exception as e:
                log.error("Failed to set API key", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/api-keys/{service}")
        async def get_api_keys(service: str):
            """Get API keys for a service (without revealing values)."""
            keys = self.config_manager.get_api_keys(service)
            # Return structure without actual key values
            return {key: "***REDACTED***" if value else None for key, value in keys.items()}

        # System information routes
        @self.app.get("/api/system/stats", response_model=SystemStatsResponse)
        async def get_system_stats():
            """Get system statistics."""
            bots = self.bot_manager.list_bots()
            running_bots = [bot for bot in bots if bot["status"] == "running"]

            total_guilds = sum(bot.get("guild_count", 0) for bot in running_bots)
            total_users = sum(bot.get("user_count", 0) for bot in running_bots)

            return SystemStatsResponse(
                total_bots=len(bots),
                running_bots=len(running_bots),
                total_guilds=total_guilds,
                total_users=total_users,
                uptime=0.0,  # TODO: Implement uptime tracking
                memory_usage=0.0,  # TODO: Implement memory monitoring
                api_calls_today=0  # TODO: Implement API call tracking
            )

        @self.app.get("/api/system/logs")
        async def get_system_logs():
            """Get recent system logs."""
            # TODO: Implement log retrieval
            return {"logs": [], "message": "Log retrieval not yet implemented"}

        # WebSocket endpoint for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)

            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    # Echo back for now - could handle client commands
                    await websocket.send_text(f"Echo: {data}")

            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)

    async def _start_bot_task(self, bot_id: str):
        """Background task to start a bot."""
        try:
            success = await self.bot_manager.start_bot(bot_id)
            await self._broadcast_update("bot_status_changed", {
                "bot_id": bot_id,
                "status": "running" if success else "error"
            })
        except Exception as e:
            log.error("Error in start bot task", extra={"bot_id": bot_id, "error": str(e)})

    async def _stop_bot_task(self, bot_id: str):
        """Background task to stop a bot."""
        try:
            success = await self.bot_manager.stop_bot(bot_id)
            await self._broadcast_update("bot_status_changed", {
                "bot_id": bot_id,
                "status": "stopped" if success else "error"
            })
        except Exception as e:
            log.error("Error in stop bot task", extra={"bot_id": bot_id, "error": str(e)})

    async def _restart_bot_task(self, bot_id: str):
        """Background task to restart a bot."""
        try:
            success = await self.bot_manager.restart_bot(bot_id)
            await self._broadcast_update("bot_status_changed", {
                "bot_id": bot_id,
                "status": "running" if success else "error"
            })
        except Exception as e:
            log.error("Error in restart bot task", extra={"bot_id": bot_id, "error": str(e)})

    async def _broadcast_update(self, event_type: str, data: Dict[str, Any]):
        """Broadcast update to all WebSocket connections."""
        if not self.websocket_connections:
            return

        message = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # Remove disconnected websockets
        active_connections = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
                active_connections.append(websocket)
            except:
                # Connection is dead, remove it
                pass

        self.websocket_connections = active_connections

    def _setup_background_tasks(self):
        """Setup periodic background tasks."""
        # TODO: Add periodic tasks for monitoring, cleanup, etc.
        pass

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Run the API server."""
        log.info("Starting API server", extra={"host": host, "port": port})
        uvicorn.run(self.app, host=host, port=port)


async def main():
    """Main entry point for the API server."""
    # Initialize managers
    config_manager = ConfigManager()
    bot_manager = BotManager()

    # Create API server
    api_server = APIServer(bot_manager, config_manager)

    # Start bot monitoring
    monitoring_task = asyncio.create_task(bot_manager.monitor_bots())

    try:
        # Run the server
        api_server.run()
    finally:
        # Cleanup
        monitoring_task.cancel()
        await bot_manager.stop_all_bots()
        config_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
