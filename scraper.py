"""
Instagram scraper using instaloader (no paid API required).

Logs in with your Instagram credentials (stored in .env) to avoid
aggressive rate-limiting on anonymous requests.  Falls back to anonymous
access if credentials are not provided, but expect more throttling.

Pulls top-performing reels from hashtags or profile usernames, filtered by
minimum view count.  Returns structured ReelData objects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import instaloader
from rich.console import Console

import config

console = Console()

# Instaloader instance (shared, login happens once)
_loader: instaloader.Instaloader | None = None


def _get_loader() -> instaloader.Instaloader:
    global _loader
    if _loader is not None:
        return _loader

    L = instaloader.Instaloader(
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    if config.IG_USERNAME and config.IG_PASSWORD:
        try:
            L.login(config.IG_USERNAME, config.IG_PASSWORD)
            console.print(f"[green]Logged in to Instagram as @{config.IG_USERNAME}[/]")
        except instaloader.exceptions.BadCredentialsException:
            console.print("[red]Instagram login failed — bad credentials. Falling back to anonymous.[/]")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            console.print(
                "[yellow]Two-factor auth required.[/] Disable 2FA on your scraper account "
                "or log in once manually with: [bold]instaloader --login <username>[/]"
            )
    else:
        console.print("[yellow]No IG credentials set — using anonymous access (more rate-limiting).[/]")

    _loader = L
    return L


@dataclass
class ReelData:
    """Metadata for a single Instagram reel / video post."""

    shortcode: str
    url: str
    video_url: Optional[str]
    caption: str
    views: int
    likes: int
    comments: int
    owner_username: str
    timestamp: str
    hashtags: list[str] = field(default_factory=list)
    transcript: Optional[str] = None
    analysis: Optional[dict] = None


def _post_to_reel(post: instaloader.Post) -> Optional[ReelData]:
    """Convert an instaloader Post to a ReelData object."""
    if not post.is_video:
        return None

    return ReelData(
        shortcode=post.shortcode,
        url=f"https://www.instagram.com/reel/{post.shortcode}/",
        video_url=post.video_url,
        caption=post.caption or "",
        views=post.video_view_count or 0,
        likes=post.likes,
        comments=post.comments,
        owner_username=post.owner_username,
        timestamp=str(post.date_utc),
        hashtags=list(post.caption_hashtags),
    )


def scrape_by_hashtag(
    hashtag: str,
    max_results: int = config.MAX_REELS_PER_TARGET,
    min_views: int = config.MIN_VIEWS,
) -> list[ReelData]:
    """
    Scrape video posts for a hashtag and return those meeting the view
    threshold, sorted by view count descending.
    """
    L = _get_loader()
    clean_tag = hashtag.lstrip("#")
    console.print(f"[bold cyan]Scraping hashtag:[/] #{clean_tag} (min views: {min_views:,})")

    try:
        tag = instaloader.Hashtag.from_name(L.context, clean_tag)
    except instaloader.exceptions.QueryReturnedNotFoundException:
        console.print(f"  [red]Hashtag #{clean_tag} not found.[/]")
        return []

    reels: list[ReelData] = []
    fetched = 0
    limit = max_results * 5  # over-fetch to get enough videos after filtering

    try:
        for post in tag.get_posts():
            if fetched >= limit:
                break
            fetched += 1

            reel = _post_to_reel(post)
            if reel and reel.views >= min_views:
                reels.append(reel)

            # Brief pause to respect rate limits
            if fetched % 10 == 0:
                time.sleep(2)
    except instaloader.exceptions.TooManyRequestsException:
        console.print(f"  [yellow]Rate limited by Instagram after {fetched} posts. Using what we have.[/]")

    reels.sort(key=lambda r: r.views, reverse=True)
    top = reels[:max_results]
    console.print(f"  [green]Found {len(top)} qualifying reels[/] from #{clean_tag}")
    return top


def scrape_by_profile(
    username_or_url: str,
    max_results: int = config.MAX_REELS_PER_TARGET,
    min_views: int = config.MIN_VIEWS,
) -> list[ReelData]:
    """
    Scrape video posts from a specific Instagram profile.
    Accepts a bare username, @username, or a full profile URL.
    """
    L = _get_loader()

    # Normalise input
    if username_or_url.startswith("http"):
        username = username_or_url.rstrip("/").split("/")[-1]
    else:
        username = username_or_url.lstrip("@")

    console.print(f"[bold cyan]Scraping profile:[/] @{username} (min views: {min_views:,})")

    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except instaloader.exceptions.ProfileNotExistsException:
        console.print(f"  [red]Profile @{username} not found.[/]")
        return []

    reels: list[ReelData] = []
    fetched = 0
    limit = max_results * 5

    try:
        for post in profile.get_posts():
            if fetched >= limit:
                break
            fetched += 1

            reel = _post_to_reel(post)
            if reel and reel.views >= min_views:
                reels.append(reel)

            if fetched % 10 == 0:
                time.sleep(2)
    except instaloader.exceptions.TooManyRequestsException:
        console.print(f"  [yellow]Rate limited by Instagram after {fetched} posts. Using what we have.[/]")

    reels.sort(key=lambda r: r.views, reverse=True)
    top = reels[:max_results]
    console.print(f"  [green]Found {len(top)} qualifying reels[/] from @{username}")
    return top


def scrape_targets(
    targets: list[str],
    max_results: int = config.MAX_REELS_PER_TARGET,
    min_views: int = config.MIN_VIEWS,
) -> list[ReelData]:
    """
    Accept a mixed list of hashtags and @profiles/URLs and return a
    de-duplicated, combined list of qualifying reels sorted by views.
    """
    seen: set[str] = set()
    all_reels: list[ReelData] = []

    for target in targets:
        target = target.strip()
        if not target:
            continue

        try:
            if target.startswith("http") or target.startswith("@"):
                batch = scrape_by_profile(target, max_results, min_views)
            else:
                batch = scrape_by_hashtag(target, max_results, min_views)
        except Exception as exc:
            console.print(f"  [red]Error scraping '{target}':[/] {exc}")
            continue

        for reel in batch:
            if reel.shortcode not in seen:
                seen.add(reel.shortcode)
                all_reels.append(reel)

        time.sleep(3)  # pause between targets

    all_reels.sort(key=lambda r: r.views, reverse=True)
    return all_reels
