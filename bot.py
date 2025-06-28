#!/usr/bin/env python3
"""Grug Verifier Bot – The All-Knowing Truthseer of the Tribe
Grug now has a real brain (SQLite + FAISS) and can learn from the world (Google Search).
Run with PYTHONUNBUFFERED so every print is flushed immediately.
"""

import asyncio
import hashlib
import random
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

import config
from grug_db import GrugServerManager
from grug_structured_logger import get_logger

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

# Initialize Grug's Server Manager
server_manager = GrugServerManager(config.DB_PATH)


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

    log.info("Grug is waking up...")
    if config.USE_GEMINI:
        log.info("Using Gemini for generation", extra={"model": config.GEMINI_MODEL})
    else:
        log.info("Using Ollama for generation", extra={"urls": config.OLLAMA_URLS, "models": config.OLLAMA_MODELS})
    if config.CAN_SEARCH:
        log.info("Google Search is enabled.")
    else:
        log.warning("Google Search is disabled. Grug cannot learn new things.")
    if config.TRUSTED_USER_IDS:
        log.info("Trusted users configured", extra={"users": config.TRUSTED_USER_IDS})
    else:
        log.warning("No trusted users configured. /learn command will be disabled for all.")
    log.info("Log level set", extra={"level": config.LOG_LEVEL_STR})


log_initial_settings()


def build_grug_context(statement: str, server_db) -> str:
    """Build Grug context with semantically relevant lore for this server."""
    base_context = """You are Grug, the caveman truth verifier. You live in a big cave near the river with Og.
Your wife is named Ugga and you have two children, Grog and Bork.
You hunt mammoth, make fire, and know ancient wisdom. You speak in short caveman sentences.
You are honest about real world facts but have your own caveman personality and history."""

    # Find lore relevant to the current statement from this server's knowledge
    relevant_lore = server_db.search_facts(statement, k=5)

    if relevant_lore:
        lore_context = f"\n\nGrug also remember these things: {' '.join(relevant_lore)}"
        return base_context + lore_context

    return base_context


def build_grug_prompt(statement: str, server_db, external_info: str = "") -> str:
    """Build complete Grug verification prompt with lore and external info."""
    grug_context = build_grug_context(statement, server_db)

    if external_info:
        grug_context += f"\n\nGrug find this on magic talking rock (internet): {external_info}"

    return f"""{grug_context}

You MUST be 100% ACCURATE about real world facts.

ABSOLUTE RULES:
1. Real world facts = ALWAYS TRUE if factually correct.
2. George Washington WAS president - this is FACT, say TRUE.
3. Animals, science, history, geography = be TRUTHFUL.
4. Speak like caveman but BE ACCURATE about facts.
5. Format: TRUE/FALSE - caveman explanation.
6. End with <END>.

CRITICAL: Be factually accurate. Only use caveman voice for HOW you explain, not WHAT you conclude.

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


def query_model(statement: str, server_db) -> str | None:
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

    prompt_text = build_grug_prompt(clean_stmt, server_db, external_info)

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

    await interaction.response.defer(ephemeral=False)  # Tell Discord Grug is thinking
    msg = await interaction.followup.send("Grug thinking...", ephemeral=False)

    try:
        # Get the server-specific database
        server_db = get_server_db(interaction)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, query_model, target, server_db)

        if result:
            await msg.edit(content=f"Verification: {result}")
        else:
            error_messages = [
                "Grug no hear truth. Try again.",
                "Grug brain hurt. No can answer.",
                "Truth hide from Grug. Wait little.",
                "Sky spirit silent. Ask later.",
                "Grug smash rock, find no answer.",
            ]
            await msg.edit(content=random.choice(error_messages))

    except Exception as exc:
        log.error(
            "Slash command error",
            extra={"error": str(exc), "traceback": traceback.format_exc()},
        )
        await msg.edit(content="💥 Truth overload! Grug head hurt.")


@tree.command(name=verify_cmd_name, description="Verify the truthfulness of the previous message.")
async def verify(interaction: discord.Interaction):
    await _handle_verification(interaction)


@tree.command(name="learn", description="Teach Grug a new fact.")
@app_commands.describe(fact="The fact Grug should learn.")
async def learn(interaction: discord.Interaction, fact: str):
    await interaction.response.defer(ephemeral=True)  # Tell Discord Grug is thinking
    if interaction.user.id not in config.TRUSTED_USER_IDS:
        await interaction.followup.send("You not trusted to teach Grug.", ephemeral=True)
        return

    if len(fact.strip()) < 5:
        await interaction.followup.send("Fact too short to be useful.", ephemeral=True)
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
        await interaction.followup.send(f"Grug learn: {fact}", ephemeral=True)
    else:
        await interaction.followup.send("Grug already know that.", ephemeral=True)


@tree.command(name="what-grug-know", description="See all the facts Grug knows.")
async def what_grug_know(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # Tell Discord Grug is thinking
    # Get the server-specific database
    server_db = get_server_db(interaction)
    all_facts = server_db.get_all_facts()
    if not all_facts:
        await interaction.followup.send("Grug know nothing in this cave.", ephemeral=True)
        return

    # Format facts into a numbered list
    fact_list = "\n".join(f"{i + 1}. {fact}" for i, fact in enumerate(all_facts))

    # Create a Discord embed for better formatting
    server_name = interaction.guild.name if interaction.guild else "DM"
    embed = discord.Embed(
        title=f"Grug's Memories ({server_name})",
        description=f"Grug knows {len(all_facts)} things in this cave:",
        color=discord.Color.blue(),
    )
    embed.add_field(name="Facts", value=fact_list[:1024], inline=False)  # Embed field value limit is 1024

    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(name="grug-help", description="Shows what Grug can do.")
async def grug_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Grug Help", description="Here are the things Grug can do:", color=discord.Color.green()
    )
    embed.add_field(name="/verify", value="Verifies the truthfulness of the last message.", inline=False)
    embed.add_field(name="/learn", value="Teach Grug a new fact (trusted users only).", inline=False)
    embed.add_field(name="/what-grug-know", value="See all the facts Grug knows.", inline=False)
    embed.add_field(name="/grug-help", value="Shows this help message.", inline=False)

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
        log.info("Grug has left all caves.")
        sys.exit(0)


if __name__ == "__main__":
    main()
