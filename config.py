"""
Central configuration.

Works in two environments:
  1. Local / CLI  — reads from a .env file via python-dotenv
  2. Streamlit Cloud — reads from st.secrets (set in the Streamlit dashboard)

Free stack:
  - Scraping:      instaloader (Instagram login, no paid API)
  - Transcription: Groq Whisper API (same key as LLM, free tier)
  - LLM:           Groq free tier (Llama 3.3 70B)
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Read from st.secrets (Streamlit Cloud) with fallback to env vars."""
    try:
        import streamlit as st  # only available when running as Streamlit app
        val = st.secrets.get(key, "")
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, default)


def _require(key: str) -> str:
    val = _get(key)
    if not val:
        raise EnvironmentError(
            f"Required config key '{key}' is not set. "
            f"Add it to .env (local) or Streamlit secrets (cloud)."
        )
    return val


# --- Groq (free tier — LLM + Whisper) ---
GROQ_API_KEY: str = _require("GROQ_API_KEY")

# --- Instagram credentials (for instaloader) ---
IG_USERNAME: str = _get("IG_USERNAME")
IG_PASSWORD: str = _get("IG_PASSWORD")

# --- Google Sheets (optional) ---
GOOGLE_SERVICE_ACCOUNT_FILE: str = _get("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
GOOGLE_SHEET_ID: str = _get("GOOGLE_SHEET_ID")

# --- Scraper defaults ---
SCRAPE_TARGETS: list[str] = [
    t.strip() for t in _get("SCRAPE_TARGETS", "fitness,motivation").split(",") if t.strip()
]
MIN_VIEWS: int = int(_get("MIN_VIEWS", "1000000"))
MAX_REELS_PER_TARGET: int = int(_get("MAX_REELS_PER_TARGET", "20"))
SCRIPTS_TO_GENERATE: int = int(_get("SCRIPTS_TO_GENERATE", "10"))

# --- Groq model ---
GROQ_MODEL: str = _get("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Local paths ---
AUDIO_CACHE_DIR = "audio_cache"
OUTPUT_DIR = "output"
