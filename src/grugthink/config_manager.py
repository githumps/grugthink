#!/usr/bin/env python3
"""
GrugThink Dynamic Configuration Manager

Handles hot-reloading of configuration changes without container restart.
Supports environment variable manipulation and multi-bot configuration.
"""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Optional dependencies for configuration management
try:
    import yaml

    _YAML_AVAILABLE = True
except ImportError:
    yaml = None
    _YAML_AVAILABLE = False

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:
    FileSystemEventHandler = None
    Observer = None
    _WATCHDOG_AVAILABLE = False

from .grug_structured_logger import get_logger

log = get_logger(__name__)


@dataclass
class ConfigTemplate:
    """Template for creating bot configurations."""

    name: str
    description: str
    personality: Optional[str] = None  # References personality config
    force_personality: Optional[str] = None  # Deprecated, use personality instead
    load_embedder: bool = True
    default_gemini_key: bool = True
    default_google_search: bool = False
    default_ollama: bool = False
    custom_env: Dict[str, str] = field(default_factory=dict)


if _WATCHDOG_AVAILABLE:

    class ConfigChangeHandler(FileSystemEventHandler):
        """Handles configuration file changes."""

        def __init__(self, config_manager):
            self.config_manager = config_manager

        def on_modified(self, event):
            if not event.is_directory and event.src_path == self.config_manager.config_file:
                self.config_manager._reload_config()
else:

    class ConfigChangeHandler:
        """Stub class when watchdog is not available."""

        def __init__(self, config_manager):
            pass


