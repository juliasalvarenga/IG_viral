"""
Central configuration loaded from environment variables.
Copy .env.example to .env and fill in your keys before running.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in your values."
        )
    return value


# --- API keys ---
APIFY_API_TOKEN: str = _require("APIFY_API_TOKEN")
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str = _require("OPENAI_API_KEY")

# --- Google Sheets (optional) ---
GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")

# --- Scraper defaults ---
SCRAPE_TARGETS: list[str] = [
    t.strip() for t in os.getenv("SCRAPE_TARGETS", "fitness,motivation").split(",") if t.strip()
]
MIN_VIEWS: int = int(os.getenv("MIN_VIEWS", "1000000"))
MAX_REELS_PER_TARGET: int = int(os.getenv("MAX_REELS_PER_TARGET", "20"))
SCRIPTS_TO_GENERATE: int = int(os.getenv("SCRIPTS_TO_GENERATE", "10"))

# --- Apify actor IDs ---
APIFY_INSTAGRAM_SCRAPER_ACTOR = "apify/instagram-scraper"

# --- Claude model ---
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- Local paths ---
AUDIO_CACHE_DIR = "audio_cache"
OUTPUT_DIR = "output"
