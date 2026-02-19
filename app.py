"""
IG Viral Scripter — Streamlit web app.

Deploy free at share.streamlit.io by connecting your GitHub repo.
Set secrets in the Streamlit dashboard (GROQ_API_KEY, IG_USERNAME, IG_PASSWORD).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import streamlit as st

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IG Viral Scripter",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_secrets() -> bool:
    """Return True if GROQ_API_KEY is configured."""
    try:
        key = st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
        return bool(key)
    except Exception:
        return bool(os.getenv("GROQ_API_KEY", ""))


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎬 IG Viral Scripter")
    st.caption("Scrape → Transcribe → Analyse → Generate")
    st.divider()

    st.subheader("Targets")
    targets_input = st.text_input(
        "Hashtags or @profiles",
        value="fitness,motivation",
        help="Comma-separated. Use # for hashtags or @ for profiles. E.g. fitness,@hubermanlab",
    )
    niche = st.text_input(
        "Niche label",
        value="fitness motivation",
        help="Describes the content niche — used in AI prompts.",
    )

    st.subheader("Filters")
    min_views = st.number_input(
        "Minimum views",
        min_value=10_000,
        max_value=100_000_000,
        value=1_000_000,
        step=100_000,
        format="%d",
    )
    max_reels = st.slider("Max reels per target", 3, 30, 10)

    st.subheader("Script generation")
    n_scripts = st.slider("Scripts to generate", 3, 20, 10)
    instructions = st.text_area(
        "Custom instructions (optional)",
        placeholder="e.g. Write in a Gen-Z tone. Keep scripts under 45 seconds.",
        height=100,
    )

    st.divider()
    run_btn = st.button("▶  Run Pipeline", type="primary", use_container_width=True)

# ── Main area ────────────────────────────────────────────────────────────────
st.title("IG Viral Scripter")
st.markdown(
    "Pull top Instagram reels → transcribe → extract viral patterns → generate original scripts. "
    "All free using [Groq](https://console.groq.com) + instaloader."
)

if not _check_secrets():
    st.error(
        "**GROQ_API_KEY not set.**\n\n"
        "- **Streamlit Cloud:** Add it in your app's *Settings → Secrets* as `GROQ_API_KEY = \"gsk_...\"`\n"
        "- **Local:** Add `GROQ_API_KEY=gsk_...` to your `.env` file"
    )
    st.stop()

if not run_btn:
    st.info("Configure your targets in the sidebar, then click **▶ Run Pipeline**.")

    with st.expander("How it works"):
        st.markdown("""
