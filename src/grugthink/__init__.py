"""
GrugThink - Adaptable Discord Personality Engine

A sophisticated multi-bot container system with personality evolution,
web dashboard management, and real-time monitoring capabilities.
"""

__version__ = "3.0.0"
__author__ = "GrugThink Contributors"
__description__ = "Adaptable Discord Personality Engine with Multi-Bot Container Support"

# Multi-bot system - core modules always available
from . import bot
from .bot_manager import BotConfig, BotInstance, BotManager
from .config_manager import ConfigManager, ConfigTemplate
from .grug_db import GrugDB
from .grug_structured_logger import get_logger
from .personality_engine import PersonalityEngine, PersonalityState, PersonalityTemplate

# Optional API server (requires uvicorn/fastapi)
try:
    from .api_server import APIServer

    _API_SERVER_AVAILABLE = True
except ImportError:
    APIServer = None
    _API_SERVER_AVAILABLE = False

__all__ = [
    "PersonalityEngine",
    "PersonalityTemplate",
    "PersonalityState",
    "GrugDB",
    "get_logger",
    "BotManager",
    "BotConfig",
    "BotInstance",
    "ConfigManager",
    "ConfigTemplate",
    "bot",
]

# Only export APIServer if available
if _API_SERVER_AVAILABLE:
    __all__.append("APIServer")
