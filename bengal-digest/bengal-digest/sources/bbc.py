import feedparser
import requests
import os
from datetime import datetime
from models import Article
from utils import clean_text

BBC_BENGALI_RSS = "https://feeds.bbci.co.uk/bengali/rss.xml"
BBC_API_BASE = os.environ.get("BBC_API_BASE")


def fetch_bbc_bengali(limit: int = 15) -> list[Article]:
    """
    Fetches news directly from BBC News বাংলা official RSS feed.
    If BBC_API_BASE is explicitly configured to a custom scraper service,
    it falls back to checking the custom API.
    """
    articles = []

    # 1. Primary: Direct BBC News বাংলা official RSS feed (Fast, reliable, zero server needed)
    try:
        feed = feedparser.parse(BBC_BENGALI_RSS)
        for entry in feed.entries[:limit]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            articles.append(Article(
                source="bbc_bengali",
                title=clean_text(entry.get("title", "")),
                url=entry.get("link", ""),
                published_at=published,
                content=clean_text(entry.get("summary") or entry.get("description") or ""),
                language="bn",
            ))
        if articles:
            return articles
    except Exception as e:
        print(f"[bbc_bengali:rss] RSS fetch failed: {e}")

    # 2. Secondary fallback: Custom deployed Node API (if user explicitly provided BBC_API_BASE)
    if BBC_API_BASE and not BBC_API_BASE.startswith("http://localhost"):
        try:
            resp = requests.get(f"{BBC_API_BASE.rstrip('/')}/categories/main", timeout=10)
            if resp.ok:
                data = resp.json()
                for item in data.get("articles", [])[:limit]:
                    articles.append(Article(
                        source="bbc_bengali",
                        title=clean_text(item.get("title", "")),
                        url=item.get("link", ""),
                        published_at=None,
                        content=clean_text(item.get("description") or ""),
                        language="bn",
                    ))
        except Exception as e:
            print(f"[bbc_bengali:custom_api] fallback failed: {e}")

    return articles


def fetch_bbc_bengali_multi(categories: list[str] = None, limit_per_category: int = 10) -> list[Article]:
    return fetch_bbc_bengali(limit=limit_per_category * 2)