| Stage | Tool | Cost |
|-------|------|------|
| Scrape Instagram | instaloader | Free |
| Download audio | yt-dlp | Free |
| Transcribe | Groq Whisper API | Free |
| Analyse patterns | Groq Llama 3.3 70B | Free |
| Generate scripts | Groq Llama 3.3 70B | Free |
        """)
    st.stop()

# ── Pipeline execution ────────────────────────────────────────────────────────
target_list = [t.strip() for t in targets_input.split(",") if t.strip()]

if not target_list:
    st.error("Please enter at least one target.")
    st.stop()

import scraper as scraper_mod
import downloader as downloader_mod
import transcriber as transcriber_mod
import analyzer as analyzer_mod
import script_generator as sg_mod

# Use a temp dir for audio so it works on Streamlit Cloud (no persistent disk)
tmp_dir = Path(tempfile.mkdtemp())

overall = st.progress(0, text="Starting pipeline…")

# ── Stage 1: Scrape ────────────────────────────────────────────────────────
st.subheader("Stage 1 — Scraping Instagram")
scrape_status = st.empty()
reels_placeholder = st.empty()

all_reels: list[scraper_mod.ReelData] = []
seen: set[str] = set()

for idx, target in enumerate(target_list):
    target = target.strip()
    scrape_status.info(f"Scraping **{target}**…")
    try:
        if target.startswith("http") or target.startswith("@"):
            batch = scraper_mod.scrape_by_profile(target, max_reels, min_views)
        else:
            batch = scraper_mod.scrape_by_hashtag(target, max_reels, min_views)
        for r in batch:
            if r.shortcode not in seen:
                seen.add(r.shortcode)
                all_reels.append(r)
    except Exception as exc:
        st.warning(f"Error scraping '{target}': {exc}")

overall.progress(20, text=f"Scraped {len(all_reels)} reels")

if not all_reels:
    st.error("No reels found. Try lowering the minimum views or adding more targets.")
    st.stop()

all_reels.sort(key=lambda r: r.views, reverse=True)
scrape_status.success(f"Found **{len(all_reels)} reels** across {len(target_list)} target(s)")

# Show reels table
reels_data = [
    {
        "Username": f"@{r.owner_username}",
        "Views": f"{r.views:,}",
        "Likes": f"{r.likes:,}",
        "URL": r.url,
    }
    for r in all_reels[:20]
]
reels_placeholder.dataframe(reels_data, use_container_width=True, hide_index=True)

# ── Stage 2: Download audio ───────────────────────────────────────────────
st.subheader("Stage 2 — Downloading audio")
dl_status = st.empty()
dl_bar = st.progress(0)

import yt_dlp as yt_dlp_mod
import hashlib

audio_map: dict[str, Path] = {}

for i, reel in enumerate(all_reels):
    dl_bar.progress((i + 1) / len(all_reels))
    dl_status.info(f"Downloading {i+1}/{len(all_reels)}: @{reel.owner_username}")

    url = reel.video_url or reel.url
    safe_id = hashlib.md5(reel.shortcode.encode()).hexdigest()[:12]
    dest = tmp_dir / f"{safe_id}.mp3"

    if dest.exists():
        audio_map[reel.shortcode] = dest
        continue

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(dest.with_suffix("")),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp_mod.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        audio_map[reel.shortcode] = dest
    except Exception:
        pass  # skip failed downloads silently

dl_status.success(f"Downloaded audio for **{len(audio_map)}/{len(all_reels)} reels**")
overall.progress(40, text="Audio downloaded")

# ── Stage 3: Transcribe ───────────────────────────────────────────────────
st.subheader("Stage 3 — Transcribing audio")
tr_status = st.empty()
tr_bar = st.progress(0)

for i, reel in enumerate(all_reels):
    tr_bar.progress((i + 1) / len(all_reels))
    audio_path = audio_map.get(reel.shortcode)
    if not audio_path:
        continue
    tr_status.info(f"Transcribing {i+1}/{len(all_reels)}: @{reel.owner_username}")
    reel.transcript = transcriber_mod.transcribe_file(audio_path)

transcribed = sum(1 for r in all_reels if r.transcript)
tr_status.success(f"Transcribed **{transcribed}/{len(all_reels)} reels**")
overall.progress(60, text="Transcription complete")

if transcribed == 0:
    st.error("No transcripts produced. Check that ffmpeg is installed and audio downloaded correctly.")
    st.stop()

# ── Stage 4: Analyse ──────────────────────────────────────────────────────
st.subheader("Stage 4 — Analysing with AI")
an_status = st.empty()
an_bar = st.progress(0)

per_reel_results = []
for i, reel in enumerate(all_reels):
    if not reel.transcript:
        continue
    an_bar.progress((i + 1) / len(all_reels))
    an_status.info(f"Analysing {i+1}: @{reel.owner_username} ({reel.views:,} views)")
    result = analyzer_mod.analyse_reel(reel)
    if result:
        reel.analysis = result
        per_reel_results.append(result)

aggregate_strategy: dict | None = None
if per_reel_results:
    an_status.info("Synthesising master strategy…")
    aggregate_strategy = analyzer_mod.analyse_batch(all_reels, niche=niche)

an_status.success(f"Analysis complete — {len(per_reel_results)} reels analysed")
overall.progress(80, text="Analysis complete")

if not aggregate_strategy:
    st.error("Analysis failed. Cannot generate scripts.")
    st.stop()

# ── Stage 5: Generate scripts ─────────────────────────────────────────────
st.subheader("Stage 5 — Generating scripts")
gen_status = st.empty()
gen_status.info(f"Generating {n_scripts} original scripts…")

scripts = sg_mod.generate_scripts(
    aggregate_strategy,
    niche=niche,
    n=n_scripts,
    user_instructions=instructions,
)

gen_status.success(f"Generated **{len(scripts)} original scripts**")
overall.progress(100, text="Pipeline complete!")

# ── Results ───────────────────────────────────────────────────────────────
st.divider()
st.header("Results")

tab_scripts, tab_strategy, tab_reels = st.tabs(["Scripts", "Strategy", "Reel Data"])

with tab_scripts:
    if not scripts:
        st.warning("No scripts were generated.")
    else:
        # Download button for all scripts as text
        all_text = "\n\n" + ("=" * 70 + "\n\n").join(s.full_script() for s in scripts)
        st.download_button(
            "Download all scripts (.txt)",
            data=all_text,
            file_name=f"scripts_{niche.replace(' ', '_')}.txt",
            mime="text/plain",
        )
        st.download_button(
            "Download all scripts (.json)",
            data=json.dumps(
                [{"index": s.index, "hook": s.hook, "hook_type": s.hook_type,
                  "body": s.body, "cta": s.cta, "caption": s.caption,
                  "hashtags": s.hashtags, "duration_s": s.estimated_duration_seconds,
                  "tone": s.tone, "why_it_works": s.why_this_works}
                 for s in scripts],
                indent=2,
            ),
            file_name=f"scripts_{niche.replace(' ', '_')}.json",
            mime="application/json",
        )

        st.divider()
        for script in scripts:
            with st.expander(
                f"Script {script.index} — {script.hook_type.upper()} | ~{script.estimated_duration_seconds}s | {script.tone}",
                expanded=(script.index == 1),
            ):
                st.markdown(f"**Hook:** {script.hook}")
                st.divider()
                st.markdown("**Body:**")
                st.text(script.body)
                st.divider()
                st.markdown(f"**CTA:** {script.cta}")
                st.markdown(f"**Caption:** {script.caption}")
                st.markdown(f"**Hashtags:** {' '.join(script.hashtags)}")
                st.caption(f"Why it works: {script.why_this_works}")

with tab_strategy:
    if aggregate_strategy:
        st.download_button(
            "Download strategy (.json)",
            data=json.dumps(aggregate_strategy, indent=2),
            file_name=f"strategy_{niche.replace(' ', '_')}.json",
            mime="application/json",
        )
        st.json(aggregate_strategy)

with tab_reels:
    reel_rows = []
    for r in all_reels:
        reel_rows.append({
            "Username": f"@{r.owner_username}",
            "Views": r.views,
            "Likes": r.likes,
            "URL": r.url,
            "Has Transcript": bool(r.transcript),
            "Caption (preview)": (r.caption[:80] + "…") if len(r.caption) > 80 else r.caption,
        })
    st.dataframe(reel_rows, use_container_width=True, hide_index=True)
