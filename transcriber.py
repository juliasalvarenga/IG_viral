"""
Audio transcription using a local OpenAI Whisper model.

No API key or internet connection required after the first run
(the model weights are downloaded automatically on first use and cached
locally by the whisper library under ~/.cache/whisper/).

Model sizes and approximate tradeoffs (English):
  tiny   — fastest, ~1x real-time on CPU, lowest accuracy
  base   — good balance, ~2-4x real-time on CPU        ← default
  small  — better accuracy, ~4-8x real-time on CPU
  medium — near-API quality, slow on CPU (GPU recommended)
  large  — best quality, GPU required for reasonable speed

Set WHISPER_MODEL_SIZE in .env to override.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

import config
from scraper import ReelData

console = Console()

# Lazily loaded — avoids slow import when running --help
_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper  # openai-whisper package

        size = config.WHISPER_MODEL_SIZE
        console.print(f"[cyan]Loading local Whisper model:[/] '{size}' (downloading on first run…)")
        _model = whisper.load_model(size)
        console.print(f"[green]Whisper model ready.[/]")
    return _model


def transcribe_file(audio_path: Path, force: bool = False) -> Optional[str]:
    """
    Transcribe a local audio file and return the plain-text transcript.

    Caches the result as a sidecar .txt file next to the audio.
    Pass force=True to re-transcribe even if a cached file exists.
    """
    cache_path = audio_path.with_suffix(".txt")

    if cache_path.exists() and not force:
        console.print(f"  [dim]Transcript cache hit:[/] {cache_path.name}")
        return cache_path.read_text(encoding="utf-8")

    if not audio_path.exists():
        console.print(f"  [red]Audio file not found:[/] {audio_path}")
        return None

    console.print(f"  [cyan]Transcribing locally:[/] {audio_path.name}")

    try:
        model = _get_model()
        result = model.transcribe(str(audio_path), fp16=False)
        transcript = result["text"].strip()
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
