#!/usr/bin/env python3
"""Grug Verifier Bot – The All-Knowing Truthseer of the Tribe
Grug now has a real brain (SQLite + FAISS) and can learn from the world (Google Search).
Run with PYTHONUNBUFFERED so every print is flushed immediately.
"""
import asyncio
import hashlib
import logging
import random
import re
import signal
import sys
import time
import traceback


import discord
from discord.ext import commands
from discord import app_commands
import requests

import config
from grug_db import GrugDB

log = logging.getLogger(__name__)

# Initialize Grug's Brain
db = GrugDB(config.DB_PATH)

config.log_initial_settings()

def build_grug_context(statement: str) -> str:
    """Build Grug context with semantically relevant lore."""
    base_context = """You are Grug, the caveman truth verifier. You live in a big cave near the river with Og.
Your wife is named Ugga and you have two children, Grog and Bork.
You hunt mammoth, make fire, and know ancient wisdom. You speak in short caveman sentences.
You are honest about real world facts but have your own caveman personality and history."""

    # Find lore relevant to the current statement
    relevant_lore = db.search_facts(statement, k=5)

    if relevant_lore:
        lore_context = f"\n\nGrug also remember these things: {' '.join(relevant_lore)}"
        return base_context + lore_context

    return base_context

def build_grug_prompt(statement: str, external_info: str = "") -> str:
    """Build complete Grug verification prompt with lore and external info."""
    grug_context = build_grug_context(statement)

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

# Cache and rate limiting
response_cache = {}
user_cooldowns = {}
session = requests.Session()

def clean_statement(text: str) -> str:
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text = re.sub(r'<@[!&]?[0-9]+>', '', text)
    text = re.sub(r'<#[0-9]+>', '', text)
    text = ' '.join(text.split())
    return text.strip()

def get_cache_key(statement: str) -> str:
    return hashlib.md5(statement.encode()).hexdigest()

def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    if user_id in user_cooldowns and now - user_cooldowns[user_id] < 5:
        return True
    user_cooldowns[user_id] = now
    return False

def extract_lore_from_response(response: str):
    """Extract and save new lore to Grug's brain."""
    try:
        lore_sentences = re.findall(r'[^.!?]*\bGrug\b[^.!?]*[.!?]', response, re.IGNORECASE)
        for sentence in lore_sentences:
            sentence_clean = sentence.strip().capitalize()
            if (sentence_clean and len(sentence_clean) > 15 and not sentence_clean.startswith(('TRUE', 'FALSE'))):
                if db.add_fact(sentence_clean):
                    log.info(f"[GRUGBRAIN] New lore learned: {sentence_clean}")
                else:
                    log.info(f"[GRUGBRAIN] Lore already known: {sentence_clean}")
    except Exception as e:
        log.error(f"[GRUGBRAIN] Error extracting lore: {e}")

def search_google(query: str) -> str:
    """Search Google for information if Grug doesn't know the answer."""
    if not config.CAN_SEARCH:
        return ""
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': config.GOOGLE_API_KEY, 'cx': config.GOOGLE_CSE_ID, 'q': query}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            results = response.json().get('items', [])
            snippets = [item.get('snippet', '') for item in results[:3]]
            return ' '.join(snippets).replace('\n', '')
    except Exception as e:
        log.error(f"[GOOGLE] Search failed: {e}")
    return ""

def query_model(statement: str) -> str | None:
    """Unified query function for both Ollama and Gemini."""
    if not statement or len(statement.strip()) < 3:
        return "FALSE - Statement too short to verify."

    cache_key = get_cache_key(statement)
    if cache_key in response_cache:
        cache_time, cached_response = response_cache[cache_key]
        if time.time() - cache_time < 300:
            log.info("[CACHE] Using cached response")
            return cached_response

    clean_stmt = clean_statement(statement)
    if len(clean_stmt) > 1000:
        clean_stmt = clean_stmt[:1000]

    # Check internal knowledge first
    relevant_lore = db.search_facts(clean_stmt, k=1)
    external_info = ""
    if not relevant_lore: # If no strong internal signal, search web
        log.info(f"[BRAIN] No strong memory for '{clean_stmt}', searching web.")
        external_info = search_google(clean_stmt)

    prompt_text = build_grug_prompt(clean_stmt, external_info)

    if config.USE_GEMINI:
        return query_gemini_api(prompt_text, cache_key)
    else:
        return query_ollama_api(prompt_text, cache_key)

def query_ollama_api(prompt_text: str, cache_key: str) -> str | None:
    log.info("[OLLAMA] Querying with integrated prompt.")
    for idx, url in enumerate(config.OLLAMA_URLS):
        raw_model = config.OLLAMA_MODELS[idx] if idx < len(config.OLLAMA_MODELS) else config.OLLAMA_MODELS[0]
        try:
            payload = {
                "model": raw_model, "prompt": prompt_text, "stream": False,
                "options": {"num_predict": 80, "temperature": 0.3, "top_p": 0.5, "stop": ["<END>"]}
            }
            r = session.post(f"{url}/api/generate", json=payload, timeout=60)
            if r.status_code == 200:
                response = r.json().get("response", "").strip()
                validated = validate_and_process_response(response, cache_key)
                if validated:
                    return validated
        except requests.exceptions.RequestException as e:
            log.error(f"[OLLAMA] Request to {url} failed: {e}")
    return None

def query_gemini_api(prompt_text: str, cache_key: str) -> str | None:
    log.info("[GEMINI] Querying with integrated prompt.")
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=config.GEMINI_MODEL)
        resp = model.generate_content(prompt_text, stream=False, generation_config={"temperature": 0.3, "top_p": 0.5})
        validated = validate_and_process_response(resp.text, cache_key)
        if validated:
            return validated
    except Exception as e:
        log.error(f"[GEMINI] API call failed: {e}")
    return None

