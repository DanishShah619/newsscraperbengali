import feedparser
from datetime import datetime
from models import Article
from utils import clean_text

ABP_FEEDS = {
    "home": "https://bengali.abplive.com/home/feed",
    "kolkata": "https://bengali.abplive.com/news/kolkata/feed",
    "states": "https://bengali.abplive.com/states/feed",
    "district": "https://bengali.abplive.com/district/feed",
}


def fetch_abp_rss(section: str = "kolkata", limit: int = 10) -> list[Article]:
    url = ABP_FEEDS.get(section)
    if not url:
        print(f"[abp] unknown section: {section}")
        return []

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"[abp:{section}] fetch failed: {e}")
        return []

    articles = []
    for entry in feed.entries[:limit]:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])

        articles.append(Article(
            source="abp_ananda",
            title=clean_text(entry.get("title", "")),
            url=entry.get("link", ""),
            published_at=published,
            content=clean_text(entry.get("summary")),
            language="bn",
        ))
    return articles


def fetch_abp_rss_multi(sections: list[str] = None, limit_per_section: int = 10) -> list[Article]:
    if sections is None:
        sections = ["kolkata", "district", "states"]
    articles = []
    for s in sections:
        articles += fetch_abp_rss(section=s, limit=limit_per_section)
    return articles
