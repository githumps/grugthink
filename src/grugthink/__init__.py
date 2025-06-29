"""
GrugThink - Adaptable Discord Personality Engine

A sophisticated multi-bot container system with personality evolution,
web dashboard management, and real-time monitoring capabilities.
"""

__version__ = "3.0.0"
__author__ = "GrugThink Contributors"
__description__ = "Adaptable Discord Personality Engine with Multi-Bot Container Support"

# Core modules
from .api_server import APIServer

# Multi-bot system
from .bot_manager import BotConfig, BotInstance, BotManager
from .config_manager import ConfigManager, ConfigTemplate
from .grug_db import GrugDB
from .grug_structured_logger import get_logger
from .personality_engine import PersonalityEngine, PersonalityState, PersonalityTemplate

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
    "APIServer",
]