class ConfigManager:
    """Manages dynamic configuration with hot-reloading."""

    def __init__(self, config_file: str = "grugthink_config.yaml"):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}
        self.change_callbacks: List[Callable] = []
        self._lock = threading.Lock()

        # File watcher for hot-reloading (if watchdog available)
        if _WATCHDOG_AVAILABLE:
            self.observer = Observer()
            self.handler = ConfigChangeHandler(self)
        else:
            self.observer = None
            self.handler = ConfigChangeHandler(self)

        # Built-in templates
        self.templates = self._create_default_templates()

        # Load initial configuration
        self._load_config()
        self._start_watching()

        log.info("ConfigManager initialized", extra={"config_file": config_file, "templates": len(self.templates)})

    def _create_default_templates(self) -> Dict[str, ConfigTemplate]:
        """Create default bot configuration templates."""
        return {
            "pure_grug": ConfigTemplate(
                name="Pure Grug",
                description="Caveman personality only, no evolution",
                force_personality="grug",
                load_embedder=True,
            ),
            "pure_big_rob": ConfigTemplate(
                name="Pure Big Rob",
                description="norf FC lad personality only, no evolution",
                force_personality="big_rob",
                load_embedder=True,
            ),
            "evolution_bot": ConfigTemplate(
                name="Evolution Bot",
                description="Adaptive personality that evolves per server",
                force_personality=None,  # No forced personality
                load_embedder=True,
            ),
            "lightweight_grug": ConfigTemplate(
                name="Lightweight Grug",
                description="Grug personality without semantic search",
                force_personality="grug",
                load_embedder=False,
            ),
            "multi_personality": ConfigTemplate(
                name="Multi-Personality",
                description="Random personality selection per server",
                force_personality=None,
                load_embedder=True,
            ),
            "ollama_bot": ConfigTemplate(
                name="Ollama Bot",
                description="Uses local Ollama instead of Gemini",
                force_personality=None,
                load_embedder=True,
                default_gemini_key=False,
                default_ollama=True,
                custom_env={"OLLAMA_URLS": "http://localhost:11434", "OLLAMA_MODELS": "llama3.2:3b"},
            ),
        }

    def _load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
                        if _YAML_AVAILABLE:
                            data = yaml.safe_load(f) or {}
                        else:
                            log.warning("YAML config file found but PyYAML not available, skipping")
                            data = {}
                    else:
                        data = json.load(f)

                # Load external personalities from personalities directory
                external_personalities = self._load_external_personalities()
                if external_personalities:
                    # Merge external personalities with inline ones, external take precedence
                    inline_personalities = data.get("personalities", {})
                    data["personalities"] = {**inline_personalities, **external_personalities}
                    log.info("Loaded external personalities", extra={"count": len(external_personalities)})

                with self._lock:
                    self.config_data = data
                    self.env_vars = data.get("environment", {})

                log.info(
                    "Configuration loaded", extra={"config_file": self.config_file, "env_vars": len(self.env_vars)}
                )
            else:
                # Create default configuration
                self._create_default_config()

        except Exception as e:
            log.error("Failed to load configuration", extra={"error": str(e), "config_file": self.config_file})
            self._create_default_config()

    def _load_external_personalities(self) -> Dict[str, Any]:
        """Load personality configurations from personalities directory."""
        personalities = {}
        personalities_dir = "personalities"

        if not os.path.exists(personalities_dir):
            log.debug("Personalities directory not found", extra={"dir": personalities_dir})
            return personalities

        try:
            for filename in os.listdir(personalities_dir):
                if filename.endswith((".yaml", ".yml")):
                    personality_id = filename.replace(".yaml", "").replace(".yml", "")
                    file_path = os.path.join(personalities_dir, filename)

                    try:
                        with open(file_path, "r") as f:
                            if _YAML_AVAILABLE:
                                personality_data = yaml.safe_load(f)
                                if personality_data:
                                    personalities[personality_id] = personality_data
                                    log.debug("Loaded personality", extra={"id": personality_id, "file": file_path})
                            else:
                                log.warning(
                                    "YAML personality file found but PyYAML not available", extra={"file": file_path}
                                )
                    except Exception as e:
                        log.error("Failed to load personality file", extra={"file": file_path, "error": str(e)})

        except Exception as e:
            log.error("Failed to scan personalities directory", extra={"error": str(e), "dir": personalities_dir})

        return personalities

    def _create_default_config(self):
        """Create default configuration file."""
        default_config = {
            "version": "2.0",
            "description": "GrugThink Multi-Bot Configuration",
            "global_settings": {
                "log_level": "INFO",
                "data_directory": "./data",
                "enable_monitoring": True,
                "api_rate_limit": 100,
            },
            "environment": {"GRUGBOT_VARIANT": "prod", "LOG_LEVEL": "INFO"},
            "api_keys": {
                "gemini": {"primary": "", "secondary": "", "fallback": ""},
                "google_search": {"api_key": "", "cse_id": ""},
                "discord": {"tokens": []},
            },
            "bot_templates": {template_id: asdict(template) for template_id, template in self.templates.items()},
        }

        try:
            with open(self.config_file, "w") as f:
                if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
                    if _YAML_AVAILABLE:
                        yaml.safe_dump(default_config, f, indent=2, default_flow_style=False)
                    else:
                        # Fall back to JSON if yaml not available
                        json.dump(default_config, f, indent=2)
                else:
                    json.dump(default_config, f, indent=2)

            with self._lock:
                self.config_data = default_config
                self.env_vars = default_config.get("environment", {})

            log.info("Created default configuration", extra={"config_file": self.config_file})

        except Exception as e:
            log.error("Failed to create default configuration", extra={"error": str(e)})

    def _reload_config(self):
        """Reload configuration and notify callbacks."""
        old_config = self.config_data.copy()
        old_env = self.env_vars.copy()

        self._load_config()

        # Check for changes and notify callbacks
        if self.config_data != old_config or self.env_vars != old_env:
            log.info("Configuration changed, notifying callbacks", extra={"callbacks": len(self.change_callbacks)})

            for callback in self.change_callbacks:
                try:
                    callback(old_config, self.config_data, old_env, self.env_vars)
                except Exception as e:
                    log.error("Error in config change callback", extra={"error": str(e)})

    def _start_watching(self):
        """Start watching configuration file for changes."""
        if not _WATCHDOG_AVAILABLE or self.observer is None:
            log.info("File watching disabled (watchdog not available)")
            return

        try:
            config_dir = os.path.dirname(os.path.abspath(self.config_file))
            self.observer.schedule(self.handler, config_dir, recursive=False)
            self.observer.start()

            log.info("Started configuration file watcher", extra={"directory": config_dir})

        except Exception as e:
            log.error("Failed to start file watcher", extra={"error": str(e)})

    def add_change_callback(self, callback: Callable):
        """Add callback for configuration changes."""
        self.change_callbacks.append(callback)

    def get_config(self, key: str = None) -> Any:
        """Get configuration value."""
        with self._lock:
            if key is None:
                return self.config_data.copy()

            keys = key.split(".")
            data = self.config_data

            for k in keys:
                if isinstance(data, dict) and k in data:
                    data = data[k]
                else:
                    return None

            return data

    def set_config(self, key: str, value: Any):
        """Set configuration value."""
        with self._lock:
            keys = key.split(".")
            data = self.config_data

            # Navigate to parent
            for k in keys[:-1]:
                if k not in data:
                    data[k] = {}
                data = data[k]

            # Set value
            data[keys[-1]] = value

            # Save to file
            self._save_config()

    def get_env_var(self, key: str, default: str = None) -> str:
        """Get environment variable with fallback to config."""
        # First check actual environment
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value

        # Then check config environment section
        with self._lock:
            return self.env_vars.get(key, default)

    def set_env_var(self, key: str, value: str):
        """Set environment variable in config (not actual env)."""
        with self._lock:
            self.env_vars[key] = value
            self.config_data["environment"] = self.env_vars
            self._save_config()

    def get_api_keys(self, service: str) -> Dict[str, Any]:
        """Get API keys for a service."""
        return self.get_config(f"api_keys.{service}") or {}

    def set_api_key(self, service: str, key_name: str, value: str):
        """Set API key for a service."""
        current_keys = self.get_api_keys(service)
        current_keys[key_name] = value
        self.set_config(f"api_keys.{service}", current_keys)

    def add_discord_token(self, name: str, token: str) -> str:
        """Add a Discord bot token."""
        tokens = self.get_config("api_keys.discord.tokens") or []

        token_entry = {
            "id": str(len(tokens) + 1),
            "name": name,
            "token": token,
            "added_at": time.time(),
            "active": True,
        }

        tokens.append(token_entry)
        self.set_config("api_keys.discord.tokens", tokens)

        log.info("Added Discord token", extra={"name": name, "token_id": token_entry["id"]})

        return token_entry["id"]

    def remove_discord_token(self, token_id: str) -> bool:
        """Remove a Discord bot token by ID."""
        tokens = self.get_config("api_keys.discord.tokens") or []
        for idx, token in enumerate(tokens):
            if token["id"] == token_id:
                tokens.pop(idx)
                self.set_config("api_keys.discord.tokens", tokens)
                log.info("Removed Discord token", extra={"token_id": token_id})
                return True
        return False

    def get_discord_tokens(self) -> List[Dict[str, Any]]:
        """Get all Discord tokens."""
        return self.get_config("api_keys.discord.tokens") or []

    def get_available_discord_token(self) -> Optional[str]:
        """Get an available Discord token."""
        tokens = self.get_discord_tokens()
        for token_data in tokens:
            if token_data.get("active", True):
                return token_data["token"]
        return None

    def get_discord_token_by_id(self, token_id: str) -> Optional[str]:
        """Get a Discord token by its ID."""
        tokens = self.get_discord_tokens()
        for token_data in tokens:
            if token_data["id"] == token_id:
                return token_data["token"]
        return None

    def get_template(self, template_id: str) -> Optional[ConfigTemplate]:
        """Get bot configuration template."""
        if template_id in self.templates:
            return self.templates[template_id]

        # Check if it's in the config file
        template_data = self.get_config(f"bot_templates.{template_id}")
        if template_data:
            return ConfigTemplate(**template_data)

        return None

    def get_personality(self, personality_id: str) -> Optional[Dict[str, Any]]:
        """Get personality configuration by ID."""
        personalities = self.get_config("personalities") or {}
        return personalities.get(personality_id)

    def list_personalities(self) -> Dict[str, Dict[str, Any]]:
        """List all available personalities."""
        return self.get_config("personalities") or {}

    def add_personality(self, personality_id: str, personality_config: Dict[str, Any]) -> bool:
        """Add a new personality configuration."""
        personalities = self.get_config("personalities") or {}
        personalities[personality_id] = personality_config
        self.set_config("personalities", personalities)
        log.info("Added personality", extra={"personality_id": personality_id})
        return True

    def update_personality(self, personality_id: str, updates: Dict[str, Any]) -> bool:
        """Update a personality configuration."""
        personalities = self.get_config("personalities") or {}
        if personality_id in personalities:
            personalities[personality_id].update(updates)
            self.set_config("personalities", personalities)
            log.info("Updated personality", extra={"personality_id": personality_id})
            return True
        return False

    def remove_personality(self, personality_id: str) -> bool:
        """Remove a personality configuration."""
        personalities = self.get_config("personalities") or {}
        if personality_id in personalities:
            del personalities[personality_id]
            self.set_config("personalities", personalities)
            log.info("Removed personality", extra={"personality_id": personality_id})
            return True
        return False

    def list_templates(self) -> Dict[str, ConfigTemplate]:
        """List all available templates."""
        templates = self.templates.copy()

        # Add templates from config file
        config_templates = self.get_config("bot_templates") or {}
        for template_id, template_data in config_templates.items():
            if template_id not in templates:
                try:
                    templates[template_id] = ConfigTemplate(**template_data)
                except Exception as e:
                    log.error("Invalid template in config", extra={"template_id": template_id, "error": str(e)})

        return templates

    def create_bot_env(self, template_id: str, discord_token: str, **overrides) -> Dict[str, str]:
        """Create environment variables for a bot from template."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")

        env = {}

        # Base environment from config
        env.update(self.env_vars)

        # Core bot settings
        env["DISCORD_TOKEN"] = discord_token
        env["LOAD_EMBEDDER"] = str(template.load_embedder)

        # Set personality (prefer new 'personality' field over deprecated 'force_personality')
        personality = getattr(template, "personality", None) or template.force_personality
        if personality:
            env["FORCE_PERSONALITY"] = personality

        # API keys
        if template.default_gemini_key:
            gemini_keys = self.get_api_keys("gemini")
            primary_key = gemini_keys.get("primary")
            if primary_key:
                env["GEMINI_API_KEY"] = primary_key

        if template.default_google_search:
            google_keys = self.get_api_keys("google_search")
            if google_keys.get("api_key"):
                env["GOOGLE_API_KEY"] = google_keys["api_key"]
            if google_keys.get("cse_id"):
                env["GOOGLE_CSE_ID"] = google_keys["cse_id"]

        if template.default_ollama:
            env["OLLAMA_URLS"] = self.get_env_var("OLLAMA_URLS", "http://localhost:11434")
            env["OLLAMA_MODELS"] = self.get_env_var("OLLAMA_MODELS", "llama3.2:3b")

        # Custom environment from template
        env.update(template.custom_env)

        # Apply overrides
        env.update(overrides)

        return env

    def _save_config(self):
        """Save current configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                if self.config_file.endswith(".yaml") or self.config_file.endswith(".yml"):
                    if _YAML_AVAILABLE:
                        yaml.safe_dump(self.config_data, f, indent=2, default_flow_style=False)
                    else:
                        json.dump(self.config_data, f, indent=2)
                else:
                    json.dump(self.config_data, f, indent=2)

            log.debug("Configuration saved", extra={"config_file": self.config_file})

        except Exception as e:
            log.error("Failed to save configuration", extra={"error": str(e)})

    def export_config(self, filename: str = None) -> str:
        """Export current configuration to file."""
        if filename is None:
            timestamp = int(time.time())
            if _YAML_AVAILABLE:
                filename = f"grugthink_config_backup_{timestamp}.yaml"
            else:
                filename = f"grugthink_config_backup_{timestamp}.json"

        try:
            with open(filename, "w") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    if _YAML_AVAILABLE:
                        yaml.safe_dump(self.config_data, f, indent=2, default_flow_style=False)
                    else:
                        json.dump(self.config_data, f, indent=2)
                else:
                    json.dump(self.config_data, f, indent=2)

            log.info("Configuration exported", extra={"filename": filename})

            return filename

        except Exception as e:
            log.error("Failed to export configuration", extra={"error": str(e), "filename": filename})
            raise

    def import_config(self, filename: str):
        """Import configuration from file."""
        try:
            with open(filename, "r") as f:
                if filename.endswith(".yaml") or filename.endswith(".yml"):
                    if _YAML_AVAILABLE:
                        imported_config = yaml.safe_load(f)
                    else:
                        raise ValueError("YAML config file provided but PyYAML not available")
                else:
                    imported_config = json.load(f)

            with self._lock:
                self.config_data = imported_config
                self.env_vars = imported_config.get("environment", {})
                self._save_config()

            log.info("Configuration imported", extra={"filename": filename})

            # Notify callbacks
            self._reload_config()

        except Exception as e:
            log.error("Failed to import configuration", extra={"error": str(e), "filename": filename})
            raise

    def add_bot_config(self, bot_config: Dict[str, Any]) -> str:
        """Add a bot configuration to the YAML config."""
        bot_configs = self.get_config("bot_configs") or {}
        bot_id = bot_config["bot_id"]
        bot_configs[bot_id] = bot_config
        self.set_config("bot_configs", bot_configs)
        log.info("Added bot configuration", extra={"bot_id": bot_id})
        return bot_id

    def remove_bot_config(self, bot_id: str) -> bool:
        """Remove a bot configuration."""
        bot_configs = self.get_config("bot_configs") or {}
        if bot_id in bot_configs:
            del bot_configs[bot_id]
            self.set_config("bot_configs", bot_configs)
            log.info("Removed bot configuration", extra={"bot_id": bot_id})
            return True
        return False

    def update_bot_config(self, bot_id: str, updates: Dict[str, Any]) -> bool:
        """Update a bot configuration."""
        bot_configs = self.get_config("bot_configs") or {}
        if bot_id in bot_configs:
            bot_configs[bot_id].update(updates)
            self.set_config("bot_configs", bot_configs)
            log.info("Updated bot configuration", extra={"bot_id": bot_id})
            return True
        return False

    def get_bot_config(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get a bot configuration by ID."""
        bot_configs = self.get_config("bot_configs") or {}
        return bot_configs.get(bot_id)

    def list_bot_configs(self) -> Dict[str, Dict[str, Any]]:
        """List all bot configurations."""
        return self.get_config("bot_configs") or {}

    def migrate_from_json(self, json_file: str) -> Dict[str, str]:
        """Migrate bot configurations from JSON file to YAML config.

        Returns a mapping of old bot IDs to Discord token IDs for reference.
        """
        if not os.path.exists(json_file):
            log.warning("JSON config file not found", extra={"file": json_file})
            return {}

        try:
            with open(json_file, "r") as f:
                json_configs = json.load(f)

            migration_map = {}
            migrated_configs = {}

            for json_config in json_configs:
                bot_id = json_config["bot_id"]
                discord_token = json_config["discord_token"]

                # Find matching token ID in YAML config
                token_id = None
                for token_data in self.get_discord_tokens():
                    if token_data["token"] == discord_token:
                        token_id = token_data["id"]
                        break

                if not token_id:
                    # Token not found, add it
                    token_name = f"Migrated - {json_config.get('name', bot_id)}"
                    token_id = self.add_discord_token(token_name, discord_token)

                # Create new bot config structure
                new_config = {
                    "bot_id": bot_id,
                    "name": json_config.get("name", f"Bot {bot_id}"),
                    "discord_token_id": token_id,
                    "template_id": self._determine_template_from_json(json_config),
                    "force_personality": json_config.get("force_personality"),
                    "load_embedder": json_config.get("load_embedder", True),
                    "log_level": json_config.get("log_level", "INFO"),
                    "data_dir": json_config.get("data_dir", "./data"),
                    "trusted_user_ids": json_config.get("trusted_user_ids"),
                    "status": json_config.get("status", "stopped"),
                    "created_at": json_config.get("created_at", time.time()),
                    # Override fields for any custom API keys
                    "override_gemini_key": json_config.get("gemini_api_key"),
                    "override_google_api_key": json_config.get("google_api_key"),
                    "override_google_cse_id": json_config.get("google_cse_id"),
                    "override_ollama_urls": json_config.get("ollama_urls"),
                    "override_ollama_models": json_config.get("ollama_models"),
                }

                # Remove None values to keep config clean
                new_config = {k: v for k, v in new_config.items() if v is not None}

                migrated_configs[bot_id] = new_config
                migration_map[bot_id] = token_id

                log.info(
                    "Migrated bot config",
                    extra={"bot_id": bot_id, "token_id": token_id, "template": new_config.get("template_id")},
                )

            # Save all migrated configs
            self.set_config("bot_configs", migrated_configs)

            log.info("Migration completed", extra={"migrated_count": len(migrated_configs), "source_file": json_file})

            return migration_map

        except Exception as e:
            log.error("Migration failed", extra={"error": str(e), "file": json_file})
            raise

    def _determine_template_from_json(self, json_config: Dict[str, Any]) -> str:
        """Determine the best template based on old JSON config."""
        force_personality = json_config.get("force_personality")
        load_embedder = json_config.get("load_embedder", True)
        has_ollama = json_config.get("ollama_urls") or json_config.get("ollama_models")

        if has_ollama:
            return "ollama_bot"
        elif force_personality == "grug":
            return "pure_grug" if load_embedder else "lightweight_grug"
        elif force_personality == "big_rob":
            return "pure_big_rob"
        elif force_personality is None:
            return "evolution_bot"
        else:
            return "evolution_bot"  # Default fallback

    def stop(self):
        """Stop the configuration manager."""
        if self.observer and hasattr(self.observer, "is_alive") and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

        log.info("ConfigManager stopped")
