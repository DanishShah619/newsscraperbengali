import os
import time
import hashlib
import psycopg2
from models import Article


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


def get_conn(retries: int = 3, backoff: float = 2.0):
    """Connect to Postgres with exponential-backoff retry.

    Railway's managed Postgres occasionally needs a cold-start moment; retrying
    avoids wasting an entire daily cron run on a transient connection blip.
    """
    db_url = _get_db_url()
    last_exc = None
    for attempt in range(retries):
        try:
            return psycopg2.connect(db_url)
        except psycopg2.OperationalError as exc:
            last_exc = exc
            if attempt < retries - 1:
                wait = backoff ** attempt  # 1s, 2s, 4s
                print(f"[db] connection attempt {attempt + 1} failed, retrying in {wait:.0f}s: {exc}")
                time.sleep(wait)
    raise RuntimeError(f"[db] could not connect after {retries} attempts") from last_exc


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_articles (
    id SERIAL PRIMARY KEY,
    url_hash TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    seen_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS digest_runs (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMP DEFAULT NOW(),
    articles_fetched INT,
    articles_new INT,
    status TEXT,
    error_message TEXT
);
"""


def ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(SCHEMA)
    conn.commit()
    cur.close()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def filter_new_articles(conn, articles: list[Article]) -> list[Article]:
    """Single-query check: fetches all known hashes in one round-trip via ANY()."""
    if not articles:
        return []
    hashes = [url_hash(a.url) for a in articles]
    cur = conn.cursor()
    cur.execute("SELECT url_hash FROM seen_articles WHERE url_hash = ANY(%s)", (hashes,))
    seen = {row[0] for row in cur.fetchall()}
    cur.close()
    return [a for a in articles if url_hash(a.url) not in seen]


def mark_seen(conn, articles: list[Article]) -> None:
    """Batch-insert all seen articles in one executemany call."""
    if not articles:
        return
    rows = [(url_hash(a.url), a.source, a.title) for a in articles]
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO seen_articles (url_hash, source, title) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        rows,
    )
    conn.commit()
    cur.close()


def log_run(conn, fetched: int, new: int, status: str, error: str = None) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO digest_runs (articles_fetched, articles_new, status, error_message) VALUES (%s, %s, %s, %s)",
        (fetched, new, status, error),
    )
    conn.commit()
    cur.close()
