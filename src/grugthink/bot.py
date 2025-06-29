#!/usr/bin/env python3
"""GrugThink – Adaptable Personality Engine for Discord
An AI bot that develops unique personalities for each Discord server.
Supports organic personality evolution and self-naming capabilities.
Run with PYTHONUNBUFFERED so every print is flushed immediately.
"""

import asyncio
import hashlib
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

# Initialize Server Manager and Personality Engine
server_manager = GrugServerManager(config.DB_PATH)
personality_engine = PersonalityEngine("personalities.db")


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
    logging.basicConfig(level=log_level)

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


log_initial_settings()


def build_personality_context(statement: str, server_db, server_id: str) -> str:
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


def build_personality_prompt(statement: str, server_db, server_id: str, external_info: str = "") -> str:
    """Build complete personality verification prompt with lore and external info."""
    personality_context = build_personality_context(statement, server_db, server_id)

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
client = commands.Bot(command_prefix="/", intents=intents)
tree = client.tree

session = requests.Session()


def clean_statement(text: str) -> str:
    text = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", text)
    text = re.sub(r"<@[!&]?[0-9]+>", "", text)
    text = re.sub(r"<#[0-9]+>", "", text)
    text = " ".join(text.split())
    return text.strip()


def get_cache_key(statement: str) -> str:
    return hashlib.md5(statement.encode()).hexdigest()


def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    if user_id in user_cooldowns and now - user_cooldowns[user_id] < 5:
        return True
    user_cooldowns[user_id] = now
    return False


def extract_lore_from_response(response: str, server_db):
    """Extract and save new lore to Grug's brain."""
    try:
        lore_sentences = re.findall(r"[^.!?]*\bGrug\b[^.!?]*[.!?]", response, re.IGNORECASE)
        for sentence in lore_sentences:
            sentence_clean = sentence.strip().capitalize()
            if sentence_clean and len(sentence_clean) > 15 and not sentence_clean.startswith(("TRUE", "FALSE")):
                if server_db.add_fact(sentence_clean):
                    log.info("New lore learned", extra={"lore": sentence_clean})
                else:
                    log.info("Lore already known", extra={"lore": sentence_clean})
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


def query_model(statement: str, server_db, server_id: str) -> str | None:
    """Unified query function for both Ollama and Gemini."""
    if not statement or len(statement.strip()) < 3:
        return "FALSE - Statement too short to verify."

    cache_key = get_cache_key(statement)
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
    if not relevant_lore:  # If no strong internal signal, search web
        log.info("No strong memory for statement, searching web", extra={"statement": clean_stmt})
        external_info = search_google(clean_stmt)

    prompt_text = build_personality_prompt(clean_stmt, server_db, server_id, external_info)

    # Track personality evolution
    personality_engine.evolve_personality(server_id, clean_stmt)

    if config.USE_GEMINI:
        return query_gemini_api(prompt_text, cache_key, server_db)
    else:
        return query_ollama_api(prompt_text, cache_key, server_db)


def query_ollama_api(prompt_text: str, cache_key: str, server_db=None) -> str | None:
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
                validated = validate_and_process_response(response, cache_key, server_db)
                if validated:
                    return validated
        except requests.exceptions.RequestException as e:
            log.error("Ollama request failed", extra={"url": url, "error": str(e)})
    return None


def query_gemini_api(prompt_text: str, cache_key: str, server_db=None) -> str | None:
    log.info("Querying Gemini with integrated prompt")
    try:
        import google.generativeai as genai

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=config.GEMINI_MODEL)
        resp = model.generate_content(prompt_text, stream=False, generation_config={"temperature": 0.3, "top_p": 0.5})
        validated = validate_and_process_response(resp.text, cache_key, server_db)
        if validated:
            return validated
    except Exception as e:
        log.error("Gemini API call failed", extra={"error": str(e)})
    return None


def validate_and_process_response(response: str, cache_key: str, server_db=None) -> str | None:
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
                        extract_lore_from_response(full_response, server_db)
                    log.info("Validated response", extra={"response": full_response[:200]})
                    return full_response
    log.warning("Invalid format, discarding", extra={"response": response[:200]})
    return None


@client.event
async def on_ready():
    log.info("Logged in to Discord", extra={"user": str(client.user)})
    try:
        await tree.sync()
        log.info("Commands synced")
    except Exception as e:
        log.error("Failed to sync commands", extra={"error": str(e)})


@client.event
async def on_guild_join(guild):
    """Initialize personality when joining a new server."""
    server_id = str(guild.id)
    personality = personality_engine.get_personality(server_id)

    log.info(
        "Joined new server, personality initialized",
        extra={"guild_id": server_id, "guild_name": guild.name, "personality_name": personality.name},
    )


