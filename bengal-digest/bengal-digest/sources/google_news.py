import feedparser
import urllib.parse
from datetime import datetime
from models import Article
from utils import clean_text


def fetch_google_news_rss(query: str, lang: str = "bn-IN", limit: int = 10) -> list[Article]:
    gl = lang.split("-")[-1]
    ceid = f"{gl}:{lang.split('-')[0]}"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={lang}&gl={gl}&ceid={ceid}"

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"[google_news] fetch failed for '{query}': {e}")
        return []

    articles = []
    for entry in feed.entries[:limit]:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])

        articles.append(Article(
            source="google_news",
            title=clean_text(entry.get("title", "")),
            url=entry.get("link", ""),
            published_at=published,
            content=clean_text(entry.get("summary")),
            language=lang.split("-")[0],
        ))
    return articles
