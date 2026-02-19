"""
Audio downloader for Instagram reels.

Uses yt-dlp to extract and download the audio track from a reel's video URL.
Downloaded files are cached locally so repeated runs don't re-download.
"""

from __future__ import annotations

import os
import hashlib
from pathlib import Path

import yt_dlp
from rich.console import Console

import config
from scraper import ReelData

console = Console()

AUDIO_DIR = Path(config.AUDIO_CACHE_DIR)


def _cache_path(reel: ReelData) -> Path:
    """Return the expected local path for a reel's audio file."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = hashlib.md5(reel.shortcode.encode()).hexdigest()[:12]
    return AUDIO_DIR / f"{safe_id}.mp3"


def download_audio(reel: ReelData, force: bool = False) -> Path | None:
    """
    Download the audio track of a reel and return the local file path.

    Returns None if the download fails (e.g. geo-blocked, deleted reel).
    Skips the download when a cached file already exists unless force=True.
    """
    dest = _cache_path(reel)

    if dest.exists() and not force:
        console.print(f"  [dim]Cache hit:[/] {dest.name} — skipping download")
        return dest

    url = reel.video_url or reel.url

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(dest.with_suffix("")),  # yt-dlp appends the extension
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        console.print(f"  [green]Downloaded audio:[/] {dest.name}")
        return dest
    except yt_dlp.utils.DownloadError as exc:
        console.print(f"  [red]Download failed for {reel.shortcode}:[/] {exc}")
        return None


def download_all(reels: list[ReelData], force: bool = False) -> dict[str, Path]:
    """
    Download audio for a list of reels.

    Returns a mapping of {shortcode: local_path} for successful downloads.
    """
    results: dict[str, Path] = {}
    total = len(reels)

    for i, reel in enumerate(reels, 1):
        console.print(f"[bold]Downloading audio {i}/{total}:[/] @{reel.owner_username} — {reel.views:,} views")
        path = download_audio(reel, force=force)
        if path:
            results[reel.shortcode] = path

    return results
