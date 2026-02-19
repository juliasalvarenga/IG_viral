#!/usr/bin/env python3
"""
IG Viral Scripter — CLI entry point.

Full pipeline:
  1. Scrape top reels from Instagram (via Apify)
  2. Download audio tracks (via yt-dlp)
  3. Transcribe audio (via OpenAI Whisper)
  4. Analyse content patterns (via Claude)
  5. Generate original scripts (via Claude)
  6. Export results to files (and optionally Google Sheets)

Usage:
  python main.py --help
  python main.py --targets fitness,motivation --niche "fitness motivation" --scripts 10
  python main.py --targets @garyvee --niche "entrepreneurship" --min-views 500000
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
console = Console()


def _print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]IG Viral Scripter[/]\n"
            "[dim]Scrape → Transcribe → Analyse → Generate[/]",
            border_style="magenta",
        )
    )


@app.command()
def run(
    targets: str = typer.Option(
        None,
        "--targets",
        "-t",
        help="Comma-separated hashtags or @profiles to scrape. Overrides .env SCRAPE_TARGETS.",
    ),
    niche: str = typer.Option(
        "general",
        "--niche",
        "-n",
        help="Human-readable niche label used in analysis prompts (e.g. 'fitness motivation').",
    ),
    min_views: int = typer.Option(
        None,
        "--min-views",
        "-v",
        help="Minimum view count to include a reel. Overrides .env MIN_VIEWS.",
    ),
    max_reels: int = typer.Option(
        None,
        "--max-reels",
        "-m",
        help="Max reels to pull per target. Overrides .env MAX_REELS_PER_TARGET.",
    ),
    scripts: int = typer.Option(
        None,
        "--scripts",
        "-s",
        help="Number of scripts to generate. Overrides .env SCRIPTS_TO_GENERATE.",
    ),
    instructions: str = typer.Option(
        "",
        "--instructions",
        "-i",
        help="Extra instructions to include in the script-generation prompt.",
    ),
    sheets: bool = typer.Option(
        False,
        "--sheets",
        help="Export results to Google Sheets (requires credentials in .env).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Re-download and re-transcribe even if cached files exist.",
    ),
    skip_download: bool = typer.Option(
        False,
        "--skip-download",
        help="Skip downloading audio (useful if audio_cache already populated).",
    ),
    strategy_file: Optional[Path] = typer.Option(
        None,
        "--strategy-file",
        help="Path to a previously saved strategy JSON to skip scraping/analysis.",
    ),
) -> None:
    """Run the full IG viral script generation pipeline."""
    _print_banner()

    # --- Lazy imports (so --help is instant without loading heavy deps) ---
    import config
    import scraper as scraper_mod
    import downloader as downloader_mod
    import transcriber as transcriber_mod
    import analyzer as analyzer_mod
    import script_generator as sg_mod
    import exporter as exporter_mod

    # Resolve CLI overrides
    target_list = [t.strip() for t in targets.split(",")] if targets else config.SCRAPE_TARGETS
    _min_views = min_views if min_views is not None else config.MIN_VIEWS
    _max_reels = max_reels if max_reels is not None else config.MAX_REELS_PER_TARGET
    _n_scripts = scripts if scripts is not None else config.SCRIPTS_TO_GENERATE

    # -----------------------------------------------------------------------
    # STAGE 1 — Scrape (or load strategy directly)
    # -----------------------------------------------------------------------
    aggregate_strategy: dict | None = None
    reels: list[scraper_mod.ReelData] = []

    if strategy_file and strategy_file.exists():
        console.print(f"\n[bold]Loading saved strategy from:[/] {strategy_file}")
        aggregate_strategy = json.loads(strategy_file.read_text(encoding="utf-8"))
    else:
        console.print(f"\n[bold]Stage 1 — Scraping[/] targets: {target_list}")
        reels = scraper_mod.scrape_targets(target_list, _max_reels, _min_views)

        if not reels:
            console.print("[red]No reels found. Try lowering --min-views or adding more targets.[/]")
            raise typer.Exit(code=1)

        _show_reels_table(reels)

        # -------------------------------------------------------------------
        # STAGE 2 — Download audio
        # -------------------------------------------------------------------
        audio_map: dict[str, Path] = {}
        if not skip_download:
            console.print(f"\n[bold]Stage 2 — Downloading audio ({len(reels)} reels)[/]")
            audio_map = downloader_mod.download_all(reels, force=force)
        else:
            console.print("\n[yellow]Stage 2 — Skipping audio download (--skip-download)[/]")

        # -------------------------------------------------------------------
        # STAGE 3 — Transcribe
        # -------------------------------------------------------------------
        console.print(f"\n[bold]Stage 3 — Transcribing audio[/]")
        reels = transcriber_mod.transcribe_reels(reels, audio_map, force=force)

        transcribed = sum(1 for r in reels if r.transcript)
        console.print(f"  Transcribed: {transcribed}/{len(reels)} reels")

        if transcribed == 0:
            console.print("[red]No transcripts produced. Cannot continue.[/]")
            raise typer.Exit(code=1)

        # -------------------------------------------------------------------
        # STAGE 4 — Analyse
        # -------------------------------------------------------------------
        console.print(f"\n[bold]Stage 4 — Analysing with Claude[/]")
        aggregate_strategy = analyzer_mod.analyse_batch(reels, niche=niche)

        if aggregate_strategy is None:
            console.print("[red]Analysis failed. Cannot generate scripts.[/]")
            raise typer.Exit(code=1)

        # Save intermediate outputs
        exporter_mod.save_reels_json(reels, niche)
        exporter_mod.save_strategy_json(aggregate_strategy, niche)

    # -----------------------------------------------------------------------
    # STAGE 5 — Generate scripts
    # -----------------------------------------------------------------------
    console.print(f"\n[bold]Stage 5 — Generating {_n_scripts} original scripts[/]")
    generated_scripts = sg_mod.generate_scripts(
        aggregate_strategy,
        niche=niche,
        n=_n_scripts,
        user_instructions=instructions,
    )

    if not generated_scripts:
        console.print("[red]Script generation failed.[/]")
        raise typer.Exit(code=1)

    # -----------------------------------------------------------------------
    # STAGE 6 — Export
    # -----------------------------------------------------------------------
    console.print(f"\n[bold]Stage 6 — Exporting results[/]")
    exporter_mod.save_scripts_text(generated_scripts, niche)
    exporter_mod.save_scripts_json(generated_scripts, niche)

    if sheets:
        exporter_mod.export_to_sheets(generated_scripts, aggregate_strategy, niche)

    # Final preview
    console.print("\n[bold green]Done! Here's a preview of Script #1:[/]")
    console.print(Panel(generated_scripts[0].full_script(), border_style="green"))
    console.print(f"\n[dim]All {len(generated_scripts)} scripts saved to ./{config.OUTPUT_DIR}/[/]")


def _show_reels_table(reels: list) -> None:
    table = Table(title="Top Reels Found", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Username", style="cyan")
    table.add_column("Views", justify="right", style="bold")
    table.add_column("Likes", justify="right")
    table.add_column("URL")

    for i, r in enumerate(reels[:20], 1):
        table.add_row(
            str(i),
            f"@{r.owner_username}",
            f"{r.views:,}",
            f"{r.likes:,}",
            r.url[:60] + "…" if len(r.url) > 60 else r.url,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Alternative: generate scripts from an existing strategy file only
# ---------------------------------------------------------------------------
@app.command("gen")
def generate_only(
    strategy_file: Path = typer.Argument(..., help="Path to a strategy JSON file."),
    niche: str = typer.Option("general", "--niche", "-n"),
    scripts: int = typer.Option(10, "--scripts", "-s"),
    instructions: str = typer.Option("", "--instructions", "-i"),
    sheets: bool = typer.Option(False, "--sheets"),
) -> None:
    """Generate scripts directly from a saved strategy JSON (no scraping needed)."""
    _print_banner()

    import config
    import script_generator as sg_mod
    import exporter as exporter_mod

    if not strategy_file.exists():
        console.print(f"[red]File not found:[/] {strategy_file}")
        raise typer.Exit(code=1)

    strategy = json.loads(strategy_file.read_text(encoding="utf-8"))
    generated_scripts = sg_mod.generate_scripts(strategy, niche=niche, n=scripts, user_instructions=instructions)

    if not generated_scripts:
        raise typer.Exit(code=1)

    exporter_mod.save_scripts_text(generated_scripts, niche)
    exporter_mod.save_scripts_json(generated_scripts, niche)

    if sheets:
        exporter_mod.export_to_sheets(generated_scripts, strategy, niche)

    console.print(Panel(generated_scripts[0].full_script(), border_style="green"))


if __name__ == "__main__":
    app()
