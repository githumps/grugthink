#!/usr/bin/env python3
"""
GrugThink Management API Server

RESTful API for managing multiple Discord bot instances, configurations,
and monitoring. Provides endpoints for the web dashboard frontend.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, Set

import requests
import uvicorn
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from .bot_manager import BotManager
from .config_manager import ConfigManager
from .grug_structured_logger import get_logger

# In-memory log storage for web dashboard
RECENT_LOGS: List[Dict[str, str]] = []

# Simple cache for API responses
API_CACHE: Dict[str, tuple] = {}  # key: (data, timestamp)
CACHE_TTL = 30  # seconds


def cache_response(ttl: int = CACHE_TTL):
    """Decorator to cache API responses for better performance."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and args
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # Check cache
            if cache_key in API_CACHE:
                data, timestamp = API_CACHE[cache_key]
                if time.time() - timestamp < ttl:
                    return data

            # Execute function and cache result
            result = await func(*args, **kwargs)
            API_CACHE[cache_key] = (result, time.time())

            # Clean old cache entries periodically
            if len(API_CACHE) > 100:
                API_CACHE.clear()  # Simple cleanup

            return result

        return wrapper

    return decorator


class InMemoryLogHandler(logging.Handler):
    """Simple logging handler that keeps recent logs in memory."""

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()

        # Try to parse JSON message from StructuredLogger
        structured_data = None
        try:
            structured_data = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            # Not a JSON message, use as-is
            pass

        # Extract message and other data
        if structured_data and isinstance(structured_data, dict):
            log_entry = structured_data
            actual_message = structured_data.get("message", message)
            bot_id = structured_data.get("bot_id")
        else:
            log_entry = {"message": message}
            actual_message = message
            bot_id = None

        log_entry.update(
            {
                "level": record.levelname.lower(),
                "message": actual_message,
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "logger": record.name,
            }
        )

        # Extract bot_id from various sources
        if bot_id:
            log_entry["bot_id"] = bot_id
        elif hasattr(record, "bot_id"):
            log_entry["bot_id"] = record.bot_id
        elif "extra" in record.__dict__ and isinstance(record.extra, dict):
            if "bot_id" in record.extra:
                log_entry["bot_id"] = record.extra["bot_id"]

        RECENT_LOGS.append(log_entry)
        if len(RECENT_LOGS) > 2000:  # Increased buffer for multiple bots
            RECENT_LOGS.pop(0)


log = get_logger(__name__)
logging.getLogger().addHandler(InMemoryLogHandler())

log = get_logger(__name__)


