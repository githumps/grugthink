#!/usr/bin/env python3
"""GrugThink – Adaptable Personality Engine for Discord
An AI bot that develops unique personalities for each Discord server.
Supports organic personality evolution and self-naming capabilities.
Run with PYTHONUNBUFFERED so every print is flushed immediately.
"""

import asyncio
import hashlib
import os
import re
import signal
import sys
import time
import traceback
from collections import OrderedDict

import discord
import requests
from discord import app_commands
from discord.ext import commands

from . import config
from .grug_db import GrugServerManager
from .grug_structured_logger import get_logger
from .personality_engine import PersonalityEngine

log = get_logger(__name__)


class LRUCache:
    """Memory-bounded LRU cache with automatic expiration."""

    def __init__(self, max_size=100, ttl_seconds=300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()

    def get(self, key):
        if key not in self.cache:
            return None
        timestamp, value = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            return None
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return value

    def put(self, key, value):
        now = time.time()
        if key in self.cache:
            self.cache[key] = (now, value)
            self.cache.move_to_end(key)
        else:
            self.cache[key] = (now, value)
            if len(self.cache) > self.max_size:
                # Remove oldest entry
                self.cache.popitem(last=False)


# Cache and rate limiting
response_cache = LRUCache(max_size=100, ttl_seconds=300)
user_cooldowns = {}

# Cross-bot interaction tracking
cross_bot_mentions = LRUCache(max_size=200, ttl_seconds=600)  # Track mentions for 10 minutes
# Track if bots have already fired back at each other for a given conversation
cross_bot_responses = LRUCache(max_size=200, ttl_seconds=600)
cross_bot_topic_responses = LRUCache(max_size=100, ttl_seconds=1800)  # Store bot responses by topic for 30 minutes

# Initialize Server Manager and Personality Engine
server_manager = GrugServerManager(config.DB_PATH)

_personality_engine_instance = None


def get_personality_engine():
    global _personality_engine_instance
    if _personality_engine_instance is None:
        # For single-bot mode, respect FORCE_PERSONALITY environment variable
        forced_personality = os.getenv("FORCE_PERSONALITY")
        _personality_engine_instance = PersonalityEngine("personalities.db", forced_personality=forced_personality)
    return _personality_engine_instance


def _reset_personality_engine():
    global _personality_engine_instance
    _personality_engine_instance = None


def store_bot_response_for_cross_reference(response: str, personality_name: str):
    """Store bot response for other bots to reference when topics are mentioned."""
    if not personality_name or not response:
        return

    # Extract key topics/keywords from the response
    response_lower = response.lower()
    topics = []

    # Common topics that bots might argue about
    topic_keywords = {
        "carling": ["carling", "beer", "drink", "pint"],
        "beer": ["beer", "carling", "drink", "pint", "ale"],
        "food": ["pie", "potato", "shepherd", "meat", "food", "grub"],
        "pie": ["pie", "potato", "shepherd", "meat", "food"],
        "fight": ["fight", "beat", "strong", "tough", "battle"],
        "football": ["football", "footy", "norf", "fc", "team"],
        "caveman": ["caveman", "mammoth", "cave", "stone", "hunt"],
    }

    # Check which topics this response relates to
    for topic, keywords in topic_keywords.items():
        if any(keyword in response_lower for keyword in keywords):
            topics.append(topic)

    # Store the response under each relevant topic
    for topic in topics:
        topic_key = f"{topic}:{personality_name.lower()}"
        topic_data = {"bot_name": personality_name, "response": response, "timestamp": time.time(), "topic": topic}
        cross_bot_topic_responses.put(topic_key, topic_data)

        log.info(
            "Stored bot response for cross-reference",
            extra={"bot_name": personality_name, "topic": topic, "response": response[:100]},
        )


def _pair_key(name_a: str, name_b: str, server_id: str, channel_id: str) -> str:
    """Return a normalized key for tracking two bots interacting."""
    names = sorted([name_a.lower(), name_b.lower()])
    return f"{server_id}:{channel_id}:{names[0]}:{names[1]}"


def generate_shit_talk(target_name: str, style: str) -> str:
    """Return a short insult aimed at another bot."""
    import random

    target = target_name.strip()

    if style == "caveman":
        caveman_insults = [
            f"{target} weak. Grug strongest!",
            f"{target} soft like mammoth belly!",
            f"Grug smash {target} with big rock!",
            f"{target} no can hunt. Grug better!",
            f"{target} brain small like pebble!",
            f"Grug eat {target} for breakfast!",
            f"{target} weaker than sick woolly!",
            f"Grug club {target} into next cave!",
            f"{target} no know fire. Grug know fire!",
            f"{target} run from sabertooth. Grug fight sabertooth!",
            f"Grug throw {target} into tar pit!",
            f"{target} hide in cave like scared rabbit!",
        ]
        return random.choice(caveman_insults)

    elif style == "british_working_class":
        british_insults = [
            f"oi {target}, pipe down ya muppet",
            f"{target}'s a right tosser, innit",
            f"get stuffed {target}, you plonker",
            f"{target} couldn't organize a piss-up in a brewery",
            f"shut it {target}, you absolute weapon",
            f"{target}'s thick as two short planks",
            f"do one {target}, ya numpty",
            f"{target} talks pure waffle, simple as",
            f"wind your neck in {target}, you melt",
            f"{target}'s got more issues than a newsstand",
            f"bore off {target}, you proper div",
            f"{target} couldn't find water in a swimming pool",
        ]
        return random.choice(british_insults)

    elif style == "adaptive":
        adaptive_insults = [
            f"{target} clearly clueless",
            f"{target} needs a reality check",
            f"{target} talking nonsense again",
            f"{target} should stick to lurking",
            f"{target}'s logic is fundamentally flawed",
            f"{target} missed the point entirely",
            f"{target} needs to recalibrate their thinking",
            f"{target}'s analysis is rather shallow",
            f"{target} should consider alternative perspectives",
            f"{target}'s reasoning lacks nuance",
            f"{target} demonstrates poor comprehension",
            f"{target} fails to grasp the complexity here",
        ]
        return random.choice(adaptive_insults)

    # Default fallback insults for unknown styles
    default_insults = [
        f"{target} clearly clueless",
        f"{target} needs a reality check",
        f"{target} talking nonsense again",
        f"{target} should stick to lurking",
    ]
    return random.choice(default_insults)


def get_server_db(interaction_or_guild_id):
    """Get the appropriate database for a Discord interaction or guild ID."""
    if hasattr(interaction_or_guild_id, "guild_id"):
        # It's a Discord interaction
        guild_id = interaction_or_guild_id.guild_id
    elif hasattr(interaction_or_guild_id, "guild") and interaction_or_guild_id.guild:
        # It's a Discord message with guild
        guild_id = interaction_or_guild_id.guild.id
    else:
        # It's a guild ID directly, or a DM
        guild_id = interaction_or_guild_id

    return server_manager.get_server_db(guild_id)


def log_initial_settings():
    import logging

    log_level = getattr(logging, config.LOG_LEVEL_STR, logging.INFO)

    # Configure logging with timestamps and better formatting
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    log.info("GrugThink personality engine is starting up...")
    if config.USE_GEMINI:
        log.info("Using Gemini for generation", extra={"model": config.GEMINI_MODEL})
    else:
        log.info("Using Ollama for generation", extra={"urls": config.OLLAMA_URLS, "models": config.OLLAMA_MODELS})
    if config.CAN_SEARCH:
        log.info("Google Search is enabled.")
    else:
        log.warning("Google Search is disabled. Bot cannot learn new things from the internet.")
    if config.TRUSTED_USER_IDS:
        log.info("Trusted users configured", extra={"users": config.TRUSTED_USER_IDS})
    else:
        log.warning("No trusted users configured. /learn command will be disabled for all.")
    log.info("Log level set", extra={"level": config.LOG_LEVEL_STR})


# log_initial_settings() # Moved to individual bot startup to avoid conflicts in multi-bot mode


def build_personality_context(statement: str, server_db, server_id: str, personality_engine) -> str:
    """Build personality context with semantically relevant lore for this server."""
    personality = personality_engine.get_personality(server_id)

    # Get base context from personality
    base_context = personality.base_context

    # Find lore relevant to the current statement from this server's knowledge
    relevant_lore = server_db.search_facts(statement, k=5)

    if relevant_lore:
        # Format lore based on personality style
        if personality.response_style == "caveman":
            bot_name = personality.chosen_name or personality.name
            lore_context = f"\n\n{bot_name} also remember these things: {' '.join(relevant_lore)}"
        elif personality.response_style == "british_working_class":
            lore_context = f"\n\nI remember these bits: {' '.join(relevant_lore)}"
        else:
            lore_context = f"\n\nI also know: {' '.join(relevant_lore)}"

        return base_context + lore_context

    return base_context


def build_personality_prompt(
    statement: str, server_db, server_id: str, personality_engine, external_info: str = ""
) -> str:
    """Build complete personality verification prompt with lore and external info."""
    personality_context = build_personality_context(statement, server_db, server_id, personality_engine)

    # Add external info using personality engine
    if external_info:
        personality_context = personality_engine.get_context_prompt(server_id, external_info)

    return f"""{personality_context}

You MUST be 100% ACCURATE about real world facts.

ABSOLUTE RULES:
1. Real world facts = ALWAYS TRUE if factually correct.
2. George Washington WAS president - this is FACT, say TRUE.
3. Animals, science, history, geography = be TRUTHFUL.
4. Stay in character but BE ACCURATE about facts.
5. Format: TRUE/FALSE - character explanation.
6. End with <END>.

CRITICAL: Be factually accurate. Only use your personality for HOW you explain, not WHAT you conclude.

Statement: "{statement}"
Answer:"""


# ---------------------------------------------------------------------------
# 1. Early sanity checks (handled in config.py)
# ---------------------------------------------------------------------------
# All environment variables are now loaded and validated in config.py
# and fatal errors will exit the program there.
# ---------------------------------------------------------------------------


# Discord client setup
intents = discord.Intents.default()
intents.message_content = True

session = requests.Session()


def clean_statement(text: str) -> str:
    text = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", text)
    text = re.sub(r"<@[!&]?[0-9]+>", "", text)
    text = re.sub(r"<#[0-9]+>", "", text)
    text = " ".join(text.split())
    return text.strip()


def get_cache_key(statement: str, bot_id: str | None = None) -> str:
    """Return a cache key unique to the statement and bot."""
    key_source = f"{bot_id}:{statement}" if bot_id else statement
    return hashlib.md5(key_source.encode()).hexdigest()


def is_rate_limited(user_id: int, bot_id: str = None) -> bool:
    """Check if user is rate limited for a specific bot or globally."""
    now = time.time()

    if bot_id:
        # Check per-bot rate limiting (allows multiple bots to respond)
        key = f"{user_id}:{bot_id}"
        if key in user_cooldowns and now - user_cooldowns[key] < 5:
            return True
        user_cooldowns[key] = now
        return False
    else:
        # Global rate limiting (legacy behavior)
        if user_id in user_cooldowns and now - user_cooldowns[user_id] < 5:
            return True
        user_cooldowns[user_id] = now
        return False


def extract_lore_from_response(response: str, server_db, personality_name: str = None):
    """Extract and save new lore to bot's brain."""
    try:
        # Extract all sentences from the response after TRUE/FALSE verdict
        # Split on TRUE/FALSE and take everything after the dash
        parts = re.split(r"\b(TRUE|FALSE)\s*[-–—:]\s*", response, flags=re.IGNORECASE)
        if len(parts) >= 3:
            # Extract the explanation part after TRUE/FALSE -
            explanation = parts[2].strip()
            lore_sentences = re.findall(r"[^.!?]+[.!?]", explanation)
        else:
            # Fallback: extract all sentences
            lore_sentences = re.findall(r"[^.!?]+[.!?]", response)

        for sentence in lore_sentences:
            sentence_clean = sentence.strip().capitalize()
            if sentence_clean and len(sentence_clean) > 15:
                # Skip generic/filler phrases but allow meaningful content
                skip_phrases = ["simple as", "nuff said", "end of", "innit"]
                if any(sentence_clean.lower().strip().endswith(skip) for skip in skip_phrases):
                    continue
                if sentence_clean.lower().strip() in skip_phrases:
                    continue

                # Skip if it's just filler words
                filler_words = [
                    "the",
                    "a",
                    "an",
                    "is",
                    "are",
                    "was",
                    "were",
                    "of",
                    "for",
                    "to",
                    "in",
                    "on",
                    "it",
                    "that",
                    "this",
                ]
                meaningful_words = [word for word in sentence_clean.lower().split() if word not in filler_words]
                if len(meaningful_words) < 3:
                    continue

                # Add context about who said it if we have personality name
                if personality_name and personality_name.lower() not in sentence_clean.lower():
                    contextual_sentence = f"{personality_name} says: {sentence_clean}"
                else:
                    contextual_sentence = sentence_clean

                if server_db.add_fact(contextual_sentence):
                    log.info("New lore learned", extra={"lore": contextual_sentence})
                else:
                    log.info("Lore already known", extra={"lore": contextual_sentence})
    except Exception as e:
        log.error("Error extracting lore", extra={"error": str(e)})


def search_google(query: str) -> str:
    """Search Google for information if Grug doesn't know the answer."""
    if not config.CAN_SEARCH:
        return ""
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": config.GOOGLE_API_KEY, "cx": config.GOOGLE_CSE_ID, "q": query}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get("items", [])
            snippets = [item.get("snippet", "") for item in results[:3]]
            return " ".join(snippets).replace("\n", "")
    except Exception as e:
        log.error("Google search failed", extra={"error": str(e)})
    return ""


def get_cross_bot_personality_info(server_id: str = "global") -> dict:
    """Get personality information about other bots in the system."""
    personality_info = {}
    try:
        # In multi-bot mode, try to access bot manager for personality information
        from .main import get_bot_manager

        bot_manager = get_bot_manager()
        if bot_manager:
            for bot_id, bot_instance in bot_manager.bots.items():
                try:
                    # Get the bot's personality for this server
                    personality = bot_instance.personality_engine.get_personality(server_id)
                    bot_name = personality.chosen_name or personality.name

                    # Create a recognizable key from bot name
                    personality_info[bot_id] = {
                        "name": bot_name,
                        "response_style": personality.response_style,
                        "personality_traits": personality.personality_traits,
                        "background_elements": personality.background_elements,
                    }

                    # Also add by name for easier lookup
                    name_key = bot_name.lower().replace(" ", "_")
                    personality_info[name_key] = personality_info[bot_id]

                except Exception as e:
                    log.debug("Could not access bot personality", extra={"bot_id": bot_id, "error": str(e)})
    except ImportError:
        # Not in multi-bot mode, provide fallback personality info for known bots
        personality_info.update(
            {
                "grug": {
                    "name": "Grug",
                    "response_style": "caveman",
                    "personality_traits": {"strength": "physical", "intelligence": "primitive"},
                    "background_elements": ["lives in cave", "hunts mammoth", "uses primitive tools"],
                },
                "big_rob": {
                    "name": "Big Rob",
                    "response_style": "british_working_class",
                    "personality_traits": {"strength": "opiniated", "intelligence": "street_smart"},
                    "background_elements": ["British working class", "football fan", "strong opinions"],
                },
            }
        )
    except Exception as e:
        log.debug("Could not access bot manager", extra={"error": str(e)})

    return personality_info


def get_cross_bot_memories(statement: str, server_id: str, current_bot_id: str = None) -> str:
    """Get memories from other bots in the same server for context."""
    try:
        # Import here to avoid circular imports

        # Try to access other bot databases if available
        # This will only work in multi-bot mode where we can access the bot manager
        cross_bot_context = ""

        # Get personality information about other bots
        personality_info = get_cross_bot_personality_info(server_id)

        # For now, we'll implement a simple system that looks for other bot data directories
        # In a more advanced implementation, this could access the BotManager directly
        data_base_dir = (
            os.path.dirname(server_manager.base_db_path) if hasattr(server_manager, "base_db_path") else "./data"
        )

        if os.path.exists(data_base_dir):
            for bot_dir in os.listdir(data_base_dir):
                bot_data_path = os.path.join(data_base_dir, bot_dir)
                if os.path.isdir(bot_data_path) and bot_dir != current_bot_id:
                    facts_db_path = os.path.join(bot_data_path, "facts.db")
                    if os.path.exists(facts_db_path):
                        try:
                            # Create a temporary server manager to access other bot's memories
                            temp_manager = GrugServerManager(facts_db_path)
                            temp_db = temp_manager.get_server_db(server_id)
                            relevant_facts = temp_db.search_facts(statement, k=2)
                            if relevant_facts:
                                bot_info = ""
                                # Add personality context if available
                                # Try multiple ways to match bot identity
                                matched_personality = None

                                # Try exact bot_dir match first
                                if bot_dir in personality_info:
                                    matched_personality = personality_info[bot_dir]
                                else:
                                    # Try matching by common bot name patterns
                                    bot_dir_lower = bot_dir.lower()
                                    for key in personality_info:
                                        if (
                                            key in bot_dir_lower
                                            or bot_dir_lower in key
                                            or (key == "grug" and "grug" in bot_dir_lower)
                                            or (key == "big_rob" and ("rob" in bot_dir_lower or "big" in bot_dir_lower))
                                        ):
                                            matched_personality = personality_info[key]
                                            break

                                if matched_personality:
                                    style = matched_personality.get("response_style", "")
                                    traits = matched_personality.get("personality_traits", {})
                                    bot_name = matched_personality.get("name", bot_dir)

                                    if style == "caveman":
                                        bot_info = f" ({bot_name} - caveman who fights sabertooths and hunts mammoth)"
                                    elif style == "british_working_class":
                                        bot_info = f" ({bot_name} - British working class lad with football opinions)"
                                    elif style == "adaptive":
                                        bot_info = f" ({bot_name} - adaptive bot that learns and evolves)"
                                    else:
                                        bot_info = f" ({bot_name})"

                                    # Add specific traits if they exist
                                    if traits:
                                        key_traits = []
                                        if "strength" in traits:
                                            key_traits.append(f"strength: {traits['strength']}")
                                        if "intelligence" in traits:
                                            key_traits.append(f"smarts: {traits['intelligence']}")
                                        if key_traits:
                                            bot_info += f" [{', '.join(key_traits)}]"

                                cross_bot_context += f" {bot_dir}{bot_info} remembers: {' '.join(relevant_facts[:2])}"
                        except Exception as e:
                            log.debug(
                                "Could not access cross-bot memories", extra={"bot_dir": bot_dir, "error": str(e)}
                            )

        return cross_bot_context.strip()
    except Exception as e:
        log.debug("Cross-bot memory access failed", extra={"error": str(e)})
        return ""


def query_model(
    statement: str, server_db, server_id: str, personality_engine, current_bot_id: str = None
) -> str | None:
    """Unified query function for both Ollama and Gemini."""
    if not statement or len(statement.strip()) < 3:
        return "FALSE - Statement too short to verify."

    cache_key = get_cache_key(statement, current_bot_id)
    cached_response = response_cache.get(cache_key)
    if cached_response:
        log.info("Using cached response", extra={"cache_key": cache_key})
        return cached_response

    clean_stmt = clean_statement(statement)
    if len(clean_stmt) > 1000:
        clean_stmt = clean_stmt[:1000]

    # Check internal knowledge first from this server's database
    relevant_lore = server_db.search_facts(clean_stmt, k=1)
    external_info = ""
    cross_bot_memories = ""

    # Get memories from other bots in the same server
    if current_bot_id:
        cross_bot_memories = get_cross_bot_memories(clean_stmt, server_id, current_bot_id)

    if not relevant_lore:  # If no strong internal signal, search web
        log.info("No strong memory for statement, searching web", extra={"statement": clean_stmt})
        external_info = search_google(clean_stmt)

    # Combine external info with cross-bot memories
    combined_external_info = external_info
    if cross_bot_memories:
        combined_external_info += f" Other bots know: {cross_bot_memories}"

    prompt_text = build_personality_prompt(clean_stmt, server_db, server_id, personality_engine, combined_external_info)

    # Track personality evolution
    personality_engine.evolve_personality(server_id, clean_stmt)

    # Get personality name for lore extraction
    personality = personality_engine.get_personality(server_id)
    personality_name = personality.chosen_name or personality.name

    if config.USE_GEMINI:
        return query_gemini_api(prompt_text, cache_key, server_db, personality_name)
    else:
        return query_ollama_api(prompt_text, cache_key, server_db, personality_name)


def query_ollama_api(prompt_text: str, cache_key: str, server_db=None, personality_name: str = None) -> str | None:
    log.info("Querying Ollama with integrated prompt")
    for idx, url in enumerate(config.OLLAMA_URLS):
        raw_model = config.OLLAMA_MODELS[idx] if idx < len(config.OLLAMA_MODELS) else config.OLLAMA_MODELS[0]
        try:
            payload = {
                "model": raw_model,
                "prompt": prompt_text,
                "stream": False,
                "options": {"num_predict": 80, "temperature": 0.3, "top_p": 0.5, "stop": ["<END>"]},
            }
            r = session.post(f"{url}/api/generate", json=payload, timeout=60)
            if r.status_code == 200:
                response = r.json().get("response", "").strip()
                validated = validate_and_process_response(response, cache_key, server_db, personality_name)
                if validated:
                    return validated
        except requests.exceptions.RequestException as e:
            log.error("Ollama request failed", extra={"url": url, "error": str(e)})
    return None


def query_gemini_api(prompt_text: str, cache_key: str, server_db=None, personality_name: str = None) -> str | None:
    log.info("Querying Gemini with integrated prompt")
    try:
        import google.generativeai as genai

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=config.GEMINI_MODEL)
        resp = model.generate_content(prompt_text, stream=False, generation_config={"temperature": 0.3, "top_p": 0.5})
        validated = validate_and_process_response(resp.text, cache_key, server_db, personality_name)
        if validated:
            return validated
    except Exception as e:
        log.error("Gemini API call failed", extra={"error": str(e)})
    return None


