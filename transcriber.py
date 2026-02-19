"""
Audio transcription using OpenAI Whisper API.

Takes a local MP3 file (or any audio format Whisper accepts) and returns
the full plain-text transcript.  Results are cached as .txt sidecar files
next to the audio so repeat runs are instant.
"""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI
from rich.console import Console

import config
from scraper import ReelData

console = Console()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def transcribe_file(audio_path: Path, force: bool = False) -> str | None:
    """
    Transcribe an audio file via Whisper and return the transcript text.

    Caches the result as a .txt file alongside the audio.  Pass force=True
    to re-transcribe even if a cached version exists.
    """
    cache_path = audio_path.with_suffix(".txt")

    if cache_path.exists() and not force:
        console.print(f"  [dim]Transcript cache hit:[/] {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    if not audio_path.exists():
        console.print(f"  [red]Audio file not found:[/] {audio_path}")
        return None

    console.print(f"  [cyan]Transcribing:[/] {audio_path.name}")

    try:
        client = _get_client()
        with audio_path.open("rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
            )
        transcript = str(response).strip()
        cache_path.write_text(transcript, encoding="utf-8")
        console.print(f"  [green]Transcribed:[/] {len(transcript)} chars")
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
            console.print(f"[yellow]No audio for reel {reel.shortcode}, skipping transcription[/]")
            continue

        console.print(f"[bold]Transcribing {i}/{total}:[/] @{reel.owner_username}")
        reel.transcript = transcribe_file(audio_path, force=force)

    return reels
