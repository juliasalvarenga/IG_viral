"""
Instagram scraper powered by Apify.

Pulls top-performing reels from hashtags or profile URLs, filtered by
minimum view count. Returns structured ReelData objects ready for
downstream processing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from apify_client import ApifyClient
from rich.console import Console

import config

console = Console()


@dataclass
class ReelData:
    """Metadata for a single Instagram reel."""

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


def _parse_reel(item: dict) -> Optional[ReelData]:
    """Convert a raw Apify result item into a ReelData object."""
    # Apify's instagram-scraper returns slightly different fields depending
    # on the run type; we handle both post-level and reel-level results.
    video_url = item.get("videoUrl") or item.get("video_url")
    views = item.get("videoViewCount") or item.get("videoPlayCount") or 0

    if not video_url:
        return None  # skip non-video posts

    shortcode = item.get("shortCode") or item.get("id", "")
    post_url = item.get("url") or f"https://www.instagram.com/reel/{shortcode}/"

    return ReelData(
        shortcode=shortcode,
        url=post_url,
        video_url=video_url,
        caption=item.get("caption") or item.get("text") or "",
        views=int(views),
        likes=int(item.get("likesCount") or item.get("likes") or 0),
        comments=int(item.get("commentsCount") or item.get("comments") or 0),
        owner_username=item.get("ownerUsername") or item.get("username") or "",
        timestamp=str(item.get("timestamp") or item.get("taken_at") or ""),
        hashtags=item.get("hashtags") or [],
    )


def scrape_by_hashtag(
    hashtag: str,
    max_results: int = config.MAX_REELS_PER_TARGET,
    min_views: int = config.MIN_VIEWS,
) -> list[ReelData]:
    """
    Scrape reels for a given hashtag and return those that meet the view
    threshold, sorted by view count descending.
    """
    client = ApifyClient(config.APIFY_API_TOKEN)
    clean_tag = hashtag.lstrip("#")

    console.print(f"[bold cyan]Scraping hashtag:[/] #{clean_tag} (min views: {min_views:,})")

    run_input = {
        "hashtags": [clean_tag],
        "resultsLimit": max_results * 3,  # over-fetch so we have enough after filtering
        "scrapeType": "posts",
        "isUserReelFeedURL": False,
        "addParentData": False,
    }

    run = client.actor(config.APIFY_INSTAGRAM_SCRAPER_ACTOR).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    reels = []
    for item in items:
        reel = _parse_reel(item)
        if reel and reel.views >= min_views:
            reels.append(reel)

    reels.sort(key=lambda r: r.views, reverse=True)
    top = reels[:max_results]

    console.print(f"  [green]Found {len(top)} qualifying reels[/] from #{clean_tag}")
    return top


def scrape_by_profile(
    profile_url_or_username: str,
    max_results: int = config.MAX_REELS_PER_TARGET,
    min_views: int = config.MIN_VIEWS,
) -> list[ReelData]:
    """
    Scrape reels from a specific Instagram profile and return those that
    meet the view threshold, sorted by view count descending.
    """
    client = ApifyClient(config.APIFY_API_TOKEN)

    # Normalise: accept both a username and a full profile URL
    if profile_url_or_username.startswith("http"):
        target_url = profile_url_or_username
        username = profile_url_or_username.rstrip("/").split("/")[-1]
    else:
        username = profile_url_or_username.lstrip("@")
        target_url = f"https://www.instagram.com/{username}/"

    console.print(f"[bold cyan]Scraping profile:[/] @{username} (min views: {min_views:,})")

    run_input = {
        "directUrls": [target_url],
        "resultsType": "posts",
        "resultsLimit": max_results * 3,
        "addParentData": False,
    }

    run = client.actor(config.APIFY_INSTAGRAM_SCRAPER_ACTOR).call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    reels = []
    for item in items:
        reel = _parse_reel(item)
        if reel and reel.views >= min_views:
            reels.append(reel)

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
    Accept a mixed list of hashtags (e.g. 'fitness') and profile handles /
    URLs (e.g. '@garyvee' or 'https://www.instagram.com/garyvee/') and
    return a de-duplicated, combined list of qualifying reels.
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

        time.sleep(1)  # be polite between Apify calls

    all_reels.sort(key=lambda r: r.views, reverse=True)
    return all_reels