def validate_and_process_response(
    response: str, cache_key: str, server_db=None, personality_name: str = None
) -> str | None:
    """Centralized response validation and processing."""
    response = response.split("<END>")[0].strip()
    log.info("Raw response from model", extra={"response": response[:200]})

    true_match = re.search(r"\bTRUE\b", response, re.IGNORECASE)
    false_match = re.search(r"\bFALSE\b", response, re.IGNORECASE)

    if true_match or false_match:
        verdict = "TRUE" if true_match else "FALSE"
        pattern = rf"\b{verdict}\b\s*[-–—:]?\s*(.*)"
        match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            explanation = re.sub(r"\s+", " ", match.group(1).strip())
            if explanation:
                full_response = f"{verdict} - {explanation}"
                if not full_response.rstrip().endswith((".", "!", "?")):
                    full_response += "."

                if len(full_response.split()) >= 4 and len(full_response) >= 20:
                    response_cache.put(cache_key, full_response)
                    if server_db:
                        extract_lore_from_response(full_response, server_db, personality_name)

                    # Store bot response for cross-bot awareness
                    store_bot_response_for_cross_reference(full_response, personality_name)

                    log.info("Validated response", extra={"response": full_response[:200]})
                    return full_response
    log.warning("Invalid format, discarding", extra={"response": response[:200]})
    return None


