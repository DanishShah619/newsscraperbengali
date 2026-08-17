# Bengal News Digest Agent

An agentic pipeline that ingests news about West Bengal from four independent sources (BBC Bengali, ABP Ananda, Google News, and Tavily's agentic search), filters for relevance, deduplicates across languages using semantic embeddings, composes a categorized digest with an LLM, and delivers it to Telegram daily - running unattended on a schedule with zero manual intervention.

## Why this isn't just an aggregator

Most "news aggregator" projects stop at fetch-and-display. This pipeline adds three layers of actual judgment:

1. **Relevance filtering** - an LLM call (batched, not per-article) decides whether each article is genuinely about West Bengal specifically, filtering out generic Wikipedia/tourism pages and Bangladesh-focused false positives that keyword matching alone would miss.
2. **Cross-language semantic dedup** - the same news event covered in Bengali (ABP) and English (Google News/BBC) gets recognized as one story via multilingual embedding similarity, not just exact-text matching.
3. **Agentic query planning** (Tavily source) - rather than a fixed search query, the pipeline decides what to search and re-queries with broader terms if initial results are thin.

## Architecture

```
┌─────────────────────────────────────────┐
│  BBC Bengali scraper (Node/Express)      │
│  Deployed on Railway, always-on          │
└──────────────┬────────────────────────────┘
               │ HTTP
┌──────────────▼────────────────────────────┐
│  Python pipeline (Railway Cron Schedule)  │
│                                            │
│  Ingest (4 sources, isolated try/except)  │
│       ↓                                   │
│  Relevance filter (Groq, 1 batched call)  │
│       ↓                                   │
│  Semantic dedup (Gemini embeddings)       │
│       ↓                                   │
│  Seen-article check (Postgres)            │
│       ↓                                   │
│  Compose digest (Groq, groups + summaries)│
│       ↓                                   │
│  Deliver (Telegram, markdown-safe chunks) │
└────────────────────────────────────────────┘
```

## Setup

### 1. BBC scraper service
```bash
git clone https://github.com/faisal-shohag/news-api.git
cd news-api
npm install
```
Deploy to Railway as a Web Service (auto-detects Node). **Pin the Node version** - add to `package.json`:
```json
"engines": { "node": ">=18" }
```
This avoids a real issue encountered during development: some environments default to very old Node versions that don't support modern JS syntax the scraper uses (optional chaining, etc).

Note: the README documents `GET /api/news`, but that route is commented out in the deployed code. Use `GET /api/categories/:id` instead (e.g. `main`, `india`) - see `sources/bbc.py`.

### 2. Python pipeline
```bash
pip install -r requirements.txt
cp .env.example .env  # fill in real keys
```

Deploy to Railway as a second service with **Cron Schedule** set (e.g. `30 3 * * *` = 9:00 AM IST daily - Railway schedules run in UTC). Add a **Postgres** plugin to the project for persistent "seen articles" storage.

### 3. Getting API keys
- **Groq**: console.groq.com → API Keys (free tier, used for relevance filtering + digest composition)
- **Gemini**: aistudio.google.com/apikey (free tier, used for embeddings)
- **Tavily**: app.tavily.com (free tier, agentic search)
- **Telegram bot**: message @BotFather → `/newbot`. Get your chat ID by messaging the bot once, then visiting `https://api.telegram.org/bot<TOKEN>/getUpdates`.

## Debugging journey (things that broke and how they were fixed)

This project surfaced several real infrastructure issues worth documenting, since diagnosing them was as much the work as writing the pipeline itself:

- **HuggingFace deprecated their serverless Inference API** (`api-inference.huggingface.co` → `router.huggingface.co`) mid-development, and free-tier credits for chat models depleted after ~11 calls when checking relevance per-article. Fixed by switching to Groq (genuinely free, fast) and batching relevance checks into a single call instead of one per article.
- **Google deprecated `text-embedding-004`** (migrated to `gemini-embedding-001`, 768-dim → 3072-dim) during development - caught via a standalone cross-language similarity test before trusting it in the full pipeline.
- **Groq's free-tier TPM limit (12k)** was exceeded sending all articles' full content in one compose call - fixed by capping articles-per-digest and truncating content length.
- **The BBC scraper crashed with `SyntaxError: Unexpected token '.'`** - root cause was Colab's default `apt-get install nodejs` installing Node 12, which predates optional chaining (`?.`) syntax the scraper uses. Fixed by using Colab's pre-installed Node 20 binary directly.
- **Dedup threshold calibration** - rather than guessing a similarity cutoff, actual pairwise cosine similarity scores were logged against real duplicate/non-duplicate article pairs to empirically find the right threshold (0.78) rather than assuming a round number would work.
- **Telegram 400 errors** from blind character-count message chunking cutting markdown entities in half - fixed by chunking on paragraph boundaries and adding a plaintext retry fallback.

## Known limitations

- BBC scraper is an unofficial third-party scraper (not BBC's official API) - subject to breaking if BBC changes their page structure.
- Free-tier API limits (Groq, Gemini, Tavily) are adequate for a once-daily digest but not for higher-frequency runs.
- Dedup threshold (0.78) was calibrated against one day's real data - may need periodic recalibration.
