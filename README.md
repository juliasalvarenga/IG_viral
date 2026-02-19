# IG Viral Scripter

Automatically pull top-performing Instagram reels, transcribe them, extract what makes them go viral, and generate original scripts for your own content.

**Free stack — no paid API keys required. Runs as a web app on Streamlit Cloud.**

```
Scrape (instaloader) → Download audio (yt-dlp) → Transcribe (Groq Whisper) → Analyse (Groq LLM) → Generate scripts (Groq LLM)
```

---

## Deploy to Streamlit Cloud (free, 2 minutes)

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your fork → set **Main file path** to `app.py`
4. Click **Advanced settings → Secrets** and paste:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   IG_USERNAME = "your_ig_username"
   IG_PASSWORD = "your_ig_password"
   ```
5. Click **Deploy** — your app will be live at `https://yourname-ig-viral-app-xxxx.streamlit.app`

Get your free Groq key at [console.groq.com](https://console.groq.com) → API Keys.

---

## Cost breakdown

| Stage | Tool | Cost |
|-------|------|------|
| Scrape Instagram | instaloader + IG account | Free |
| Download audio | yt-dlp | Free |
| Transcribe | Local Whisper model | Free (runs on your machine) |
| Analyse + generate | Groq free tier (Llama 3.3 70B) | Free |
| Export to Sheets | Google Sheets API | Free |

The only thing you need to sign up for is a **free Groq account** at [console.groq.com](https://console.groq.com).

---

## How It Works

| Stage | What happens |
|-------|-------------|
| 1. Scrape | instaloader pulls top video posts for your hashtags / competitor profiles |
| 2. Download | yt-dlp downloads the audio track from each reel |
| 3. Transcribe | Local Whisper model converts audio to text (no API call) |
| 4. Analyse | Groq LLM extracts hook patterns, tone, storytelling structure, power words |
| 5. Generate | Groq LLM writes 10+ original scripts using the extracted strategy |
| 6. Export | Saves everything to `output/` and optionally to a Google Sheet |

---

## Prerequisites

- Python 3.11+
- `ffmpeg` on your PATH (required by yt-dlp for audio conversion)
- An Instagram account (recommended — anonymous scraping gets rate-limited faster)
- A free Groq account

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

The first time you run transcription, the Whisper model weights (~74MB for `base`) will be downloaded automatically to `~/.cache/whisper/`. No action needed.

### 2. Get a free Groq API key

1. Go to [console.groq.com](https://console.groq.com) and create a free account.
2. Under **API Keys**, create a new key and copy it.

### 3. Configure environment variables

```bash
cp .env.example .env
# Open .env and fill in your values
```

Minimum required in `.env`:

```
GROQ_API_KEY=gsk_...          # your Groq key
IG_USERNAME=your_username     # Instagram username (optional but recommended)
IG_PASSWORD=your_password     # Instagram password (optional but recommended)
```

> **Tip:** Use a separate "burner" Instagram account for scraping to protect your main account from rate-limiting.

### 4. (Optional) Google Sheets export

1. Create a Google Cloud service account and download the JSON credentials.
2. Share your Google Sheet with the service account email (Editor role).
3. Add to `.env`:
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

## Whisper model sizes

Set `WHISPER_MODEL_SIZE` in `.env` to trade accuracy for speed:

| Size | Accuracy | CPU speed | Download size |
|------|----------|-----------|---------------|
| `tiny` | Low | ~1x real-time | 39 MB |
| `base` | Good | ~2-4x real-time | 74 MB — **default** |
| `small` | Better | ~4-8x real-time | 244 MB |
| `medium` | Near-API | Slow on CPU | 769 MB |
| `large` | Best | GPU needed | 1550 MB |

---

## Output

All results are saved to the `output/` directory:

| File | Contents |
|------|----------|
| `reels_<niche>_<ts>.json` | Full reel metadata, transcripts, and per-reel analysis |
| `strategy_<niche>_<ts>.json` | Aggregate niche strategy |
| `scripts_<niche>_<ts>.txt` | Human-readable scripts |
| `scripts_<niche>_<ts>.json` | Machine-readable scripts (structured JSON) |

Audio files are cached in `audio_cache/` and transcripts alongside them as `.txt` files. Repeat runs are fast.

---

## Project Structure

```
IG_viral/
├── main.py              # CLI entry point (typer)
├── config.py            # Environment variable loading
├── scraper.py           # instaloader-based Instagram scraper
├── downloader.py        # yt-dlp audio downloader
├── transcriber.py       # Local Whisper transcription
├── analyzer.py          # Groq content analysis (per-reel + aggregate)
├── script_generator.py  # Groq script generation
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

## Known limitations

- **Instagram rate-limiting:** instaloader can get temporarily blocked, especially without credentials or when scraping many posts. The tool adds polite delays and handles this gracefully. If blocked, wait ~1 hour and try again.
- **View count availability:** Instagram doesn't always expose view counts on hashtag pages without login. Profile scraping is more reliable.
- **Groq free tier limits:** Groq has generous free limits (tens of thousands of tokens/minute) but they exist. If you hit them, the tool will print an error and you can retry after a minute.
- **Whisper on CPU:** Transcribing 20 reels with `base` takes roughly 5-15 minutes on CPU. Results are cached — subsequent runs are instant.
