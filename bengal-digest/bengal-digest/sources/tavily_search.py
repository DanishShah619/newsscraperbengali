import os
import requests
from models import Article
from utils import clean_text
from tavily import TavilyClient

_tavily_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    """Lazily instantiate Tavily client on first use (SEC-1, IMP-6)."""
    global _tavily_client
    if _tavily_client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY environment variable is not set")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


def fetch_tavily(query: str, days: int = 1, limit: int = 10, include_reddit: bool = False) -> list[Article]:
    try:
        kwargs = {
            "query": query,
            "search_depth": "advanced",
            "max_results": limit,
            "days": days,
            "include_raw_content": True,
        }
        if include_reddit:
            kwargs["include_domains"] = ["reddit.com"]
        response = _get_client().search(**kwargs)
    except Exception as e:
        print(f"[tavily] fetch failed for '{query}': {e}")
        return []

    articles = []
    for r in response.get("results", []):
        articles.append(Article(
            source="tavily_reddit" if include_reddit else "tavily_news",
            title=r.get("title", ""),
            url=r.get("url", ""),
            published_at=None,
            content=r.get("content") or r.get("raw_content"),
            language="en",
        ))
    return articles


def plan_and_search(topic: str = "West Bengal") -> list[Article]:
    """The agentic query-planning step: decides what to search, re-queries if thin on results."""
    queries = [f"{topic} latest news", f"{topic} Kolkata"]
    results = []
    for q in queries:
        results += fetch_tavily(q, days=1, limit=8)

    if len(results) < 5:
        results += fetch_tavily(topic, days=3, limit=10)

    return results
