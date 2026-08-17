import os
import requests

_ALLOWED_SCHEMES = ("https://", "http://localhost", "http://127.0.0.1")

_bbc_base: str | None = None


def _get_bbc_base() -> str:
    """Lazily validate and return BBC_API_BASE (SEC-1, SEC-3)."""
    global _bbc_base
    if _bbc_base is None:
        base = os.environ.get("BBC_API_BASE", "http://localhost:3000/api")
        if not any(base.startswith(s) for s in _ALLOWED_SCHEMES):
            raise RuntimeError(
                f"BBC_API_BASE must start with https:// or http://localhost, got: {base!r}"
            )
        _bbc_base = base.rstrip("/")
    return _bbc_base


# Inline import here avoids circular dependency issues if models/utils are loaded first
from models import Article
from utils import clean_text
import urllib.parse


def fetch_bbc_bengali(category: str = "main", limit: int = 10) -> list[Article]:
    """
    Note: the repo's README documents GET /api/news, but that route is commented
    out in the actual deployed code. Use /api/categories/:id instead - "main" and
    "india" are the most relevant categories for a Bengal-focused digest.
    """
    # SEC-4: URL-encode category to prevent path traversal
    safe_category = urllib.parse.quote(category, safe="")
    try:
        resp = requests.get(f"{_get_bbc_base()}/categories/{safe_category}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[bbc_bengali:{category}] fetch failed: {e}")
        return []

    articles = []
    for item in data.get("articles", [])[:limit]:
        articles.append(Article(
            source="bbc_bengali",
            title=clean_text(item.get("title", "")),
            url=item.get("link", ""),
            published_at=None,
            content=clean_text(item.get("description") or ""),
            language="bn",
        ))
    return articles


def fetch_bbc_bengali_multi(categories: list[str] = None, limit_per_category: int = 10) -> list[Article]:
    """Fetch across multiple categories (main + india recommended for Bengal relevance)."""
    if categories is None:
        categories = ["main", "india"]
    articles = []
    for cat in categories:
        articles += fetch_bbc_bengali(category=cat, limit=limit_per_category)
    return articles
