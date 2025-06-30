import os
import re

# --- Discord Configuration ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Only validate Discord token in single-bot mode (when not in multi-bot container)
# Multi-bot mode will set environment variables dynamically per bot instance
if not DISCORD_TOKEN and not os.getenv("GRUGTHINK_MULTIBOT_MODE"):
    raise ValueError("Missing DISCORD_TOKEN")

# --- LLM Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_URLS = [url.strip() for url in os.getenv("OLLAMA_URLS", "").split(",") if url.strip()]
OLLAMA_MODELS = [model.strip() for model in os.getenv("OLLAMA_MODELS", "llama3.2:3b").split(",") if model.strip()]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# --- Google Search Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# --- GrugBot Configuration ---
DATA_DIR = os.getenv("GRUGBOT_DATA_DIR", os.path.dirname(__file__))


# Create unique database path based on Discord token to prevent memory sharing between bot instances
def _get_unique_db_path():
    if DISCORD_TOKEN:
        # Create a short hash of the Discord token for database isolation
        import hashlib

        token_hash = hashlib.sha256(DISCORD_TOKEN.encode()).hexdigest()[:12]
        return os.path.join(DATA_DIR, f"grug_lore_{token_hash}.db")
    else:
        # Fallback for multi-bot mode or when token not available
        return os.path.join(DATA_DIR, "grug_lore.db")


DB_PATH = _get_unique_db_path()
GRUGBOT_VARIANT = os.getenv("GRUGBOT_VARIANT", "prod")
TRUSTED_USER_IDS = [int(uid) for uid in os.getenv("TRUSTED_USER_IDS", "").split(",") if uid.strip()]

# Whether to load the heavy embedding model at startup. Set to 'False' for lightweight deployments.
LOAD_EMBEDDER = os.getenv("LOAD_EMBEDDER", "True").lower() == "true"

# --- Logging Configuration ---
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()


# --- Validation ---
def is_valid_url(url):
    # More robust regex for URL validation
    regex = re.compile(
        r"^(?:http)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)",
        re.IGNORECASE,
    )
    return re.match(regex, url) is not None


for url in OLLAMA_URLS:
    if not is_valid_url(url):
        raise ValueError(f"Invalid OLLAMA_URL: {url}")

for model in OLLAMA_MODELS:
    if not re.match(r"^[\w\-\.:]+$", model):
        raise ValueError(f"Invalid model name: {model}")

if GEMINI_API_KEY and not re.match(r"^[\w\-]+$", GEMINI_API_KEY):
    raise ValueError("Invalid GEMINI_API_KEY")

if GOOGLE_API_KEY and not re.match(r"^[\w\-]+$", GOOGLE_API_KEY):
    raise ValueError("Invalid GOOGLE_API_KEY")

if GOOGLE_CSE_ID and not re.match(r"^[\w\-]+$", GOOGLE_CSE_ID):
    raise ValueError("Invalid GOOGLE_CSE_ID")

USE_GEMINI = bool(GEMINI_API_KEY)
if not USE_GEMINI and not OLLAMA_URLS:
    raise ValueError("Missing LLM configuration")

CAN_SEARCH = bool(GOOGLE_API_KEY and GOOGLE_CSE_ID)


def log_initial_settings():
    """Log initial configuration settings for debugging."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        "Configuration loaded",
        extra={
            "variant": GRUGBOT_VARIANT,
            "use_gemini": USE_GEMINI,
            "can_search": CAN_SEARCH,
            "trusted_users_count": len(TRUSTED_USER_IDS),
            "log_level": LOG_LEVEL_STR,
        },
    )