@client.event
async def on_message(message):
    """Handle incoming messages and detect name mentions for auto-verification."""
    # Ignore messages from bots, except for Markov bots
    if message.author.bot:
        # Only allow interaction with bots whose username contains "Markov"
        if "markov" not in message.author.name.lower():
            return

    # Process commands first
    await client.process_commands(message)

    # Get personality for this server
    server_id = str(message.guild.id) if message.guild else "dm"
    personality = personality_engine.get_personality(server_id)
    bot_name = personality.chosen_name or personality.name

    # Check if bot name is mentioned in the message
    if is_bot_mentioned(message.content, bot_name):
        await handle_auto_verification(message, server_id, personality)


def is_bot_mentioned(content: str, bot_name: str) -> bool:
    """Check if the bot name is mentioned in the message content."""
    content_lower = content.lower()
    bot_name_lower = bot_name.lower()

    # Check for direct name mentions (word boundaries)
    if re.search(rf"\b{re.escape(bot_name_lower)}\b", content_lower):
        return True

    # Check for common variations and nicknames (word boundaries)
    common_names = ["grug", "grugthink"]
    for name in common_names:
        if re.search(rf"\b{name}\b", content_lower):
            return True

    # Check for "bot" but only when directly addressing (with punctuation)
    if re.search(r"\bbot[,!?.\s]", content_lower):
        return True

    # Check for @mentions of the bot user
    if client.user and f"<@{client.user.id}>" in content:
        return True
    if client.user and f"<@!{client.user.id}>" in content:
        return True

    return False


async def handle_auto_verification(message, server_id: str, personality):
    """Handle automatic verification when bot name is mentioned."""
    # Log if this is a Markov bot interaction
    is_markov_bot = message.author.bot and "markov" in message.author.name.lower()
    if is_markov_bot:
        log.info(
            "Markov bot interaction",
            extra={
                "markov_bot_name": message.author.name,
                "server_id": server_id,
                "message_length": len(message.content),
            },
        )

    # Rate limiting check
    if is_rate_limited(message.author.id):
        # Send a brief rate limit message
        if personality.response_style == "caveman":
            await message.channel.send("Grug need rest. Wait little.", delete_after=5)
        elif personality.response_style == "british_working_class":
            await message.channel.send("slow down mate, too much carlin last nite, simple as", delete_after=5)
        else:
            await message.channel.send("Please wait a moment.", delete_after=5)
        return

    # Clean the message content for verification
    clean_content = clean_statement(message.content)

    # Remove bot name mentions to get the actual statement
    bot_name = personality.chosen_name or personality.name
    for name_variant in [bot_name.lower(), "grug", "grugthink", "bot"]:
        clean_content = re.sub(rf"\b{re.escape(name_variant)}\b", "", clean_content, flags=re.IGNORECASE)

    # Remove @mentions
    if client.user:
        clean_content = clean_content.replace(f"<@{client.user.id}>", "")
        clean_content = clean_content.replace(f"<@!{client.user.id}>", "")

    # Clean up extra whitespace
    clean_content = re.sub(r"\s+", " ", clean_content).strip()

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
        else:
            # Normal human responses
            if personality.response_style == "caveman":
                response = f"{bot_name} hear you call!"
            elif personality.response_style == "british_working_class":
                response = "wot you want mate, nuff said"
            else:
                response = "I'm listening. What would you like me to verify?"

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
    else:
        thinking_msg = f"{bot_name_display} thinking..."

    thinking_message = await message.channel.send(thinking_msg)

    try:
        # Get the server-specific database
        server_db = get_server_db(message.guild.id if message.guild else "dm")

        # Run verification in executor to avoid blocking
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, query_model, clean_content, server_db, server_id)

        if result:
            # Apply personality style to response
            styled_result = personality_engine.get_response_with_style(server_id, result)
            await thinking_message.edit(content=f"🤔 {styled_result}")

            log.info(
                "Auto-verification completed",
                extra={
                    "user_id": str(message.author.id),
                    "server_id": server_id,
                    "statement_length": len(clean_content),
                    "result_length": len(styled_result),
                    "is_markov_bot": is_markov_bot,
                    "author_name": message.author.name if is_markov_bot else None,
                },
            )
        else:
            # Use personality-appropriate error message
            error_msg = personality_engine.get_error_message(server_id)
            await thinking_message.edit(content=f"❓ {error_msg}")

    except Exception as exc:
        log.error(
            "Auto-verification error",
            extra={"error": str(exc), "user_id": str(message.author.id), "server_id": server_id},
        )
        # Use personality for error message
        error_msg = personality_engine.get_error_message(server_id)
        await thinking_message.edit(content=f"💥 {error_msg}")


