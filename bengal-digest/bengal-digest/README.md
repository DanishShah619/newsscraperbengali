# 🗞️ Bengal Digest — AI-Powered Regional News Pipeline

An autonomous, multi-source news aggregation and intelligence pipeline designed for regional news (West Bengal). It ingests articles from multiple Bengali and English sources, performs LLM-powered relevance filtering, deduplicates overlapping stories across languages using semantic vector embeddings, synthesizes a categorized summary, and delivers it daily to Telegram — running 100% serverless and free.

---

## 🌟 Key Features

Unlike standard RSS aggregators that merely dump links, Bengal Digest applies multiple layers of intelligence:

1. **Multi-Source Hybrid Ingestion**
   - **BBC News বাংলা**: Direct Bengali RSS feed ingestion from BBC.
   - **ABP Ananda**: Multi-section RSS scraping (Kolkata, Districts, States).
   - **Google News (Bengali Edition)**: Real-time query-based topic feeds.
   - **Tavily AI Search**: Agentic web search that dynamically expands queries when news coverage is thin.

2. **LLM Relevance Filtering (Groq / LLaMA 3.3 70B)**
   - Single batched LLM pass evaluating all articles simultaneously to eliminate generic wiki entries, spam, tourism guides, or Bangladesh-centric stories that pass simple keyword filters.

3. **Cross-Language Semantic Deduplication (Gemini Embeddings)**
   - Connects articles reporting on the same event in different languages (e.g., Bengali ABP article vs. English Tavily report).
   - Generates multilingual vector embeddings via `gemini-embedding-001` and clusters them using cosine graph union-find (`threshold = 0.78`).

4. **Persistent State & Deduplication (PostgreSQL)**
   - Single-query SHA-256 URL hash verification against historical runs so you never receive duplicate stories across days.

5. **LLM Digest Composition**
   - Synthesizes all new, filtered articles into a structured, mobile-friendly markdown digest with category headings and source links.

6. **Fault-Tolerant Telegram Delivery**
   - Smart chunking on paragraph boundaries to prevent Markdown entity breakage and automatic fallback to plaintext on formatting issues.

---

## 🏗️ Architecture & Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             INGESTION LAYER                                 │
│  [BBC News বাংলা]      [ABP Ananda]      [Google News]     [Tavily Search]  │
└────────┬───────────────────┬───────────────────┬───────────────────┬────────┘
         │                   │                   │                   │
         └───────────────────┼───────────────────┼───────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      STEP 1: BATCH RELEVANCE FILTER                         │
│     Groq (LLaMA 3.3 70B) — Batched JSON evaluation for topic relevance      │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  STEP 2: CROSS-LINGUAL SEMANTIC DEDUP                       │
│     Gemini Embeddings — Cosine similarity clustering (Bengali + English)    │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  STEP 3: HISTORICAL SEEN CHECK (POSTGRES)                   │
│     SHA-256 batch hash lookup against seen_articles table                   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     STEP 4: LLM DIGEST COMPOSITION                          │
│     Groq (LLaMA 3.3 70B) — Categorized, executive summary generation        │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      STEP 5: TELEGRAM DISPATCH                              │
│     Safe-chunked delivery directly to your phone / channel                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- PostgreSQL Database (e.g., free tier on [Neon.tech](https://neon.tech), [Supabase](https://supabase.com), or [Render](https://render.com))

### 2. Required API Keys (All Free Tiers Available)
| Key | Provider | Purpose |
|-----|----------|---------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Relevance filtering & final digest composition |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) | Semantic embeddings for deduplication |
| `TAVILY_API_KEY` | [app.tavily.com](https://app.tavily.com) | Agentic web search |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/botfather) | Bot token for sending messages |
| `TELEGRAM_CHAT_ID` | Telegram User / Channel ID | Destination chat ID |
| `DATABASE_URL` | PostgreSQL | History & run logging |

---

## 💻 Local Setup & Execution

1. **Clone the repository**:
   ```bash
   git clone https://github.com/DanishShah619/newsscraperbengali.git
   cd newsscraperbengali/bengal-digest/bengal-digest
   ```

2. **Create a virtual environment & install dependencies**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux / macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in `bengal-digest/bengal-digest/`:
   ```env
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
   GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx
   TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
   TELEGRAM_BOT_TOKEN=123456789:xxxxxxxxxxxxxxxxxxxx
   TELEGRAM_CHAT_ID=123456789
   DATABASE_URL=postgresql://user:password@host:port/dbname
   ```

4. **Run the pipeline**:
   ```bash
   python run_digest.py
   ```

---

## ☁️ Zero-Cost Automated Cloud Deployment

### Option A: GitHub Actions (Recommended — 100% Free)
A ready-to-run GitHub Actions workflow is included at [`.github/workflows/digest.yml`](../../.github/workflows/digest.yml). It automatically runs on a schedule daily at 03:30 UTC (9:00 AM IST).

1. Go to your GitHub repository: **Settings** ➔ **Secrets and variables** ➔ **Actions**.
2. Add your secrets:
   - `DATABASE_URL`
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY`
   - `TAVILY_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Go to the **Actions** tab, click **Daily Bengal News Digest**, and click **Run workflow** to test!

### Option B: Render / Cloud Cron
A [`render.yaml`](../../render.yaml) configuration is provided for one-click deployment as a managed Cron Job or Blueprint.

---

## 🔮 Future Improvements & Ideas for Extension

If you would like to fork, customize, or expand this project, here are some great feature ideas:

- [ ] **Multi-Topic / Multi-Region Support**: Parameterize the topic (e.g., config file supporting "Odisha", "Assam", "Tech News", or "Global AI") so one instance can run multiple specialized digests.
- [ ] **Custom Delivery Channels**: Add support for Discord Webhooks, WhatsApp Business API, Slack, or Email (via Resend/SendGrid).
- [ ] **Sentiment & Trend Analytics**: Tag articles with sentiment scores or highlight emerging trending entities over a rolling 7-day window.
- [ ] **Web Dashboard**: A lightweight web interface (Next.js or Streamlit) to browse historical digests, search past news, and view run metrics.
- [ ] **Full Article Scraper**: Integrate Trafilatura or Playwright to extract full article bodies when RSS descriptions are too brief.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
