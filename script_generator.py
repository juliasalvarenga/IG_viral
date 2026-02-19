"""
Viral script generator powered by Claude.

Uses the aggregate content analysis to generate a batch of original,
high-performing video scripts tailored to the target niche.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic
from rich.console import Console

import config

console = Console()

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


@dataclass
class GeneratedScript:
    """A single AI-generated video script."""

    index: int
    hook: str
    hook_type: str
    body: str
    cta: str
    caption: str
    hashtags: list[str]
    estimated_duration_seconds: int
    tone: str
    why_this_works: str

    def full_script(self) -> str:
        """Return the complete script as a formatted string."""
        return (
            f"--- SCRIPT {self.index} ---\n"
            f"HOOK ({self.hook_type.upper()}): {self.hook}\n\n"
            f"BODY:\n{self.body}\n\n"
            f"CTA: {self.cta}\n\n"
            f"CAPTION: {self.caption}\n\n"
            f"HASHTAGS: {' '.join(self.hashtags)}\n"
            f"EST. DURATION: ~{self.estimated_duration_seconds}s\n"
            f"TONE: {self.tone}\n\n"
            f"WHY IT WORKS: {self.why_this_works}\n"
        )


_GENERATION_PROMPT = """\
You are an expert viral short-form video scriptwriter.

Your task: write {n} completely ORIGINAL Instagram reel scripts for the niche \
"{niche}". The scripts must NOT copy the analysed reels — they must be fresh, \
unique angles.

Use this master strategy to guide your writing:
{strategy_json}

Also consider these additional instructions from the user:
{user_instructions}

Return a JSON array with exactly {n} objects. Each object must have these keys:
{{
  "hook": "<The opening line — must stop the scroll in ≤3 seconds>",
  "hook_type": "<question|bold_claim|shock|story_tease|relatability|challenge|list>",
  "body": "<The full script body. Use line breaks between sections. Keep it tight — 30-60 seconds when spoken at a natural pace>",
  "cta": "<The closing call-to-action line>",
  "caption": "<Instagram caption copy, max 150 chars>",
  "hashtags": ["<tag1>", "<tag2>", ...],
  "estimated_duration_seconds": <integer>,
  "tone": "<tone of voice>",
  "why_this_works": "<1-2 sentences on the psychological triggers used>"
}}

Rules:
1. Every hook must be different — vary the hook_type across scripts.
2. Scripts should range from 30 to 90 seconds.
3. Write in a natural, spoken voice — not corporate or stiff.
4. Each script must feel 100% original and not derivative of each other.
5. Include 5-10 relevant hashtags per script.
6. Return ONLY the JSON array. No markdown fences, no extra text.
"""


def generate_scripts(
    aggregate_analysis: dict,
    niche: str = "general",
    n: int = config.SCRIPTS_TO_GENERATE,
    user_instructions: str = "",
) -> list[GeneratedScript]:
    """
    Generate n original video scripts based on the aggregate content analysis.

    Returns a list of GeneratedScript objects.
    """
    console.print(f"\n[bold magenta]Generating {n} original scripts for niche '{niche}'…[/]")

    instructions = user_instructions or "No special instructions. Write for maximum virality."

    prompt = _GENERATION_PROMPT.format(
        n=n,
        niche=niche,
        strategy_json=json.dumps(aggregate_analysis, indent=2)[:8000],
        user_instructions=instructions,
    )

    try:
        client = _get_client()
        message = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        console.print(f"[red]JSON parse error in script generation:[/] {exc}")
        return []
    except anthropic.APIError as exc:
        console.print(f"[red]Claude API error in script generation:[/] {exc}")
        return []

    scripts: list[GeneratedScript] = []
    for i, item in enumerate(items, 1):
        try:
            scripts.append(
                GeneratedScript(
                    index=i,
                    hook=item.get("hook", ""),
                    hook_type=item.get("hook_type", ""),
                    body=item.get("body", ""),
                    cta=item.get("cta", ""),
                    caption=item.get("caption", ""),
                    hashtags=item.get("hashtags", []),
                    estimated_duration_seconds=int(item.get("estimated_duration_seconds", 45)),
                    tone=item.get("tone", ""),
                    why_this_works=item.get("why_this_works", ""),
                )
            )
        except (KeyError, ValueError) as exc:
            console.print(f"  [yellow]Skipping malformed script {i}:[/] {exc}")

    console.print(f"[green]Generated {len(scripts)} scripts.[/]")
    return scripts