GRUGBOT_VARIANT = config.GRUGBOT_VARIANT
verify_cmd_name = "verify-dev" if GRUGBOT_VARIANT == "dev" else "verify"


async def _handle_verification(interaction: discord.Interaction):
    if is_rate_limited(interaction.user.id):
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
        extra={"user_id": str(interaction.user.id), "target_length": len(target)},
    )

    await interaction.response.defer(ephemeral=False)  # Tell Discord the bot is thinking

    # Get server ID and personality info
    server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
    personality = personality_engine.get_personality(server_id)
    thinking_msg = f"{personality.chosen_name or personality.name} thinking..."

    msg = await interaction.followup.send(thinking_msg, ephemeral=False)

    try:
        # Get the server-specific database
        server_db = get_server_db(interaction)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, query_model, target, server_db, server_id)

        if result:
            # Apply personality style to response
            styled_result = personality_engine.get_response_with_style(server_id, result)
            await msg.edit(content=f"Verification: {styled_result}")
        else:
            error_msg = personality_engine.get_error_message(server_id)
            await msg.edit(content=error_msg)

    except Exception as exc:
        log.error(
            "Slash command error",
            extra={"error": str(exc), "traceback": traceback.format_exc()},
        )
        # Use personality for error message
        error_msg = personality_engine.get_error_message(server_id)
        await msg.edit(content=f"💥 {error_msg}")


@tree.command(name=verify_cmd_name, description="Verify the truthfulness of the previous message.")
async def verify(interaction: discord.Interaction):
    await _handle_verification(interaction)


@tree.command(name="learn", description="Teach the bot a new fact.")
@app_commands.describe(fact="The fact to learn.")
async def learn(interaction: discord.Interaction, fact: str):
    await interaction.response.defer(ephemeral=True)  # Tell Discord bot is thinking

    # Get personality info
    server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
    personality = personality_engine.get_personality(server_id)
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
    server_db = get_server_db(interaction)
    if server_db.add_fact(fact):
        log.info(
            "Fact learned",
            extra={
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


@tree.command(name="what-know", description="See all the facts the bot knows.")
async def what_know(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # Tell Discord bot is thinking

    # Get personality info
    server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
    personality = personality_engine.get_personality(server_id)
    bot_name = personality.chosen_name or personality.name

    # Get the server-specific database
    server_db = get_server_db(interaction)
    all_facts = server_db.get_all_facts()

    if not all_facts:
        if personality.response_style == "caveman":
            await interaction.followup.send(f"{bot_name} know nothing in this cave.", ephemeral=True)
        elif personality.response_style == "british_working_class":
            await interaction.followup.send("dont know nuffin yet mate, simple as", ephemeral=True)
        else:
            await interaction.followup.send("I don't know any facts yet.", ephemeral=True)
        return

    # Format facts into a numbered list
    fact_list = "\n".join(f"{i + 1}. {fact}" for i, fact in enumerate(all_facts))

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

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue(),
    )
    embed.add_field(name="Facts", value=fact_list[:1024], inline=False)  # Embed field value limit is 1024

    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="help", description="Shows what the bot can do.")
async def help_command(interaction: discord.Interaction):
    # Get personality info
    server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
    personality = personality_engine.get_personality(server_id)
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


@tree.command(name="personality", description="Shows the bot's personality information.")
async def personality_info(interaction: discord.Interaction):
    # Get personality info
    server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
    personality_info = personality_engine.get_personality_info(server_id)

    embed = discord.Embed(
        title=f"Personality: {personality_info['name']}",
        description="My personality and evolution status",
        color=discord.Color.purple(),
    )

    # Evolution stage descriptions
    stage_names = ["Initial", "Developing", "Established", "Evolved"]
    stage_name = stage_names[min(personality_info["evolution_stage"], 3)]

    embed.add_field(name="Name", value=personality_info["name"], inline=True)
    embed.add_field(name="Evolution Stage", value=f"{stage_name} ({personality_info['evolution_stage']})", inline=True)
    embed.add_field(name="Interactions", value=str(personality_info["interaction_count"]), inline=True)
    embed.add_field(name="Style", value=personality_info["style"], inline=True)

    if personality_info["quirks"]:
        quirks_text = ", ".join(personality_info["quirks"])
        embed.add_field(name="Developed Quirks", value=quirks_text, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


def main():
    log.info("Connecting to Discord gateway...")

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