class GrugThinkBot(commands.Cog):
    def __init__(self, client: commands.Bot, bot_instance):
        self.client = client
        self.bot_instance = bot_instance
        self.personality_engine = bot_instance.personality_engine
        self.server_manager = getattr(bot_instance, "server_manager", None)
        self.tree = client.tree

    def get_server_db(self, interaction_or_guild_id):
        """Get the appropriate database for a Discord interaction or guild ID."""
        if self.server_manager:
            # Multi-bot mode: use the server manager
            if hasattr(interaction_or_guild_id, "guild_id"):
                # It's a Discord interaction
                guild_id = interaction_or_guild_id.guild_id
            elif hasattr(interaction_or_guild_id, "guild") and interaction_or_guild_id.guild:
                # It's a Discord message with guild
                guild_id = interaction_or_guild_id.guild.id
            else:
                # It's a guild ID directly, or a DM
                guild_id = interaction_or_guild_id
            return self.server_manager.get_server_db(guild_id)
        else:
            # Single-bot mode: fallback to the global server manager
            return get_server_db(interaction_or_guild_id)

    def get_bot_id(self):
        """Get the bot ID for logging purposes."""
        return getattr(self.bot_instance.config, "bot_id", "unknown-bot")

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("Logged in to Discord", extra={"user": str(self.client.user)})
        try:
            await self.tree.sync()
            log.info("Commands synced")
        except Exception as e:
            log.error("Failed to sync commands", extra={"error": str(e)})

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize personality when joining a new server."""
        server_id = str(guild.id)
        personality = self.personality_engine.get_personality(server_id)

        log.info(
            "Joined new server, personality initialized",
            extra={"guild_id": server_id, "guild_name": guild.name, "personality_name": personality.name},
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages and detect name mentions for auto-verification."""
        # Ignore messages from bots, except for Markov bots and other GrugThink bots
        is_markov_bot = False
        if message.author.bot:
            is_markov_bot = "markov" in message.author.name.lower()

        # Get personality for this server
        server_id = str(message.guild.id) if message.guild else "dm"
        personality = self.personality_engine.get_personality(server_id)
        bot_name = personality.chosen_name or personality.name

        # Detect and store cross-bot mentions from all messages
        mentioned_bots = self.detect_cross_bot_mentions(message)
        if mentioned_bots:
            message_author = message.author.display_name or message.author.name
            if message.author.bot:
                self.store_cross_bot_mention(message_author, mentioned_bots, message)
            else:
                self.store_cross_bot_mention(f"user:{message_author}", mentioned_bots, message)

        # If another bot explicitly talks about this bot, fire back with a short insult once
        if (
            message.author.bot
            and self.is_bot_mentioned(message.content, bot_name)
            and message.author != self.client.user
            and not is_markov_bot
        ):
            channel_id = str(message.channel.id)
            other_name = message.author.display_name or message.author.name
            pair_key = _pair_key(other_name, bot_name, server_id, channel_id)
            pair_state = cross_bot_responses.get(pair_key)
            if pair_state is None:
                pair_state = {other_name.lower(): True, bot_name.lower(): False}
            else:
                pair_state[other_name.lower()] = True

            if not pair_state.get(bot_name.lower(), False):
                pair_state[bot_name.lower()] = True
                cross_bot_responses.put(pair_key, pair_state)
                insult = generate_shit_talk(other_name, personality.response_style)
                # Wait a moment to let the other bot finish their main response first
                await asyncio.sleep(2)
                await message.channel.send(insult)
            else:
                cross_bot_responses.put(pair_key, pair_state)
            return

        if message.author.bot and not is_markov_bot:
            # Ignore other bot messages that don't mention us
            return
        # Process commands first
        await self.client.process_commands(message)

        # Check if bot name is mentioned in the message by a human
        if self.is_bot_mentioned(message.content, bot_name):
            if is_rate_limited(message.author.id, self.get_bot_id()):
                if personality.response_style == "caveman":
                    await message.channel.send("Grug need rest. Wait little.", delete_after=5)
                elif personality.response_style == "british_working_class":
                    await message.channel.send("slow down mate, too much carlin last nite, simple as", delete_after=5)
                else:
                    await message.channel.send("Please wait a moment.", delete_after=5)
                return
            await self.handle_auto_verification(message, server_id, personality, mentioned_bots)

    def is_bot_mentioned(self, content: str, bot_name: str) -> bool:
        """Check if the bot name is mentioned in the message content."""
        content_lower = content.lower()
        bot_name_lower = bot_name.lower()

        # Check for direct name mentions (word boundaries)
        if re.search(rf"\b{re.escape(bot_name_lower)}\b", content_lower):
            return True

        # Check for @mentions of the bot user
        if self.client.user and f"<@{self.client.user.id}>" in content:
            return True
        if self.client.user and f"<@!{self.client.user.id}>" in content:
            return True

        return False

    def detect_cross_bot_mentions(self, message) -> list:
        """Detect mentions of other bot names in a message."""
        mentioned_bots = []
        content_lower = message.content.lower()

        # Common bot names to look for (more comprehensive list)
        bot_names = ["grug", "big rob", "rob", "adaptive", "markov", "grugthink"]

        # Also check for variations
        name_variations = {
            "big rob": ["big rob", "bigrob", "rob"],
            "grug": ["grug", "grugthink"],
            "adaptive": ["adaptive", "adapt"],
            "markov": ["markov"],
        }

        for bot_name in bot_names:
            # Check primary name
            if re.search(rf"\b{re.escape(bot_name.lower())}\b", content_lower):
                mentioned_bots.append(bot_name)
                continue

            # Check variations
            for main_name, variations in name_variations.items():
                if bot_name == main_name:
                    for variation in variations:
                        if re.search(rf"\b{re.escape(variation.lower())}\b", content_lower):
                            mentioned_bots.append(bot_name)
                            break

        return list(set(mentioned_bots))  # Remove duplicates

    def store_cross_bot_mention(self, mentioning_source: str, mentioned_bot_names: list, message):
        """Store cross-bot mentions for later reference."""
        server_id = str(message.guild.id) if message.guild else "dm"
        channel_id = str(message.channel.id)

        for mentioned_bot in mentioned_bot_names:
            # Normalize the mentioned bot name
            mentioned_bot_normalized = mentioned_bot.lower()

            # Create a simpler key structure for easier retrieval
            mention_key = f"{server_id}:{channel_id}:{mentioned_bot_normalized}:{int(time.time())}"
            mention_data = {
                "mentioning_bot": mentioning_source,
                "mentioned_bot": mentioned_bot_normalized,
                "message_content": message.content,
                "message_id": message.id,
                "channel_id": channel_id,
                "server_id": server_id,
                "timestamp": time.time(),
            }
            cross_bot_mentions.put(mention_key, mention_data)

            log.info(
                "Cross-bot mention stored",
                extra={
                    "mentioning_source": mentioning_source,
                    "mentioned_bot": mentioned_bot_normalized,
                    "server_id": server_id,
                    "channel_id": channel_id,
                    "mention_key": mention_key,
                    "message_content": message.content[:100],
                    "total_mentions_cached": len(cross_bot_mentions.cache),
                },
            )

    def get_recent_mentions_about_bot(self, bot_name: str, server_id: str, channel_id: str) -> list:
        """Get recent mentions about this bot from other sources."""
        mentions = []
        bot_name_lower = bot_name.lower()

        # Also check for name variations
        name_to_check = [bot_name_lower]
        if "rob" in bot_name_lower:
            name_to_check.extend(["big rob", "rob"])
        elif "grug" in bot_name_lower:
            name_to_check.extend(["grug", "grugthink"])

        log.info(
            "Checking for cross-bot mentions",
            extra={
                "bot_name": bot_name,
                "names_to_check": name_to_check,
                "server_id": server_id,
                "channel_id": channel_id,
                "cache_size": len(cross_bot_mentions.cache),
            },
        )

        # Check all stored mentions for ones about this bot
        for key, mention_data in cross_bot_mentions.cache.items():
            if mention_data and isinstance(mention_data, tuple):
                _, data = mention_data
                mentioned_bot = data.get("mentioned_bot", "").lower()

                if (
                    any(name in mentioned_bot or mentioned_bot in name for name in name_to_check)
                    and data.get("server_id") == server_id
                    and data.get("channel_id") == channel_id
                ):
                    mentions.append(data)
                    log.info(
                        "Found cross-bot mention",
                        extra={
                            "mentioned_bot": data.get("mentioned_bot"),
                            "mentioning_source": data.get("mentioning_bot"),
                            "content": data.get("message_content", "")[:100],
                        },
                    )

        # Sort by timestamp, most recent first
        mentions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return mentions[:3]  # Return up to 3 most recent mentions

    def get_cross_bot_topic_context(self, statement: str, current_bot_name: str) -> str:
        """Get context from other bots about topics mentioned in the statement."""
        statement_lower = statement.lower()
        current_bot_lower = current_bot_name.lower()

        # Topics to check for
        topic_keywords = {
            "carling": ["carling", "beer", "drink", "pint"],
            "beer": ["beer", "carling", "drink", "pint", "ale"],
            "food": ["pie", "potato", "shepherd", "meat", "food", "grub"],
            "pie": ["pie", "potato", "shepherd", "meat", "food"],
            "fight": ["fight", "beat", "strong", "tough", "battle"],
            "football": ["football", "footy", "norf", "fc", "team"],
            "caveman": ["caveman", "mammoth", "cave", "stone", "hunt"],
        }

        # Check which topics this statement relates to
        relevant_topics = []
        for topic, keywords in topic_keywords.items():
            if any(keyword in statement_lower for keyword in keywords):
                relevant_topics.append(topic)

        if not relevant_topics:
            return ""

        # Look for responses from other bots about these topics
        other_bot_responses = []
        for topic in relevant_topics:
            for key, topic_data in cross_bot_topic_responses.cache.items():
                if topic_data and isinstance(topic_data, tuple):
                    _, data = topic_data
                    if data.get("topic") == topic and data.get("bot_name", "").lower() != current_bot_lower:
                        other_bot_responses.append(data)

        if not other_bot_responses:
            return ""

        # Sort by timestamp and get the most recent response
        other_bot_responses.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        latest_response = other_bot_responses[0]

        other_bot_name = latest_response.get("bot_name", "another bot")
        other_response = latest_response.get("response", "")

        log.info(
            "Found cross-bot topic context",
            extra={
                "current_bot": current_bot_name,
                "other_bot": other_bot_name,
                "topic": latest_response.get("topic"),
                "other_response": other_response[:100],
            },
        )

        # Format context based on current bot's personality
        if "grug" in current_bot_lower:
            return f" Grug hear {other_bot_name} say: '{other_response[:80]}'. "
        elif "rob" in current_bot_lower:
            return f" Heard {other_bot_name} chattin: '{other_response[:80]}' - "
        else:
            return f" {other_bot_name} said: '{other_response[:80]}'. "

    async def store_bot_response_after_edit(self, message, response_content: str, server_id: str):
        """Store bot response for cross-bot detection after message edit."""
        try:
            # Create a mock message object for the cross-bot detection
            # This simulates what would happen if this was a new message
            bot_name = self.personality_engine.get_personality(server_id).chosen_name or "Bot"

            # Check if this response mentions other bots
            mentioned_bots = self.detect_cross_bot_mentions_in_text(response_content)
            if mentioned_bots:
                # Create a simplified message data structure
                class MockMessage:
                    def __init__(self, content, channel, guild, author_name):
                        self.content = content
                        self.channel = channel
                        self.guild = guild
                        self.id = message.id  # Use the actual message ID
                        self.author_name = author_name

                mock_message = MockMessage(response_content, message.channel, message.guild, bot_name)

                # Store the cross-bot mention using the bot as the mentioning source
                self.store_cross_bot_mention(bot_name, mentioned_bots, mock_message)

                log.info(
                    "Stored cross-bot mentions from edited bot response",
                    extra={
                        "bot_id": self.get_bot_id(),
                        "bot_name": bot_name,
                        "mentioned_bots": mentioned_bots,
                        "response_content": response_content[:100],
                    },
                )
        except Exception as e:
            log.error(
                "Failed to store bot response after edit",
                extra={"bot_id": self.get_bot_id(), "error": str(e), "response_content": response_content[:100]},
            )

    def detect_cross_bot_mentions_in_text(self, text: str) -> list:
        """Detect mentions of other bot names in text content."""
        mentioned_bots = []
        content_lower = text.lower()

        # Common bot names to look for (more comprehensive list)
        bot_names = ["grug", "big rob", "rob", "adaptive", "markov", "grugthink"]

        # Also check for variations
        name_variations = {
            "big rob": ["big rob", "bigrob", "rob"],
            "grug": ["grug", "grugthink"],
            "adaptive": ["adaptive", "adapt"],
            "markov": ["markov"],
        }

        for bot_name in bot_names:
            # Check primary name
            if re.search(rf"\b{re.escape(bot_name.lower())}\b", content_lower):
                mentioned_bots.append(bot_name)
                continue

            # Check variations
            for main_name, variations in name_variations.items():
                if bot_name == main_name:
                    for variation in variations:
                        if re.search(rf"\b{re.escape(variation.lower())}\b", content_lower):
                            mentioned_bots.append(bot_name)
                            break

        return list(set(mentioned_bots))  # Remove duplicates

    async def handle_auto_verification(self, message, server_id: str, personality, mentioned_bots=None):
        """Handle automatic verification when bot name is mentioned."""
        # Log if this is a bot interaction
        is_markov_bot = message.author.bot and "markov" in message.author.name.lower()
        is_other_grugthink_bot = message.author.bot and not is_markov_bot

        if is_markov_bot:
            log.info(
                "Markov bot interaction",
                extra={
                    "markov_bot_name": message.author.name,
                    "server_id": server_id,
                    "message_length": len(message.content),
                },
            )
        elif is_other_grugthink_bot:
            log.info(
                "GrugThink bot interaction",
                extra={
                    "bot_id": self.get_bot_id(),
                    "other_bot_name": message.author.name,
                    "server_id": server_id,
                    "message_length": len(message.content),
                },
            )

        # Clean the message content for verification
        clean_content = clean_statement(message.content)

        # Remove bot name mentions to get the actual statement
        bot_name = personality.chosen_name or personality.name
        clean_content = re.sub(rf"\b{re.escape(bot_name.lower())}\b", "", clean_content, flags=re.IGNORECASE)

        # Remove @mentions
        if self.client.user:
            clean_content = clean_content.replace(f"<@{self.client.user.id}>", "")
            clean_content = clean_content.replace(f"<@!{self.client.user.id}>", "")

        # Clean up extra whitespace
        clean_content = re.sub(r"\s+", " ", clean_content).strip()

        # Prepare contextual info from other bots (only for human messages that
        # don't mention other bots)
        cross_bot_context = ""
        mentioned_bots = mentioned_bots or []

        if not message.author.bot and not mentioned_bots:
            topic_context = self.get_cross_bot_topic_context(clean_content, bot_name)

            if topic_context:
                cross_bot_context = topic_context
                log.info(
                    "Adding cross-bot topic context to response",
                    extra={
                        "bot_id": self.get_bot_id(),
                        "topic_context": topic_context[:50],
                    },
                )

        # Skip if the remaining content is too short or just punctuation
        if len(clean_content) < 5 or not re.search(r"[a-zA-Z]", clean_content):
            # Respond with a personality-appropriate acknowledgment
            if is_markov_bot:
                # Special responses for Markov bot interactions
                if personality.response_style == "caveman":
                    response = f"{bot_name} hear robot friend call!"
                elif personality.response_style == "british_working_class":
                    response = "alright robot mate, wot you sayin, nuff said"
                else:
                    response = "Hello fellow bot! What would you like me to verify?"
            elif is_other_grugthink_bot:
                # Special responses for other GrugThink bot interactions
                other_bot_name = message.author.display_name or message.author.name
                if personality.response_style == "caveman":
                    response = f"{bot_name} hear {other_bot_name} call! What {other_bot_name} want know?"
                elif personality.response_style == "british_working_class":
                    response = f"alright {other_bot_name} mate, wot you after then, nuff said"
                else:
                    response = f"Hello {other_bot_name}! What would you like me to verify?"
            else:
                # Normal human responses - include cross-bot context if available
                if personality.response_style == "caveman":
                    response = f"{bot_name} hear you call!{cross_bot_context}"
                elif personality.response_style == "british_working_class":
                    response = f"wot you want mate, nuff said{cross_bot_context}"
                else:
                    response = f"I'm listening. What would you like me to verify?{cross_bot_context}"

            await message.channel.send(response)
            return

        # Send thinking message
        bot_name_display = personality.chosen_name or personality.name
        if is_markov_bot:
            if personality.response_style == "caveman":
                thinking_msg = f"{bot_name_display} think about robot friend words..."
            elif personality.response_style == "british_working_class":
                thinking_msg = f"{bot_name_display} checkin wot robot mate said..."
            else:
                thinking_msg = f"{bot_name_display} analyzing bot input..."
        elif is_other_grugthink_bot:
            other_bot_name = message.author.display_name or message.author.name
            if personality.response_style == "caveman":
                thinking_msg = f"{bot_name_display} think about {other_bot_name} words..."
            elif personality.response_style == "british_working_class":
                thinking_msg = f"{bot_name_display} checkin wot {other_bot_name} said..."
            else:
                thinking_msg = f"{bot_name_display} considering {other_bot_name}'s statement..."
        else:
            thinking_msg = f"{bot_name_display} thinking..."

        thinking_message = await message.channel.send(thinking_msg)

        try:
            # Get the server-specific database
            server_db = self.get_server_db(message.guild.id if message.guild else "dm")

            # Run verification in executor to avoid blocking
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, query_model, clean_content, server_db, server_id, self.personality_engine, self.get_bot_id()
            )

            if result:
                # Apply personality style to response
                styled_result = self.personality_engine.get_response_with_style(server_id, result)

                # Add cross-bot context if available
                if cross_bot_context:
                    styled_result = styled_result + cross_bot_context

                # Delete the thinking message and post final response as new message
                # This ensures Discord triggers on_message for cross-bot detection
                await thinking_message.delete()
                await message.channel.send(styled_result)

                log.info(
                    "Auto-verification completed",
                    extra={
                        "bot_id": self.get_bot_id(),
                        "user_id": str(message.author.id),
                        "server_id": server_id,
                        "statement_length": len(clean_content),
                        "result_length": len(styled_result),
                        "is_markov_bot": is_markov_bot,
                        "is_grugthink_bot": is_other_grugthink_bot,
                        "author_name": message.author.name if (is_markov_bot or is_other_grugthink_bot) else None,
                    },
                )
            else:
                # Use personality-appropriate error message
                error_msg = self.personality_engine.get_error_message(server_id)
                await thinking_message.delete()
                await message.channel.send(f"❓ {error_msg}")

        except Exception as exc:
            log.error(
                "Auto-verification error",
                extra={
                    "bot_id": self.get_bot_id(),
                    "error": str(exc),
                    "user_id": str(message.author.id),
                    "server_id": server_id,
                },
            )
            # Use personality for error message
            error_msg = self.personality_engine.get_error_message(server_id)
            await thinking_message.delete()
            await message.channel.send(f"💥 {error_msg}")

    @app_commands.command(name="verify", description="Verify the truthfulness of the previous message.")
    async def verify(self, interaction: discord.Interaction):
        if is_rate_limited(interaction.user.id, self.get_bot_id()):
            await interaction.response.send_message("Slow down! Wait a few seconds.", ephemeral=True)
            return

        channel = interaction.channel
        history = [m async for m in channel.history(limit=25) if not m.author.bot and m.content.strip()]

        if not history:
            await interaction.response.send_message("No user message to verify.", ephemeral=True)
            return

        target = history[0].content
        log.info(
            "Verify command initiated",
            extra={"bot_id": self.get_bot_id(), "user_id": str(interaction.user.id), "target_length": len(target)},
        )

        await interaction.response.defer(ephemeral=False)  # Tell Discord the bot is thinking

        # Get server ID and personality info
        server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
        personality = self.personality_engine.get_personality(server_id)
        thinking_msg = f"{personality.chosen_name or personality.name} thinking..."

        msg = await interaction.followup.send(thinking_msg, ephemeral=False)

        try:
            # Get the server-specific database
            server_db = self.get_server_db(interaction)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, query_model, target, server_db, server_id, self.personality_engine, self.get_bot_id()
            )

            if result:
                # Apply personality style to response
                styled_result = self.personality_engine.get_response_with_style(server_id, result)
                await msg.edit(content=f"Verification: {styled_result}")
            else:
                error_msg = self.personality_engine.get_error_message(server_id)
                await msg.edit(content=error_msg)

        except Exception as exc:
            log.error(
                "Slash command error",
                extra={"error": str(exc), "traceback": traceback.format_exc()},
            )
            # Use personality for error message
            error_msg = self.personality_engine.get_error_message(server_id)
            await msg.edit(content=f"💥 {error_msg}")

    @app_commands.command(name="learn", description="Teach the bot a new fact.")
    @app_commands.describe(fact="The fact to learn.")
    async def learn(self, interaction: discord.Interaction, fact: str):
        await interaction.response.defer(ephemeral=True)  # Tell Discord bot is thinking

        # Get personality info
        server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
        personality = self.personality_engine.get_personality(server_id)
        bot_name = personality.chosen_name or personality.name

        if interaction.user.id not in config.TRUSTED_USER_IDS:
            if personality.response_style == "caveman":
                await interaction.followup.send(f"You not trusted to teach {bot_name}.", ephemeral=True)
            elif personality.response_style == "british_working_class":
                await interaction.followup.send("oi oi, you aint on the list mate, end of", ephemeral=True)
            else:
                await interaction.followup.send("You're not authorized to teach me facts.", ephemeral=True)
            return

        if len(fact.strip()) < 5:
            if personality.response_style == "caveman":
                await interaction.followup.send("Fact too short to be useful.", ephemeral=True)
            elif personality.response_style == "british_working_class":
                await interaction.followup.send("wot? thats it? need more than that mate, simple as", ephemeral=True)
            else:
                await interaction.followup.send("Please provide a more detailed fact.", ephemeral=True)
            return

        # Get the server-specific database
        server_db = self.get_server_db(interaction)
        if server_db.add_fact(fact):
            log.info(
                "Fact learned",
                extra={
                    "bot_id": self.get_bot_id(),
                    "user_id": str(interaction.user.id),
                    "fact_length": len(fact),
                    "server_id": str(interaction.guild_id),
                },
            )
            if personality.response_style == "caveman":
                await interaction.followup.send(f"{bot_name} learn: {fact}", ephemeral=True)
            elif personality.response_style == "british_working_class":
                await interaction.followup.send(f"sorted mate, learnt that: {fact}, nuff said", ephemeral=True)
            else:
                await interaction.followup.send(f"Learned: {fact}", ephemeral=True)
        else:
            if personality.response_style == "caveman":
                await interaction.followup.send(f"{bot_name} already know that.", ephemeral=True)
            elif personality.response_style == "british_working_class":
                await interaction.followup.send("already know that one, simple as", ephemeral=True)
            else:
                await interaction.followup.send("I already know that.", ephemeral=True)

    @app_commands.command(name="what-know", description="See all the facts the bot knows.")
    async def what_know(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Tell Discord bot is thinking

        # Get personality info
        server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
        personality = self.personality_engine.get_personality(server_id)
        bot_name = personality.chosen_name or personality.name

        # Get the server-specific database
        server_db = self.get_server_db(interaction)
        all_facts = server_db.get_all_facts()

        if not all_facts:
            if personality.response_style == "caveman":
                await interaction.followup.send(f"{bot_name} know nothing in this cave.", ephemeral=True)
            elif personality.response_style == "british_working_class":
                await interaction.followup.send("dont know nuffin yet mate, simple as", ephemeral=True)
            else:
                await interaction.followup.send("I don't know any facts yet.", ephemeral=True)
            return

        # Create a Discord embed for better formatting
        server_name = interaction.guild.name if interaction.guild else "DM"

        if personality.response_style == "caveman":
            title = f"{bot_name}'s Memories ({server_name})"
            description = f"{bot_name} knows {len(all_facts)} things in this cave:"
        elif personality.response_style == "british_working_class":
            title = f"wot i know ({server_name})"
            description = f"got {len(all_facts)} fings in me ed, nuff said:"
        else:
            title = f"Knowledge Base ({server_name})"
            description = f"I know {len(all_facts)} facts:"

        # Discord embed field value limit is 1024 characters
        MAX_FIELD_LENGTH = 950  # Leave margin for formatting
        MAX_FACT_LENGTH = 100  # Max length per individual fact

        # Build fact list that respects Discord embed limits
        fact_lines = []
        current_length = 0
        facts_shown = 0

        for i, fact in enumerate(all_facts):
            # Truncate long facts
            display_fact = fact[:MAX_FACT_LENGTH] + "..." if len(fact) > MAX_FACT_LENGTH else fact
            fact_line = f"{i + 1}. {display_fact}"

            # Check if adding this fact would exceed Discord's embed field limit
            new_length = current_length + len(fact_line) + 1  # +1 for newline
            if new_length > MAX_FIELD_LENGTH:
                break

            fact_lines.append(fact_line)
            current_length = new_length
            facts_shown += 1

        # Create the fact list string
        fact_list = "\n".join(fact_lines)

        # Add truncation notice if not all facts were shown
        if facts_shown < len(all_facts):
            remaining = len(all_facts) - facts_shown
            truncation_notice = f"\n\n... and {remaining} more fact{'s' if remaining != 1 else ''}"

            # Ensure truncation notice fits within limit
            if len(fact_list) + len(truncation_notice) <= MAX_FIELD_LENGTH:
                fact_list += truncation_notice
            else:
                # Remove last fact to make room for truncation notice
                if fact_lines:
                    fact_lines.pop()
                    facts_shown -= 1
                    remaining = len(all_facts) - facts_shown
                    fact_list = (
                        "\n".join(fact_lines) + f"\n\n... and {remaining} more fact{'s' if remaining != 1 else ''}"
                    )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
        )

        # Use appropriate field name based on whether facts were truncated
        field_name = "Facts" if facts_shown == len(all_facts) else f"Facts (Showing {facts_shown} of {len(all_facts)})"
        embed.add_field(name=field_name, value=fact_list or "No facts to display", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Shows what the bot can do.")
    async def help_command(self, interaction: discord.Interaction):
        # Get personality info
        server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
        personality = self.personality_engine.get_personality(server_id)
        bot_name = personality.chosen_name or personality.name

        if personality.response_style == "caveman":
            title = f"{bot_name} Help"
            description = f"Here are the things {bot_name} can do:"
        elif personality.response_style == "british_working_class":
            title = "wot i can do"
            description = "right then, ere's wot im good for, simple as:"
        else:
            title = "Bot Help"
            description = "Here are my available commands:"

        embed = discord.Embed(title=title, description=description, color=discord.Color.green())
        embed.add_field(name="/verify", value="Verifies the truthfulness of the last message.", inline=False)
        embed.add_field(name="/learn", value="Teach me a new fact (trusted users only).", inline=False)
        embed.add_field(name="/what-know", value="See all the facts I know.", inline=False)
        embed.add_field(name="/personality", value="See my personality info and evolution.", inline=False)
        embed.add_field(name="/help", value="Shows this help message.", inline=False)

        # Add auto-verification feature description
        auto_verify_desc = f"Say '{bot_name}' or '@{bot_name}' in a message with a statement to auto-verify it!"
        if personality.response_style == "caveman":
            auto_verify_desc = f"Say '{bot_name}' with statement and {bot_name} check truth!"
        elif personality.response_style == "british_working_class":
            auto_verify_desc = "just say me name with summat and ill check it, simple as"

        embed.add_field(name="💬 Auto-Verification", value=auto_verify_desc, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="personality", description="Shows the bot's personality information.")
    async def personality_info(self, interaction: discord.Interaction):
        # Get personality info
        # Get personality info
        server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
        personality_info = self.personality_engine.get_personality_info(server_id)

        embed = discord.Embed(
            title=f"Personality: {personality_info['name']}",
            description="My personality and evolution status",
            color=discord.Color.purple(),
        )

        # Evolution stage descriptions
        stage_names = ["Initial", "Developing", "Established", "Evolved"]
        stage_name = stage_names[min(personality_info["evolution_stage"], 3)]

        embed.add_field(name="Name", value=personality_info["name"], inline=True)
        embed.add_field(
            name="Evolution Stage", value=f"{stage_name} ({personality_info['evolution_stage']})", inline=True
        )
        embed.add_field(name="Interactions", value=str(personality_info["interaction_count"]), inline=True)
        embed.add_field(name="Style", value=personality_info["style"], inline=True)

        if personality_info["quirks"]:
            quirks_text = ", ".join(personality_info["quirks"])
            embed.add_field(name="Developed Quirks", value=quirks_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


def main():
    log.info("Connecting to Discord gateway...")

    # Discord client setup
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="/", intents=intents)

    # Add the GrugThinkBot cog
    from unittest.mock import MagicMock

    bot_instance_mock = MagicMock()  # This will be replaced by actual instance in bot_manager
    bot_instance_mock.personality_engine = get_personality_engine()
    bot_instance_mock.server_manager = server_manager  # Use the global server manager for single bot mode

    @client.event
    async def on_ready():
        log.info("Single bot mode: Logged in to Discord", extra={"user": str(client.user)})
        try:
            await client.tree.sync()
            log.info("Single bot mode: Commands synced")
        except Exception as e:
            log.error("Single bot mode: Failed to sync commands", extra={"error": str(e)})

    @client.event
    async def on_guild_join(guild):
        server_id = str(guild.id)
        personality = get_personality_engine().get_personality(server_id)
        log.info(
            "Single bot mode: Joined new server, personality initialized",
            extra={"guild_id": server_id, "guild_name": guild.name, "personality_name": personality.name},
        )

    client.add_cog(GrugThinkBot(client, bot_instance_mock))

    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        log.info("Received signal, shutting down gracefully", extra={"signal": signum})
        server_manager.close_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        client.run(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        log.fatal("Discord bot token is invalid. Please check your config.DISCORD_TOKEN.")
        sys.exit(1)
    except discord.ConnectionClosed as e:
        log.error("Discord connection closed unexpectedly", extra={"error": str(e)})
        # Attempt to reconnect or handle gracefully
    except Exception as exc:
        log.fatal(
            "Unhandled exception in Discord client",
            extra={"error": str(exc), "traceback": traceback.format_exc()},
        )
        sys.exit(1)
    finally:
        server_manager.close_all()  # Ensure all DB connections are closed gracefully if not already by signal
        log.info("GrugThink personality engine has shut down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
