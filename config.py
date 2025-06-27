
import logging
import os
import re

log = logging.getLogger(__name__)

# --- Discord Configuration ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    log.error("[FATAL] DISCORD_TOKEN not set in environment")
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
DB_PATH = os.path.join(DATA_DIR, "grug_lore.db")
GRUGBOT_VARIANT = os.getenv("GRUGBOT_VARIANT", "prod")
TRUSTED_USER_IDS = [int(uid) for uid in os.getenv("TRUSTED_USER_IDS", "").split(",") if uid.strip()]

# --- Logging Configuration ---
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(level=log_level)


# --- Validation ---
def is_valid_url(url): return re.match(r"^https?://", url)

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
    log.error("[FATAL] Neither GEMINI_API_KEY nor OLLAMA_URLS provided")
    raise ValueError("Missing LLM configuration")

CAN_SEARCH = bool(GOOGLE_API_KEY and GOOGLE_CSE_ID)


def log_initial_settings():
    """Logs the initial configuration settings."""
    log.info("[BOOT] Grug is waking up...")
    if USE_GEMINI:
        log.info(f"[ENV] Using Gemini for generation (Model: {GEMINI_MODEL})")
    else:
        log.info(f"[ENV] Using Ollama for generation: {OLLAMA_URLS} with models {OLLAMA_MODELS}")
    if CAN_SEARCH:
        log.info("[ENV] Google Search is enabled.")
    else:
        log.warning("[ENV] Google Search is disabled. Grug cannot learn new things.")
    if TRUSTED_USER_IDS:
        log.info(f"[ENV] Trusted users configured: {TRUSTED_USER_IDS}")
    else:
        log.warning("[ENV] No trusted users configured. /learn command will be disabled for all.")
    log.info(f"[ENV] Log level set to {log_level_str}")

