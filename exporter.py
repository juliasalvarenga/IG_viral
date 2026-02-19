"""
Export results to JSON, plain-text, and optionally Google Sheets.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from rich.console import Console

import config
from scraper import ReelData
from script_generator import GeneratedScript

console = Console()

OUTPUT_DIR = Path(config.OUTPUT_DIR)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_reels_json(reels: list[ReelData], niche: str) -> Path:
    """Save reel metadata + per-reel analysis to a JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"reels_{niche}_{_timestamp()}.json"

    data = []
    for r in reels:
        data.append(
            {
                "shortcode": r.shortcode,
                "url": r.url,
                "owner": r.owner_username,
                "views": r.views,
                "likes": r.likes,
                "comments": r.comments,
                "timestamp": r.timestamp,
                "caption": r.caption,
                "transcript": r.transcript,
                "analysis": r.analysis,
            }
        )

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Reels saved:[/] {path}")
    return path


def save_strategy_json(strategy: dict, niche: str) -> Path:
    """Save the aggregate strategy to a JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"strategy_{niche}_{_timestamp()}.json"
    path.write_text(json.dumps(strategy, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Strategy saved:[/] {path}")
    return path


def save_scripts_text(scripts: list[GeneratedScript], niche: str) -> Path:
    """Save all generated scripts as a human-readable text file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"scripts_{niche}_{_timestamp()}.txt"

    lines = [
        f"IG VIRAL SCRIPTER — {len(scripts)} scripts for niche: {niche}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        "",
    ]
    for script in scripts:
        lines.append(script.full_script())
        lines.append("=" * 70)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]Scripts saved:[/] {path}")
    return path


def save_scripts_json(scripts: list[GeneratedScript], niche: str) -> Path:
    """Save all generated scripts as structured JSON."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"scripts_{niche}_{_timestamp()}.json"

    data = [
        {
            "index": s.index,
            "hook": s.hook,
            "hook_type": s.hook_type,
            "body": s.body,
            "cta": s.cta,
            "caption": s.caption,
            "hashtags": s.hashtags,
            "estimated_duration_seconds": s.estimated_duration_seconds,
            "tone": s.tone,
            "why_this_works": s.why_this_works,
        }
        for s in scripts
    ]

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"[green]Scripts JSON saved:[/] {path}")
    return path


def export_to_sheets(
    scripts: list[GeneratedScript],
    strategy: dict | None,
    niche: str,
) -> bool:
    """
    Export scripts (and optionally strategy) to Google Sheets.

    Requires GOOGLE_SERVICE_ACCOUNT_FILE and GOOGLE_SHEET_ID to be set.
    Returns True on success, False otherwise.
    """
    sheet_id = config.GOOGLE_SHEET_ID
    creds_file = config.GOOGLE_SERVICE_ACCOUNT_FILE

    if not sheet_id or not os.path.exists(creds_file):
        console.print(
            "[yellow]Google Sheets export skipped:[/] "
            "Set GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE in .env to enable."
        )
        return False

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)

        # --- Scripts tab ---
        try:
            ws = sh.worksheet("Scripts")
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="Scripts", rows=500, cols=20)

        headers = ["#", "Hook", "Hook Type", "Body", "CTA", "Caption", "Hashtags",
                   "Duration (s)", "Tone", "Why It Works"]
        rows = [headers]
        for s in scripts:
            rows.append([
                s.index,
                s.hook,
                s.hook_type,
                s.body,
                s.cta,
                s.caption,
                " ".join(s.hashtags),
                s.estimated_duration_seconds,
                s.tone,
                s.why_this_works,
            ])
        ws.update(rows)

        # --- Strategy tab ---
        if strategy:
            try:
                ws2 = sh.worksheet("Strategy")
                ws2.clear()
            except gspread.WorksheetNotFound:
                ws2 = sh.add_worksheet(title="Strategy", rows=100, cols=5)

            strategy_rows = [["Key", "Value"]]
            for k, v in strategy.items():
                strategy_rows.append([k, json.dumps(v) if isinstance(v, (list, dict)) else str(v)])
            ws2.update(strategy_rows)

        console.print(f"[green]Exported to Google Sheets:[/] {sheet_id}")
        return True

    except ImportError:
        console.print("[red]gspread / google-auth not installed. Run: pip install gspread google-auth[/]")
        return False
    except Exception as exc:
        console.print(f"[red]Google Sheets export failed:[/] {exc}")
        return False
