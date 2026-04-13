# 🎙 Podcast Pipeline

A fully configurable, production-grade pipeline that:

1. **Parses an RSS feed** and finds new podcast episodes
2. **Downloads the audio** with retries and size guards
3. **Transcribes the audio** (AssemblyAI, OpenAI Whisper, or Deepgram)
4. **Splits the transcript into chapters** (using provider timestamps *or* an LLM)
5. **Generates a cinematic image prompt** per chapter via an LLM
6. **Generates an image** per chapter (DALL-E 3, Stability AI, or Replicate/Flux)
7. **Posts the images + captions to Telegram** (per-chapter or episode summary)
8. **Tracks state** in SQLite — never re-processes a finished episode

---

## Quick Start

```bash
# 1. Clone / copy the project
git clone https://github.com/yourname/podcast-pipeline.git
cd podcast-pipeline

# 2. Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# → Fill in your API keys in .env

# 5. Configure the pipeline
cp config.yaml config.local.yaml   # optional local overrides
# → Edit config.yaml (or config.local.yaml) with your RSS feed URL, models, etc.

# 6. Run!
python main.py run
```

---

## Configuration Files

| File | Purpose |
|---|---|
| `config.yaml` | All pipeline settings (models, providers, directories, Telegram, etc.) |
| `prompts.yaml` | Every LLM prompt used in the pipeline |
| `.env` | API keys (never commit this) |
| `config.local.yaml` | Optional local overrides (gitignored) |

### `config.yaml` — Key Sections

```yaml
rss:
  feed_url: "https://..."   # Your podcast RSS feed
  max_episodes: 1           # Episodes to process per run

transcription:
  provider: "assemblyai"    # assemblyai | openai_whisper | deepgram

chapters:
  strategy: "both"          # provider | llm | both

image_prompt:
  style_suffix: "..."       # Appended to every image prompt for consistent style

image_generation:
  provider: "openai_dalle"  # openai_dalle | stability_ai | replicate

telegram:
  send_mode: "per_chapter"  # per_chapter | episode_summary
```

### `prompts.yaml` — Customise every LLM instruction

All prompts support template variables like `{podcast_title}`, `{chapter_title}`, etc.
See the file for the full list of available variables per prompt.

---

## CLI Reference

```bash
# Process new episodes from the configured RSS feed
python main.py run

# Override the feed URL on the fly
python main.py run --feed "https://feeds.example.com/other.rss"

# Use a different config file
python main.py --config my_config.yaml run

# Show the status of all tracked episodes
python main.py status

# Force-reprocess an episode by GUID prefix
python main.py reprocess abc123
```

---

## Provider Setup

### Transcription

| Provider | Sign up | API key env var |
|---|---|---|
| **AssemblyAI** (recommended) | https://assemblyai.com | `ASSEMBLYAI_API_KEY` |
| OpenAI Whisper | https://platform.openai.com | `OPENAI_API_KEY` |
| Deepgram | https://deepgram.com | `DEEPGRAM_API_KEY` |

**AssemblyAI is recommended** — it has built-in chapter detection, speaker diarisation, and chapter summarisation, which makes the pipeline significantly more accurate and faster.

### LLM (Chapter Splitting + Image Prompt Generation)

| Provider | Sign up | API key env var |
|---|---|---|
| **Anthropic Claude** (recommended) | https://console.anthropic.com | `ANTHROPIC_API_KEY` |
| OpenAI GPT | https://platform.openai.com | `OPENAI_API_KEY` |
| Google Gemini | https://aistudio.google.com | `GOOGLE_API_KEY` |

### Image Generation

| Provider | Sign up | API key env var |
|---|---|---|
| **DALL-E 3** (recommended) | https://platform.openai.com | `OPENAI_API_KEY` |
| Stability AI | https://platform.stability.ai | `STABILITY_API_KEY` |
| Replicate (Flux) | https://replicate.com | `REPLICATE_API_TOKEN` |

### Telegram

1. Create a bot: message `@BotFather` → `/newbot`
2. Copy the bot token → `TELEGRAM_BOT_TOKEN` in `.env`
3. Add the bot to your group/channel as an admin
4. Get the chat ID: message `@userinfobot` in the group, or use the Telegram API
5. Set `TELEGRAM_CHAT_ID` in `.env` (group IDs are negative: `-1001234567890`)

---

## Project Structure

```
podcast-pipeline/
├── main.py                  # CLI entry point
├── config.yaml              # Main configuration
├── prompts.yaml             # All LLM prompts
├── requirements.txt
├── .env.example             # Template for API keys
└── src/
    ├── __init__.py
    ├── config.py            # Config loader + secret fetcher
    ├── logger.py            # Rich logging setup
    ├── state.py             # SQLite state tracking
    ├── rss_parser.py        # RSS feed parsing
    ├── downloader.py        # Audio download with retries
    ├── transcriber.py       # AssemblyAI / Whisper / Deepgram
    ├── chapter_splitter.py  # Provider chapters or LLM splitting
    ├── image_prompt_generator.py  # LLM → image prompt
    ├── image_generator.py   # DALL-E / Stability / Replicate
    ├── telegram_poster.py   # Telegram Bot API
    └── pipeline.py          # Orchestrator
```

---

## Customising the Image Style

Edit `config.yaml` → `image_prompt.style_suffix` to apply a consistent art style across all generated images:

```yaml
image_prompt:
  style_suffix: "oil painting, Renaissance style, warm amber tones"
```

Or for a modern look:
```yaml
image_prompt:
  style_suffix: "3D render, Unreal Engine 5, volumetric lighting, cyberpunk palette"
```

---

## Troubleshooting

**"No episodes to process"** — Check `max_age_days` in config; set to `0` to disable the age filter.

**AssemblyAI returns no chapters** — Some short episodes don't trigger auto-chapters. Set `chapters.strategy: "llm"` or `"both"` as fallback.

**Telegram rate limit errors** — Increase `telegram.message_delay_seconds` in config.

**DALL-E content policy rejection** — Edit `prompts.yaml` → `image_prompt.system` to add stricter content guidelines, or switch to `stability_ai` / `replicate`.

---

## License

MIT
