"""
Audio transcription using Groq's Whisper API.

Uses the same Groq account as the LLM — no extra signup needed.
Model: whisper-large-v3-turbo (fast, accurate, free tier included).

Groq's free Whisper limits are generous: ~7,200 audio-seconds/day.
Transcripts are cached as .txt sidecar files so repeat runs are instant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from groq import Groq
from rich.console import Console

import config
from scraper import ReelData

console = Console()

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def transcribe_file(audio_path: Path, force: bool = False) -> Optional[str]:
    """
    Transcribe a local audio file via Groq Whisper and return the transcript.

    Caches the result as a .txt sidecar file next to the audio.
    Pass force=True to re-transcribe even if a cached version exists.
    """
    cache_path = audio_path.with_suffix(".txt")

    if cache_path.exists() and not force:
        console.print(f"  [dim]Transcript cache hit:[/] {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    if not audio_path.exists():
        console.print(f"  [red]Audio file not found:[/] {audio_path}")
        return None

    console.print(f"  [cyan]Transcribing via Groq Whisper:[/] {audio_path.name}")

    try:
        client = _get_client()
        with audio_path.open("rb") as f:
            response = client.audio.transcriptions.create(
                file=(audio_path.name, f.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )
        transcript = str(response).strip()
        cache_path.write_text(transcript, encoding="utf-8")
        console.print(f"  [green]Done:[/] {len(transcript)} chars")
        return transcript
    except Exception as exc:
        console.print(f"  [red]Transcription failed:[/] {exc}")
        return None


def transcribe_reels(
    reels: list[ReelData],
    audio_map: dict[str, Path],
    force: bool = False,
) -> list[ReelData]:
    """
    Transcribe audio for each reel that has a downloaded file.
    Updates reel.transcript in-place and returns the list.
    """
    total = len(reels)
    for i, reel in enumerate(reels, 1):
        audio_path = audio_map.get(reel.shortcode)
        if not audio_path:
            console.print(f"[yellow]No audio for {reel.shortcode}, skipping transcription[/]")
            continue

        console.print(f"[bold]Transcribing {i}/{total}:[/] @{reel.owner_username}")
        reel.transcript = transcribe_file(audio_path, force=force)

    return reels