def validate_and_process_response(response: str, cache_key: str) -> str | None:
    """Centralized response validation and processing."""
    response = response.split("<END>")[0].strip()
    log.info(f"[RESPONSE] Raw: {response[:200]}")

    true_match = re.search(r'\bTRUE\b', response, re.IGNORECASE)
    false_match = re.search(r'\bFALSE\b', response, re.IGNORECASE)

    if true_match or false_match:
        verdict = "TRUE" if true_match else "FALSE"
        pattern = rf'\b{verdict}\b\s*[-–—:]?\s*(.*)'
        match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            explanation = re.sub(r'\s+', ' ', match.group(1).strip())
            if explanation:
                full_response = f"{verdict} - {explanation}"
                if not full_response.rstrip().endswith((".", "!", "?")):
                    full_response += "."

                if len(full_response.split()) >= 4 and len(full_response) >= 20:
                    response_cache[cache_key] = (time.time(), full_response)
                    extract_lore_from_response(full_response)
                    log.info(f"[RESPONSE] Validated: {full_response}")
                    return full_response
    log.warning(f"[RESPONSE] Invalid format, discarding: {response[:200]}")
    return None

@client.event
async def on_ready():
    log.info(f"[DISCORD] Logged in as {client.user}")
    try:
        await tree.sync()
        log.info("[DISCORD] Commands synced")
    except Exception as e:
        log.error(f"[DISCORD] Failed to sync commands: {e}")

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
    log.info(f"[VERIFY] User: {interaction.user.name}, Target: {target[:100]}...")

    await interaction.response.defer(ephemeral=False) # Tell Discord Grug is thinking
    msg = await interaction.followup.send("Grug thinking...", ephemeral=False)

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, query_model, target)

        if result:
            await msg.edit(content=f"Verification: {result}")
        else:
            error_messages = [
                "Grug no hear truth. Try again.", "Grug brain hurt. No can answer.",
                "Truth hide from Grug. Wait little.", "Sky spirit silent. Ask later.",
                "Grug smash rock, find no answer."
            ]
            await msg.edit(content=random.choice(error_messages))

    except Exception as exc:
        log.error(f"[DISCORD] Slash command error: {exc}")
        log.error(traceback.format_exc())
        await msg.edit(content="💥 Truth overload! Grug head hurt.")

@tree.command(name=verify_cmd_name, description="Verify the truthfulness of the previous message.")
async def verify(interaction: discord.Interaction):
    await _handle_verification(interaction)

@tree.command(name="learn", description="Teach Grug a new fact.")
@app_commands.describe(fact="The fact Grug should learn.")
async def learn(interaction: discord.Interaction, fact: str):
    await interaction.response.defer(ephemeral=True) # Tell Discord Grug is thinking
    if interaction.user.id not in config.TRUSTED_USER_IDS:
        await interaction.followup.send("You not trusted to teach Grug.", ephemeral=True)
        return
    
    if len(fact.strip()) < 5:
        await interaction.followup.send("Fact too short to be useful.", ephemeral=True)
        return

    if db.add_fact(fact):
        log.info(f"[LEARN] User {interaction.user.name} taught Grug: {fact}")
        await interaction.followup.send(f"Grug learn: {fact}", ephemeral=True)
    else:
        await interaction.followup.send("Grug already know that.", ephemeral=True)

@tree.command(name="what-grug-know", description="See all the facts Grug knows.")
async def what_grug_know(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True) # Tell Discord Grug is thinking
    all_facts = db.get_all_facts()
    if not all_facts:
        await interaction.followup.send("Grug know nothing.", ephemeral=True)
        return

    # Format facts into a numbered list
    fact_list = "\n".join(f"{i+1}. {fact}" for i, fact in enumerate(all_facts))

    # Create a Discord embed for better formatting
    embed = discord.Embed(
        title="Grug's Memories",
        description=f"Grug knows {len(all_facts)} things:",
        color=discord.Color.blue()
    )
    embed.add_field(name="Facts", value=fact_list[:1024], inline=False) # Embed field value limit is 1024

    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="grug-help", description="Shows what Grug can do.")
async def grug_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Grug Help",
        description="Here are the things Grug can do:",
        color=discord.Color.green()
    )
    embed.add_field(name="/verify", value="Verifies the truthfulness of the last message.", inline=False)
    embed.add_field(name="/learn", value="Teach Grug a new fact (trusted users only).", inline=False)
    embed.add_field(name="/what-grug-know", value="See all the facts Grug knows.", inline=False)
    embed.add_field(name="/grug-help", value="Shows this help message.", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)








def main():
    log.info("[BOOT] Connecting to Discord gateway …")

    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        log.info(f"[SHUTDOWN] Received signal {signum}. Shutting down gracefully...")
        db.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        client.run(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        log.fatal("[FATAL] Discord bot token is invalid. Please check your config.DISCORD_TOKEN.")
        sys.exit(1)
    except discord.ConnectionClosed as e:
        log.error(f"[DISCORD] Discord connection closed unexpectedly: {e}")
        # Attempt to reconnect or handle gracefully
    except Exception as exc:
        log.fatal(f"[FATAL] Unhandled exception in Discord client: {exc}")
        log.fatal(traceback.format_exc())
        sys.exit(1)
    finally:
        db.close() # Ensure DB connection is closed gracefully if not already by signal
        log.info("[BOOT] Grug has left the cave.")
        sys.exit(0)

if __name__ == "__main__":
    main()
