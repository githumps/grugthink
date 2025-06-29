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
    force_personality: Optional[str] = None
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

    def get_template(self, template_id: str) -> Optional[ConfigTemplate]:
        """Get bot configuration template."""
        if template_id in self.templates:
            return self.templates[template_id]

        # Check if it's in the config file
        template_data = self.get_config(f"bot_templates.{template_id}")
        if template_data:
            return ConfigTemplate(**template_data)

        return None

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

        if template.force_personality:
            env["FORCE_PERSONALITY"] = template.force_personality

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

    def stop(self):
        """Stop the configuration manager."""
        if self.observer and hasattr(self.observer, "is_alive") and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

        log.info("ConfigManager stopped")
