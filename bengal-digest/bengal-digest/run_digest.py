"""
Entrypoint triggered by Railway's Cron Schedule.
Must exit cleanly - Railway skips the next scheduled run if this one is still alive.
"""
import re
from sources.bbc import fetch_bbc_bengali_multi
from sources.abp import fetch_abp_rss_multi
from sources.google_news import fetch_google_news_rss
from sources.tavily_search import plan_and_search
from relevance import filter_relevant
from dedup import dedup_articles
from compose import compose_digest
from deliver import send_telegram_digest
from db import get_conn, ensure_schema, filter_new_articles, mark_seen, log_run

TOPIC = "West Bengal"

# API key prefixes commonly leaked in SDK error messages (SEC-6)
_KEY_PATTERN = re.compile(r"(gsk_|AIzaSy|tvly-|bot\d+:)[A-Za-z0-9_\-]{8,}")


def _sanitise_error(msg: str) -> str:
    """Redact recognisable API key patterns before persisting error to DB (SEC-6)."""
    return _KEY_PATTERN.sub(r"\1<REDACTED>", str(msg))


def ingest_all(topic: str) -> list:
    articles = []

    try:
        articles += fetch_bbc_bengali_multi(categories=["main", "india"], limit_per_category=10)
    except Exception as e:
        print(f"[ingest] BBC source failed entirely: {e}")

    try:
        articles += fetch_abp_rss_multi(sections=["kolkata", "district", "states"], limit_per_section=10)
    except Exception as e:
        print(f"[ingest] ABP source failed entirely: {e}")

    try:
        articles += fetch_google_news_rss(query=topic, lang="bn-IN", limit=15)
    except Exception as e:
        print(f"[ingest] Google News source failed entirely: {e}")

    try:
        articles += plan_and_search(topic=topic)
    except Exception as e:
        print(f"[ingest] Tavily source failed entirely: {e}")

    return articles


def main():
    conn = get_conn()
    ensure_schema(conn)

    try:
        print("Step 1: Ingesting from all sources...")
        articles = ingest_all(TOPIC)
        print(f"Total raw articles: {len(articles)}")

        print("Step 2: Filtering relevance...")
        articles = filter_relevant(articles, topic=TOPIC)

        print("Step 3: Deduplicating...")
        articles = dedup_articles(articles)

        print("Step 4: Checking against seen articles...")
        new_articles = filter_new_articles(conn, articles)
        print(f"New articles: {len(new_articles)}")

        if not new_articles:
            log_run(conn, len(articles), 0, "success_no_new")
            print("No new articles today.")
            return

        print("Step 5: Composing digest...")
        digest_text = compose_digest(new_articles, topic=TOPIC)

        print("Step 6: Delivering...")
        send_telegram_digest(digest_text)

        mark_seen(conn, new_articles)
        log_run(conn, len(articles), len(new_articles), "success")
        print(f"Delivered digest with {len(new_articles)} new articles.")

    except Exception as e:
        log_run(conn, 0, 0, "failed", _sanitise_error(str(e)))
        print(f"Run failed: {e}")
        raise
    finally:
        conn.close()  # required - Railway checks the process actually exits


if __name__ == "__main__":
    main()
