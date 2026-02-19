# IG Viral Scripter

Automatically pull top-performing Instagram reels, transcribe them, extract what makes them go viral, and generate original scripts for your own content — all from one command.

```
Scrape (Apify) → Download audio (yt-dlp) → Transcribe (Whisper) → Analyse (Claude) → Generate scripts (Claude)
```

---

## How It Works

| Stage | Tool | What happens |
|-------|------|--------------|
| 1. Scrape | Apify Instagram Scraper | Pulls top reels for your hashtags / competitor profiles, filtered by view count |
| 2. Download | yt-dlp | Downloads the audio track from each reel |
| 3. Transcribe | OpenAI Whisper | Converts audio to text |
| 4. Analyse | Claude | Extracts hook patterns, tone, storytelling structure, power words |
| 5. Generate | Claude | Writes 10+ original scripts using the extracted strategy |
| 6. Export | Files + Google Sheets | Saves everything to `output/` and optionally to a Google Sheet |

---

## Prerequisites

- Python 3.11+
- `ffmpeg` installed and on your PATH (required by yt-dlp for audio conversion)
- API keys for Apify, Anthropic, and OpenAI

### Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required keys in `.env`:

```
APIFY_API_TOKEN=...      # https://console.apify.com/account/integrations
ANTHROPIC_API_KEY=...    # https://console.anthropic.com/
OPENAI_API_KEY=...       # https://platform.openai.com/api-keys
```

### 3. (Optional) Google Sheets export

1. Create a Google Cloud service account and download the JSON credentials file.
2. Share your target Google Sheet with the service account email.
3. Set in `.env`:
   ```
   GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
   GOOGLE_SHEET_ID=<sheet_id_from_url>
   ```

---

## Usage

### Full pipeline (recommended)

```bash
python main.py \
  --targets fitness,motivation \
  --niche "fitness motivation" \
  --min-views 1000000 \
  --max-reels 20 \
  --scripts 10
```

### Scrape a competitor's profile

```bash
python main.py \
  --targets @hubermanlab,@garyvee \
  --niche "health and wellness" \
  --min-views 500000
```

### Add custom instructions for script generation

```bash
python main.py \
  --targets entrepreneur \
  --niche "entrepreneurship" \
  --instructions "Write in a conversational, Gen-Z tone. Avoid buzzwords like 'hustle'."
```

### Export to Google Sheets

```bash
python main.py --targets fitness --niche fitness --sheets
```

### Generate new scripts from a previously saved strategy (no scraping)

Useful once you've already analysed a niche and just want fresh scripts:

```bash
python main.py gen output/strategy_fitness_20240601_120000.json \
  --niche fitness \
  --scripts 15
```

### Skip audio download (if `audio_cache/` is already populated)

```bash
python main.py --targets fitness --niche fitness --skip-download
```

### Force re-download and re-transcribe

```bash
python main.py --targets fitness --niche fitness --force
```

---

## Output

All results are saved to the `output/` directory:

| File | Contents |
|------|----------|
| `reels_<niche>_<ts>.json` | Full reel metadata, transcripts, and per-reel analysis |
| `strategy_<niche>_<ts>.json` | Aggregate niche strategy extracted by Claude |
| `scripts_<niche>_<ts>.txt` | Human-readable scripts (one per section) |
| `scripts_<niche>_<ts>.json` | Machine-readable scripts (structured JSON) |

Audio files are cached in `audio_cache/` and transcripts alongside them as `.txt` files. Repeat runs are fast.

---

## Project Structure

```
IG_viral/
├── main.py              # CLI entry point (typer)
├── config.py            # Environment variable loading
├── scraper.py           # Apify Instagram scraper integration
├── downloader.py        # yt-dlp audio downloader
├── transcriber.py       # OpenAI Whisper transcription
├── analyzer.py          # Claude content analysis (per-reel + aggregate)
├── script_generator.py  # Claude script generation
├── exporter.py          # File + Google Sheets export
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## CLI Reference

### `python main.py` (full pipeline)

| Flag | Default | Description |
|------|---------|-------------|
| `--targets`, `-t` | from `.env` | Comma-separated hashtags or @profiles |
| `--niche`, `-n` | `general` | Niche label used in prompts |
| `--min-views`, `-v` | 1,000,000 | Minimum view count |
| `--max-reels`, `-m` | 20 | Max reels per target |
| `--scripts`, `-s` | 10 | Scripts to generate |
| `--instructions`, `-i` | — | Extra prompt instructions |
| `--sheets` | off | Export to Google Sheets |
| `--force`, `-f` | off | Re-download + re-transcribe cached files |
| `--skip-download` | off | Skip audio download stage |
| `--strategy-file` | — | Load saved strategy, skip scraping |

### `python main.py gen <strategy_file>`

Generate scripts from an existing strategy JSON without scraping.

---

## Notes

- Apify charges per actor run. Each call to `instagram-scraper` consumes platform credits. Monitor your usage at [console.apify.com](https://console.apify.com).
- OpenAI Whisper is billed per audio-minute. Audio files are cached so each reel is only transcribed once.
- Claude API calls are billed per token. Aggregate analysis on 20 reels typically uses ~15k–30k tokens.
- This tool is intended for competitive research and content ideation. Use it responsibly and in accordance with Instagram's Terms of Service.
