"""
Content analysis powered by Groq (free tier LLM).

Free account: https://console.groq.com
Default model: llama-3.3-70b-versatile (fast, high quality, generous free limits)

Reads a batch of reel transcripts and metadata, then produces a structured
breakdown of:
  - Hook patterns (first 3 seconds)
  - Storytelling structure
  - Tone and pacing
  - Call-to-action style
  - Recurring themes and vocabulary
"""

from __future__ import annotations

import json

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


def _chat(prompt: str, max_tokens: int = 1024) -> str | None:
    """Send a prompt to Groq and return the response text."""
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        console.print(f"  [red]Groq API error:[/] {exc}")
        return None


# ---------------------------------------------------------------------------
# Per-reel analysis
# ---------------------------------------------------------------------------

_PER_REEL_PROMPT = """\
You are an expert viral content strategist specialising in short-form video.

Below is the transcript and metadata for a high-performing Instagram reel.
Analyse it and return a JSON object with EXACTLY these keys:

{{
  "hook": "<The opening line or first ~15 words. Explain WHY it grabs attention>",
  "hook_type": "<one of: question | bold_claim | shock | story_tease | relatability | challenge | list>",
  "structure": "<1-2 sentences describing how the content is paced and structured>",
  "tone": "<e.g. energetic, calm, humorous, authoritative, vulnerable>",
  "cta_style": "<how the creator ends / drives action>",
  "key_themes": ["<theme1>", "<theme2>"],
  "power_words": ["<word1>", "<word2>", "<word3>"],
  "why_it_works": "<2-3 sentences on the psychological triggers that drove views>"
}}

Metadata:
- Owner: @{username}
- Views: {views:,}
- Likes: {likes:,}
- Caption: {caption}

Transcript:
{transcript}

Return ONLY the JSON object. No markdown fences, no extra text.
"""


def analyse_reel(reel: ReelData) -> dict | None:
    """Run per-reel analysis. Returns a dict or None on failure."""
    if not reel.transcript:
        return None

    prompt = _PER_REEL_PROMPT.format(
        username=reel.owner_username,
        views=reel.views,
        likes=reel.likes,
        caption=(reel.caption[:300] + "…") if len(reel.caption) > 300 else reel.caption,
        transcript=reel.transcript[:4000],
    )

    raw = _chat(prompt, max_tokens=1024)
    if not raw:
        return None

    # Strip markdown fences if the model included them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        console.print(f"  [red]JSON parse error for {reel.shortcode}:[/] {exc}")
        return None


# ---------------------------------------------------------------------------
# Aggregate analysis across all reels
# ---------------------------------------------------------------------------

_AGGREGATE_PROMPT = """\
You are an expert viral content strategist.

Below are individual analyses of {n} top-performing Instagram reels in the \
niche: "{niche}".

Each analysis is a JSON object. Your job is to synthesise these into a single \
MASTER STRATEGY document returned as a JSON object with these keys:

{{
  "niche": "{niche}",
  "top_hook_patterns": [
    {{"pattern": "<description>", "frequency": <int>, "example": "<quote>"}}
  ],
  "dominant_tones": ["<tone1>", "<tone2>"],
  "common_structures": ["<structure1>", "<structure2>"],
  "power_vocabulary": ["<word1>", ...],
  "psychological_triggers": ["<trigger1>", ...],
  "content_gaps": ["<gap1>", "<gap2>"],
  "winning_formula": "<3-5 sentence description of what makes content go viral in this niche>"
}}

Individual analyses:
{analyses_json}

Return ONLY the JSON object. No markdown fences, no extra text.
"""


def analyse_batch(reels: list[ReelData], niche: str = "general") -> dict | None:
    """
    Perform per-reel analysis on all reels that have transcripts, then
    synthesise a master strategy. Returns the aggregate analysis dict.
    """
    console.print(f"\n[bold magenta]Analysing {len(reels)} reels with Groq ({config.GROQ_MODEL})…[/]")

    per_reel_results = []
    for i, reel in enumerate(reels, 1):
        if not reel.transcript:
            continue
        console.print(f"  Analysing reel {i}/{len(reels)}: @{reel.owner_username} ({reel.views:,} views)")
        result = analyse_reel(reel)
        if result:
            reel.analysis = result
            per_reel_results.append(result)

    if not per_reel_results:
        console.print("[red]No transcripts available for analysis.[/]")
        return None

    console.print(f"\n[bold magenta]Synthesising master strategy from {len(per_reel_results)} analyses…[/]")

    prompt = _AGGREGATE_PROMPT.format(
        n=len(per_reel_results),
        niche=niche,
        analyses_json=json.dumps(per_reel_results, indent=2)[:12000],
    )

    raw = _chat(prompt, max_tokens=2048)
    if not raw:
        return None

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        aggregate = json.loads(raw)
        console.print("[green]Master strategy complete.[/]")
        return aggregate
    except json.JSONDecodeError as exc:
        console.print(f"[red]JSON parse error in aggregate analysis:[/] {exc}")
        return None
