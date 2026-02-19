"""
Central configuration loaded from environment variables.
Copy .env.example to .env and fill in your keys before running.

Free stack:
  - Scraping:      instaloader (Instagram login, no paid API)
  - Transcription: local OpenAI Whisper model (runs on your machine)
  - LLM:           Groq free tier (free account at console.groq.com)
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


# --- Groq (free tier LLM) ---
GROQ_API_KEY: str = _require("GROQ_API_KEY")

# --- Instagram credentials (for instaloader — no API key needed) ---
IG_USERNAME: str = os.getenv("IG_USERNAME", "")  # optional but recommended
IG_PASSWORD: str = os.getenv("IG_PASSWORD", "")  # optional but recommended

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

# --- Groq model ---
# Best free models: llama-3.3-70b-versatile | mixtral-8x7b-32768 | gemma2-9b-it
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Local Whisper model size ---
# tiny | base | small | medium | large  (larger = more accurate but slower)
WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")

# --- Local paths ---
AUDIO_CACHE_DIR = "audio_cache"
OUTPUT_DIR = "output"