# Pydantic models for API requests/responses
class CreateBotRequest(BaseModel):
    name: str
    template_id: str
    discord_token_id: str
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
    personality: Optional[str] = None
    force_personality: Optional[str] = None
    load_embedder: Optional[bool] = None
    log_level: Optional[str] = None
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
            version="2.0.0",
            # Performance optimizations
            docs_url=None,  # Disable docs in production
            redoc_url=None,  # Disable redoc in production
        )

        # Get session secret from config manager or environment
        session_secret = "grug-secret"  # default
        if self.config_manager:
            session_secret = self.config_manager.get_env_var("SESSION_SECRET_KEY", session_secret)
        else:
            session_secret = os.getenv("SESSION_SECRET", session_secret)

        self.app.add_middleware(
            SessionMiddleware,
            secret_key=session_secret,
        )

        # WebSocket connections for real-time updates
        self.websocket_connections: List[WebSocket] = []

        # Add CORS middleware with optimizations
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods only
            allow_headers=["*"],
        )

        # Add gzip compression middleware
        from fastapi.middleware.gzip import GZipMiddleware

        self.app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Setup routes
        self._setup_routes()

        # Setup static file serving for web dashboard with caching
        try:
            # Custom StaticFiles with better caching headers
            class CachedStaticFiles(StaticFiles):
                def file_response(
                    self, full_path: str, stat_result: os.stat_result, scope: dict, status_code: int = 200
                ):
                    response = super().file_response(full_path, stat_result, scope, status_code)
                    from pathlib import Path

                    path_obj = Path(full_path)
                    # Add cache headers for better performance
                    if path_obj.suffix in [".css", ".js", ".png", ".jpg", ".ico"]:
                        response.headers["Cache-Control"] = "public, max-age=86400"  # 1 day
                    elif path_obj.suffix in [".html"]:
                        response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes

                    # Add compression hint
                    response.headers["Vary"] = "Accept-Encoding"

                    return response

            self.app.mount("/static", CachedStaticFiles(directory="web/static"), name="static")
        except Exception:
            log.warning("Static files directory not found, web dashboard may not work")

        # Setup periodic tasks
        self._setup_background_tasks()

        log.info("API Server initialized")

    def _setup_routes(self):
        """Setup FastAPI routes."""

        def get_current_user(request: Request) -> Dict[str, Any]:
            # Check if OAuth is disabled
            disable_oauth = False
            if self.config_manager:
                disable_oauth = self.config_manager.get_env_var("DISABLE_OAUTH", "false").lower() == "true"
            else:
                disable_oauth = os.getenv("DISABLE_OAUTH", "false").lower() == "true"

            if disable_oauth:
                # Return dummy user when OAuth is disabled
                return {"id": "admin", "username": "admin"}

            user = request.session.get("user")
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return user

        def admin_required(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
            # Check if OAuth is disabled - if so, skip trusted user checks
            disable_oauth = False
            if self.config_manager:
                disable_oauth = self.config_manager.get_env_var("DISABLE_OAUTH", "false").lower() == "true"
            else:
                disable_oauth = os.getenv("DISABLE_OAUTH", "false").lower() == "true"

            if disable_oauth:
                # When OAuth is disabled, allow all access
                return user

            # Get trusted users from config manager or environment
            trusted_str = ""
            if self.config_manager:
                trusted_str = self.config_manager.get_env_var("TRUSTED_USER_IDS", "")
            else:
                trusted_str = os.getenv("TRUSTED_USER_IDS", "")

            trusted = trusted_str.split(",")
            trusted = [t.strip() for t in trusted if t.strip()]
            if user["id"] not in trusted:
                raise HTTPException(status_code=403, detail="Forbidden")
            return user

        # Dashboard route
        @self.app.get("/")
        async def dashboard(request: Request):
            # Check if OAuth is disabled
            disable_oauth = False
            if self.config_manager:
                disable_oauth = self.config_manager.get_env_var("DISABLE_OAUTH", "false").lower() == "true"
            else:
                disable_oauth = os.getenv("DISABLE_OAUTH", "false").lower() == "true"

            if not disable_oauth:
                # Check if user is authenticated
                user = request.session.get("user")
                if not user:
                    return RedirectResponse("/login")

            try:
                return FileResponse("web/index.html")
            except Exception:
                return {"message": "GrugThink Management API", "version": "2.0.0"}

        @self.app.get("/login")
        async def login():
            # Check if OAuth is disabled
            disable_oauth = False
            if self.config_manager:
                disable_oauth = self.config_manager.get_env_var("DISABLE_OAUTH", "false").lower() == "true"
            else:
                disable_oauth = os.getenv("DISABLE_OAUTH", "false").lower() == "true"

            if disable_oauth:
                # If OAuth is disabled, redirect to dashboard
                return RedirectResponse("/")

            # Get Discord OAuth settings from config manager
            client_id = None
            redirect_uri = None

            if self.config_manager:
                client_id = self.config_manager.get_env_var("DISCORD_CLIENT_ID")
                redirect_uri = self.config_manager.get_env_var("DISCORD_REDIRECT_URI")

            # Fall back to environment variables
            if not client_id:
                client_id = os.getenv("DISCORD_CLIENT_ID")
            if not redirect_uri:
                redirect_uri = os.getenv("DISCORD_REDIRECT_URI")

            if not client_id:
                raise HTTPException(status_code=500, detail="Discord OAuth not configured - missing DISCORD_CLIENT_ID")
            if not redirect_uri:
                raise HTTPException(
                    status_code=500, detail="Discord OAuth not configured - missing DISCORD_REDIRECT_URI"
                )

            params = {
                "client_id": client_id,
                "response_type": "code",
                "scope": "identify",
                "redirect_uri": redirect_uri,
            }
            url = "https://discord.com/api/oauth2/authorize?" + requests.compat.urlencode(params)
            return RedirectResponse(url)

        @self.app.get("/callback")
        async def auth_callback(request: Request):
            code = request.query_params.get("code")
            if not code:
                raise HTTPException(status_code=400, detail="Missing code")

            # Get Discord OAuth settings from config manager
            client_id = None
            client_secret = None
            redirect_uri = None

            if self.config_manager:
                client_id = self.config_manager.get_env_var("DISCORD_CLIENT_ID")
                client_secret = self.config_manager.get_env_var("DISCORD_CLIENT_SECRET")
                redirect_uri = self.config_manager.get_env_var("DISCORD_REDIRECT_URI")

            # Fall back to environment variables
            if not client_id:
                client_id = os.getenv("DISCORD_CLIENT_ID")
            if not client_secret:
                client_secret = os.getenv("DISCORD_CLIENT_SECRET")
            if not redirect_uri:
                redirect_uri = os.getenv("DISCORD_REDIRECT_URI")

            if not client_id or not client_secret or not redirect_uri:
                raise HTTPException(status_code=500, detail="Discord OAuth not configured properly")

            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            token_res = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            user_res = requests.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_res.raise_for_status()
            user = user_res.json()

            # Get trusted users from config manager or environment
            trusted_str = ""
            if self.config_manager:
                trusted_str = self.config_manager.get_env_var("TRUSTED_USER_IDS", "")
            else:
                trusted_str = os.getenv("TRUSTED_USER_IDS", "")

            trusted = trusted_str.split(",")
            trusted = [t.strip() for t in trusted if t.strip()]
            if str(user["id"]) not in trusted:
                return Response("Access denied", status_code=403)

            request.session["user"] = {"id": str(user["id"]), "username": user["username"]}
            return RedirectResponse("/")

        @self.app.get("/logout")
        async def logout(request: Request):
            request.session.clear()
            return RedirectResponse("/")

        @self.app.get("/api/user")
        async def get_user(request: Request):
            """Get current authenticated user info."""
            # Check if OAuth is disabled
            disable_oauth = False
            if self.config_manager:
                disable_oauth = self.config_manager.get_env_var("DISABLE_OAUTH", "false").lower() == "true"
            else:
                disable_oauth = os.getenv("DISABLE_OAUTH", "false").lower() == "true"

            if disable_oauth:
                # Return dummy user when OAuth is disabled
                return {"id": "admin", "username": "admin"}

            user = request.session.get("user")
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return user

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for Docker and monitoring."""
            return {
                "status": "healthy",
                "service": "grugthink-api",
                "version": "2.0.0",
                "timestamp": datetime.now().isoformat(),
            }

        # Bot management routes
        @self.app.get("/api/bots", response_model=List[Dict[str, Any]], dependencies=[Depends(admin_required)])
        async def list_bots():
            """List all bot configurations and their status."""
            return self.bot_manager.list_bots()

        @self.app.get("/api/bots/{bot_id}", dependencies=[Depends(admin_required)])
        async def get_bot(bot_id: str):
            """Get specific bot status and configuration."""
            bot_status = self.bot_manager.get_bot_status(bot_id)
            if not bot_status:
                raise HTTPException(status_code=404, detail="Bot not found")
            return bot_status

        @self.app.post(
            "/api/bots",
            response_model=BotActionResponse,
            dependencies=[Depends(admin_required)],
        )
        async def create_bot(request: CreateBotRequest):
            """Create a new bot instance."""
            try:
                # Get template and create environment
                template = self.config_manager.get_template(request.template_id)
                if not template:
                    raise HTTPException(status_code=400, detail=f"Template '{request.template_id}' not found")

                # Retrieve the actual Discord token using the token ID
                discord_token = self.config_manager.get_discord_token_by_id(request.discord_token_id)
                if not discord_token:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Discord token with ID '{request.discord_token_id}' not found or inactive.",
                    )

                # Create bot environment from template
                self.config_manager.create_bot_env(request.template_id, discord_token, **request.custom_env)

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

                # Extract template settings
                template_dict = template if isinstance(template, dict) else template.__dict__

                bot_id = self.bot_manager.create_bot(
                    name=request.name,
                    discord_token_id=request.discord_token_id,
                    template_id=request.template_id,
                    personality=template_dict.get("personality"),
                    load_embedder=template_dict.get("load_embedder", True),
                    **overrides,
                )

                await self._broadcast_update("bot_created", {"bot_id": bot_id, "name": request.name})

                return BotActionResponse(
                    success=True, message=f"Bot '{request.name}' created successfully", bot_id=bot_id
                )

            except Exception as e:
                log.error("Failed to create bot", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put(
            "/api/bots/{bot_id}",
            response_model=BotActionResponse,
            dependencies=[Depends(admin_required)],
        )
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

                return BotActionResponse(success=True, message="Bot configuration updated successfully", bot_id=bot_id)

            except Exception as e:
                log.error("Failed to update bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete(
            "/api/bots/{bot_id}",
            response_model=BotActionResponse,
            dependencies=[Depends(admin_required)],
        )
        async def delete_bot(bot_id: str):
            """Delete a bot instance."""
            try:
                success = await self.bot_manager.delete_bot(bot_id)
                if not success:
                    raise HTTPException(status_code=404, detail="Bot not found")

                await self._broadcast_update("bot_deleted", {"bot_id": bot_id})

                return BotActionResponse(success=True, message="Bot deleted successfully", bot_id=bot_id)

            except Exception as e:
                log.error("Failed to delete bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post(
            "/api/bots/{bot_id}/start",
            response_model=BotActionResponse,
            dependencies=[Depends(admin_required)],
        )
        async def start_bot(bot_id: str, background_tasks: BackgroundTasks):
            """Start a bot instance."""
            try:
                background_tasks.add_task(self._start_bot_task, bot_id)

                return BotActionResponse(success=True, message="Bot start initiated", bot_id=bot_id)

            except Exception as e:
                log.error("Failed to start bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post(
            "/api/bots/{bot_id}/stop",
            response_model=BotActionResponse,
            dependencies=[Depends(admin_required)],
        )
        async def stop_bot(bot_id: str, background_tasks: BackgroundTasks):
            """Stop a bot instance."""
            try:
                background_tasks.add_task(self._stop_bot_task, bot_id)

                return BotActionResponse(success=True, message="Bot stop initiated", bot_id=bot_id)

            except Exception as e:
                log.error("Failed to stop bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post(
            "/api/bots/{bot_id}/restart",
            response_model=BotActionResponse,
            dependencies=[Depends(admin_required)],
        )
        async def restart_bot(bot_id: str, background_tasks: BackgroundTasks):
            """Restart a bot instance."""
            try:
                background_tasks.add_task(self._restart_bot_task, bot_id)

                return BotActionResponse(success=True, message="Bot restart initiated", bot_id=bot_id)

            except Exception as e:
                log.error("Failed to restart bot", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        # Configuration management routes
        @self.app.get("/api/config", dependencies=[Depends(admin_required)])
        async def get_config():
            """Get current configuration."""
            return self.config_manager.get_config()

        @self.app.put(
            "/api/config",
            response_model=Dict[str, str],
            dependencies=[Depends(admin_required)],
        )
        async def update_config(request: ConfigUpdateRequest):
            """Update configuration value."""
            try:
                self.config_manager.set_config(request.key, request.value)
                await self._broadcast_update("config_updated", {"key": request.key})

                return {"status": "success", "message": "Configuration updated"}

            except Exception as e:
                log.error("Failed to update config", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/templates/sync", dependencies=[Depends(admin_required)])
        async def sync_personalities_to_templates():
            """Automatically create templates for personalities that don't have them."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            try:
                self.config_manager.sync_personalities_to_templates()
                return {"message": "Personalities synchronized to templates successfully"}
            except Exception as e:
                log.error("Failed to sync personalities to templates", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=f"Failed to sync: {str(e)}")

        @self.app.get("/api/templates", dependencies=[Depends(admin_required)])
        @cache_response(ttl=300)  # Cache for 5 minutes
        async def list_templates():
            """List available bot templates."""
            templates = self.config_manager.list_templates()
            return {
                template_id: {
                    "name": template.name,
                    "description": template.description,
                    "force_personality": template.get_personality(),  # Use unified method
                    "load_embedder": template.load_embedder,
                }
                for template_id, template in templates.items()
            }

        @self.app.post(
            "/api/discord-tokens",
            response_model=Dict[str, str],
            dependencies=[Depends(admin_required)],
        )
        async def add_discord_token(request: AddDiscordTokenRequest):
            """Add a Discord bot token."""
            try:
                token_id = self.config_manager.add_discord_token(request.name, request.token)
                await self._broadcast_update("token_added", {"name": request.name, "token_id": token_id})

                return {"status": "success", "token_id": token_id}

            except Exception as e:
                log.error("Failed to add Discord token", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/discord-tokens", dependencies=[Depends(admin_required)])
        @cache_response(ttl=60)  # Cache for 1 minute
        async def list_discord_tokens():
            """List Discord tokens (without revealing actual tokens)."""
            tokens = self.config_manager.get_discord_tokens()
            return [
                {
                    "id": token["id"],
                    "name": token["name"],
                    "added_at": token["added_at"],
                    "active": token.get("active", True),
                }
                for token in tokens
            ]

        @self.app.delete(
            "/api/discord-tokens/{token_id}",
            dependencies=[Depends(admin_required)],
        )
        async def delete_discord_token(token_id: str):
            """Delete a stored Discord bot token."""
            if not self.config_manager.remove_discord_token(token_id):
                raise HTTPException(status_code=404, detail="Token not found")
            await self._broadcast_update("token_deleted", {"token_id": token_id})
            return {"status": "success"}

        @self.app.post(
            "/api/api-keys",
            response_model=Dict[str, str],
            dependencies=[Depends(admin_required)],
        )
        async def set_api_key(request: SetApiKeyRequest):
            """Set API key for a service."""
            try:
                self.config_manager.set_api_key(request.service, request.key_name, request.value)
                await self._broadcast_update(
                    "api_key_updated", {"service": request.service, "key_name": request.key_name}
                )

                return {"status": "success", "message": f"{request.service} API key updated"}

            except Exception as e:
                log.error("Failed to set API key", extra={"error": str(e)})
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/api-keys/{service}", dependencies=[Depends(admin_required)])
        async def get_api_keys(service: str):
            """Get API keys for a service (without revealing values)."""
            keys = self.config_manager.get_api_keys(service)
            # Return structure without actual key values
            return {key: "***REDACTED***" if value else None for key, value in keys.items()}

        # System information routes
        @self.app.get(
            "/api/system/stats",
            response_model=SystemStatsResponse,
            dependencies=[Depends(admin_required)],
        )
        async def get_system_stats():
            """Get system statistics."""
            bots = self.bot_manager.list_bots()
            running_bots = [bot for bot in bots if bot["status"] == "running"]

            guild_ids: Set[int] = set()
            for bot in running_bots:
                guild_ids.update(bot.get("guild_ids", []))

            total_guilds = len(guild_ids)

            return SystemStatsResponse(
                total_bots=len(bots),
                running_bots=len(running_bots),
                total_guilds=total_guilds,
                uptime=0.0,  # TODO: Implement uptime tracking
                memory_usage=0.0,  # TODO: Implement memory monitoring
                api_calls_today=0,  # TODO: Implement API call tracking
            )

        @self.app.get("/api/system/logs", dependencies=[Depends(admin_required)])
        async def get_system_logs():
            """Get recent system logs."""
            return {"logs": RECENT_LOGS[-200:]}  # return last 200 entries

        @self.app.get("/api/bots/{bot_id}/logs", dependencies=[Depends(admin_required)])
        async def get_bot_logs(bot_id: str):
            """Get logs for a specific bot."""
            bot_logs = [log for log in RECENT_LOGS if log.get("bot_id") == bot_id or bot_id in log.get("message", "")]
            return {"logs": bot_logs[-100:]}  # return last 100 entries for this bot

        # Personality management endpoints
        @self.app.get("/api/personalities", dependencies=[Depends(admin_required)])
        async def get_personalities():
            """Get all available personalities."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")
            personalities = self.config_manager.list_personalities()
            return {"personalities": personalities}

        @self.app.get("/api/personalities/{personality_id}", dependencies=[Depends(admin_required)])
        async def get_personality(personality_id: str):
            """Get a specific personality configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")
            personality = self.config_manager.get_personality(personality_id)
            if not personality:
                raise HTTPException(status_code=404, detail=f"Personality '{personality_id}' not found")
            return {"personality": personality}

        @self.app.post("/api/personalities/generate", dependencies=[Depends(admin_required)])
        async def generate_personality_with_ai(request: Dict[str, str]):
            """Generate a personality using Gemini AI based on user description."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            description = request.get("description", "").strip()
            personality_id = request.get("personality_id", "").strip()

            if not description or not personality_id:
                raise HTTPException(status_code=400, detail="Both 'description' and 'personality_id' are required")

            # Check if personality already exists
            existing = self.config_manager.get_personality(personality_id)
            if existing:
                raise HTTPException(status_code=409, detail=f"Personality '{personality_id}' already exists")

            try:
                # Import Gemini functionality
                import google.generativeai as genai

                # Get Gemini API key from ConfigManager instead of environment
                gemini_keys = self.config_manager.get_api_keys("gemini")
                gemini_api_key = gemini_keys.get("primary")

                if not gemini_api_key:
                    raise HTTPException(status_code=500, detail="Gemini API key not configured")

                genai.configure(api_key=gemini_api_key)

                # Get model from config or use default
                gemini_model = self.config_manager.get_env_var("GEMINI_MODEL", "gemini-pro")
                model = genai.GenerativeModel(gemini_model)

                # Create the prompt for personality generation
                prompt = f"""You are an expert YAML personality designer for Discord chatbots.
Create a personality YAML configuration based on this description: "{description}"

Your output must follow this EXACT structure and format. Be creative but maintain the structure:

```yaml
name: "Character Name Here"
description: "Brief description of the character"

behavior:
  emotions:
    confused: "How they express confusion"
    excited: "How they express excitement"
    happy: "How they express happiness"
    sad: "How they express sadness"
  response_patterns:
    agreement: "How they agree with something"
    confusion: "How they ask for clarification"
    disagreement: "How they disagree"
    farewell: "How they say goodbye"
    greeting: "How they greet people"
    learning: "How they respond when learning something new"

speech:
  catchphrases:
    - "First catchphrase"
    - "Second catchphrase"
    - "Third catchphrase"
    - "Fourth catchphrase"
    - "Fifth catchphrase"
  error_prefix: "What they say before errors:"
  help_prefix: "What they say before helping:"
  sentence_structure: "simple/casual/formal/complex"
  thinking_prefix: "What they say while thinking..."
  verification_prefix: "How they start factual statements:"
  vocabulary_level: "basic/colloquial/normal/advanced"
  word_replacements:
    original_word: "replacement_word"
    another_word: "replacement"

traits:
  emotional_range: "basic/normal/complex"
  humor_style: "innocent/cheeky/sarcastic/dry/playful"
  intelligence_level: "simple/average/advanced/genius"
  verbosity: "concise/normal/verbose"
```

Generate ONLY the YAML content. No explanation, no markdown formatting,
just the raw YAML that can be parsed directly."""

                # Generate personality with Gemini
                response = model.generate_content(prompt)
                generated_yaml = response.text.strip()

                # Clean up any markdown formatting that might have leaked through
                if "```yaml" in generated_yaml:
                    generated_yaml = generated_yaml.split("```yaml")[1].split("```")[0].strip()
                elif "```" in generated_yaml:
                    generated_yaml = generated_yaml.split("```")[1].split("```")[0].strip()

                # Validate YAML structure
                import yaml

                try:
                    personality_data = yaml.safe_load(generated_yaml)
                    if not isinstance(personality_data, dict):
                        raise ValueError("Generated content is not a valid YAML object")

                    # Ensure required fields exist
                    required_fields = ["name", "description", "behavior", "speech", "traits"]
                    for field in required_fields:
                        if field not in personality_data:
                            raise ValueError(f"Missing required field: {field}")

                except yaml.YAMLError as e:
                    raise HTTPException(status_code=500, detail=f"Generated YAML is invalid: {str(e)}")
                except ValueError as e:
                    raise HTTPException(status_code=500, detail=f"Generated content validation failed: {str(e)}")

                # Save the personality
                success = self.config_manager.add_personality(personality_id, personality_data)
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to save generated personality")

                # Also save to personalities directory as YAML file
                import os

                personalities_dir = "personalities"
                if not os.path.exists(personalities_dir):
                    os.makedirs(personalities_dir)

                yaml_file_path = os.path.join(personalities_dir, f"{personality_id}.yaml")
                with open(yaml_file_path, "w") as f:
                    f.write(generated_yaml)

                # Auto-sync personalities to templates
                self.config_manager.sync_personalities_to_templates()

                await self._broadcast_update("personality_created", {"personality_id": personality_id})

                return {
                    "message": f"Personality '{personality_id}' generated and saved successfully",
                    "personality_id": personality_id,
                    "generated_yaml": generated_yaml,
                    "personality_data": personality_data,
                }

            except ImportError:
                raise HTTPException(
                    status_code=500, detail="Gemini AI not available - missing google-generativeai package"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to generate personality: {str(e)}")

        @self.app.post("/api/personalities/{personality_id}", dependencies=[Depends(admin_required)])
        async def create_personality(personality_id: str, personality_config: Dict[str, Any]):
            """Create a new personality configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            # Check if personality already exists
            existing = self.config_manager.get_personality(personality_id)
            if existing:
                raise HTTPException(status_code=409, detail=f"Personality '{personality_id}' already exists")

            success = self.config_manager.add_personality(personality_id, personality_config)
            if success:
                # Auto-sync personalities to templates
                self.config_manager.sync_personalities_to_templates()

                await self._broadcast_update("personality_created", {"personality_id": personality_id})
                return {"message": f"Personality '{personality_id}' created successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to create personality")

        @self.app.put("/api/personalities/{personality_id}", dependencies=[Depends(admin_required)])
        async def update_personality(personality_id: str, updates: Dict[str, Any]):
            """Update a personality configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            success = self.config_manager.update_personality(personality_id, updates)
            if success:
                await self._broadcast_update("personality_updated", {"personality_id": personality_id})
                return {"message": f"Personality '{personality_id}' updated successfully"}
            else:
                raise HTTPException(status_code=404, detail=f"Personality '{personality_id}' not found")

        @self.app.delete("/api/personalities/{personality_id}", dependencies=[Depends(admin_required)])
        async def delete_personality(personality_id: str):
            """Delete a personality configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            success = self.config_manager.remove_personality(personality_id)
            if success:
                await self._broadcast_update("personality_deleted", {"personality_id": personality_id})
                return {"message": f"Personality '{personality_id}' deleted successfully"}
            else:
                raise HTTPException(status_code=404, detail=f"Personality '{personality_id}' not found")

        # Memory management endpoints
        @self.app.get("/api/bots/{bot_id}/memories", dependencies=[Depends(admin_required)])
        async def get_bot_memories(bot_id: str, search: str = None, limit: int = 100):
            """Get memories for a specific bot."""
            if not self.bot_manager:
                raise HTTPException(status_code=500, detail="Bot manager not available")

            try:
                # Get the bot's server manager and database
                bot = self.bot_manager.bots.get(bot_id)
                if not bot:
                    raise HTTPException(status_code=404, detail=f"Bot '{bot_id}' not found")

                server_manager = getattr(bot, "server_manager", None)
                if not server_manager:
                    raise HTTPException(status_code=500, detail="Server manager not available")

                # Get default server database for this bot
                server_db = server_manager.get_server_db("default")

                if search:
                    facts = server_db.search_facts(search, k=limit)
                else:
                    facts = server_db.get_all_facts()[:limit]

                return {
                    "bot_id": bot_id,
                    "total_memories": len(server_db.get_all_facts()),
                    "memories": [{"id": i, "content": fact} for i, fact in enumerate(facts)],
                    "search": search,
                    "limit": limit,
                }

            except Exception as e:
                log.error("Failed to get bot memories", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=f"Failed to get memories: {str(e)}")

        @self.app.post("/api/bots/{bot_id}/memories", dependencies=[Depends(admin_required)])
        async def add_bot_memory(bot_id: str, memory: Dict[str, str]):
            """Add a new memory to a bot."""
            if not self.bot_manager:
                raise HTTPException(status_code=500, detail="Bot manager not available")

            content = memory.get("content", "").strip()
            if not content:
                raise HTTPException(status_code=400, detail="Memory content is required")

            try:
                bot = self.bot_manager.bots.get(bot_id)
                if not bot:
                    raise HTTPException(status_code=404, detail=f"Bot '{bot_id}' not found")

                server_manager = getattr(bot, "server_manager", None)
                if not server_manager:
                    raise HTTPException(status_code=500, detail="Server manager not available")

                server_db = server_manager.get_server_db("default")
                success = server_db.add_fact(content)

                if success:
                    return {"message": "Memory added successfully", "content": content}
                else:
                    return {"message": "Memory already exists", "content": content}

            except Exception as e:
                log.error("Failed to add bot memory", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=f"Failed to add memory: {str(e)}")

        @self.app.delete("/api/bots/{bot_id}/memories", dependencies=[Depends(admin_required)])
        async def delete_bot_memory(bot_id: str, memory: Dict[str, str]):
            """Delete a memory from a bot."""
            if not self.bot_manager:
                raise HTTPException(status_code=500, detail="Bot manager not available")

            content = memory.get("content", "").strip()
            if not content:
                raise HTTPException(status_code=400, detail="Memory content is required")

            try:
                bot = self.bot_manager.bots.get(bot_id)
                if not bot:
                    raise HTTPException(status_code=404, detail=f"Bot '{bot_id}' not found")

                server_manager = getattr(bot, "server_manager", None)
                if not server_manager:
                    raise HTTPException(status_code=500, detail="Server manager not available")

                server_db = server_manager.get_server_db("default")

                # Delete fact from database
                success = server_db.delete_fact(content)

                if success:
                    return {"message": "Memory deleted successfully"}
                else:
                    raise HTTPException(status_code=404, detail="Memory not found")

            except Exception as e:
                log.error("Failed to delete bot memory", extra={"bot_id": bot_id, "error": str(e)})
                raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")

        # Template management endpoints
        @self.app.get("/api/templates", dependencies=[Depends(admin_required)])
        async def get_templates():
            """Get all available bot templates."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")
            templates = self.config_manager.get_config("bot_templates") or {}
            return {"templates": templates}

        @self.app.get("/api/templates/{template_id}", dependencies=[Depends(admin_required)])
        async def get_template(template_id: str):
            """Get a specific template configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")
            templates = self.config_manager.get_config("bot_templates") or {}
            template = templates.get(template_id)
            if not template:
                raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
            return {"template": template}

        @self.app.post("/api/templates/{template_id}", dependencies=[Depends(admin_required)])
        async def create_template(template_id: str, template_config: Dict[str, Any]):
            """Create a new template configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            templates = self.config_manager.get_config("bot_templates") or {}
            if template_id in templates:
                raise HTTPException(status_code=409, detail=f"Template '{template_id}' already exists")

            templates[template_id] = template_config
            self.config_manager.set_config("bot_templates", templates)
            await self._broadcast_update("template_created", {"template_id": template_id})
            return {"message": f"Template '{template_id}' created successfully"}

        @self.app.put("/api/templates/{template_id}", dependencies=[Depends(admin_required)])
        async def update_template(template_id: str, updates: Dict[str, Any]):
            """Update a template configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            templates = self.config_manager.get_config("bot_templates") or {}
            if template_id not in templates:
                raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

            templates[template_id].update(updates)
            self.config_manager.set_config("bot_templates", templates)
            await self._broadcast_update("template_updated", {"template_id": template_id})
            return {"message": f"Template '{template_id}' updated successfully"}

        @self.app.delete("/api/templates/{template_id}", dependencies=[Depends(admin_required)])
        async def delete_template(template_id: str):
            """Delete a template configuration."""
            if not self.config_manager:
                raise HTTPException(status_code=500, detail="Configuration manager not available")

            templates = self.config_manager.get_config("bot_templates") or {}
            if template_id not in templates:
                raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

            del templates[template_id]
            self.config_manager.set_config("bot_templates", templates)
            await self._broadcast_update("template_deleted", {"template_id": template_id})
            return {"message": f"Template '{template_id}' deleted successfully"}

        # WebSocket endpoint for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()

            # Skip authentication for now to debug connection issues
            # TODO: Re-enable authentication once connection is stable
            # user = websocket.session.get("user") if hasattr(websocket, "session") else None
            # trusted = os.getenv("TRUSTED_USER_IDS", "").split(",")
            # trusted = [t.strip() for t in trusted if t.strip()]
            # if not user or user.get("id") not in trusted:
            #     await websocket.close()
            #     return

            self.websocket_connections.append(websocket)
            log.info("WebSocket connection established", extra={"total_connections": len(self.websocket_connections)})

            try:
                # Send initial connection confirmation
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "connection_established",
                            "timestamp": datetime.now().isoformat(),
                            "data": {"message": "Connected to GrugThink API"},
                        }
                    )
                )

                # Send periodic heartbeat to keep connection alive
                last_heartbeat = datetime.now()

                while True:
                    try:
                        # Wait for data with a timeout for heartbeat
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                        # Handle ping/pong for connection health
                        if data == "ping":
                            await websocket.send_text("pong")
                        else:
                            # Echo back other messages
                            await websocket.send_text(
                                json.dumps(
                                    {"type": "echo", "timestamp": datetime.now().isoformat(), "data": {"message": data}}
                                )
                            )

                    except asyncio.TimeoutError:
                        # Send heartbeat if no data received
                        now = datetime.now()
                        if (now - last_heartbeat).seconds >= 30:
                            await websocket.send_text(
                                json.dumps(
                                    {"type": "heartbeat", "timestamp": now.isoformat(), "data": {"status": "alive"}}
                                )
                            )
                            last_heartbeat = now

            except WebSocketDisconnect:
                log.info(
                    "WebSocket connection closed", extra={"remaining_connections": len(self.websocket_connections) - 1}
                )
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
            except Exception as e:
                log.error("WebSocket error", extra={"error": str(e)})
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)

    async def _start_bot_task(self, bot_id: str):
        """Background task to start a bot."""
        try:
            success = await self.bot_manager.start_bot(bot_id)
            await self._broadcast_update(
                "bot_status_changed", {"bot_id": bot_id, "status": "running" if success else "error"}
            )
        except Exception as e:
            log.error("Error in start bot task", extra={"bot_id": bot_id, "error": str(e)})

    async def _stop_bot_task(self, bot_id: str):
        """Background task to stop a bot."""
        try:
            success = await self.bot_manager.stop_bot(bot_id)
            await self._broadcast_update(
                "bot_status_changed", {"bot_id": bot_id, "status": "stopped" if success else "error"}
            )
        except Exception as e:
            log.error("Error in stop bot task", extra={"bot_id": bot_id, "error": str(e)})

    async def _restart_bot_task(self, bot_id: str):
        """Background task to restart a bot."""
        try:
            success = await self.bot_manager.restart_bot(bot_id)
            await self._broadcast_update(
                "bot_status_changed", {"bot_id": bot_id, "status": "running" if success else "error"}
            )
        except Exception as e:
            log.error("Error in restart bot task", extra={"bot_id": bot_id, "error": str(e)})

    async def _broadcast_update(self, event_type: str, data: Dict[str, Any]):
        """Broadcast update to all WebSocket connections."""
        if not self.websocket_connections:
            return

        message = {"type": event_type, "timestamp": datetime.now().isoformat(), "data": data}

        # Remove disconnected websockets
        active_connections = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
                active_connections.append(websocket)
            except Exception:
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
    bot_manager = BotManager(config_manager=config_manager)

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
