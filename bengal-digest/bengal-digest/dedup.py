import os
import numpy as np
from itertools import combinations
import google.generativeai as genai
from models import Article

EMBED_MODEL = "models/gemini-embedding-001"
# Calibrated against real multilingual article pairs (see README for methodology):
# genuine duplicates cluster ~0.73-0.85, unrelated same-topic articles sit ~0.60-0.70.
SIMILARITY_THRESHOLD = 0.78

_genai_configured = False


def _ensure_genai() -> None:
    """Lazily configure the Gemini client on first use (SEC-1)."""
    global _genai_configured
    if not _genai_configured:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=api_key)
        _genai_configured = True


def get_embeddings(texts: list[str]) -> np.ndarray:
    _ensure_genai()
    result = genai.embed_content(model=EMBED_MODEL, content=texts)
    return np.array(result["embedding"])


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity guarded against zero-norm vectors (IMP-3)."""
    norm_a, norm_b = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def dedup_articles(articles: list[Article]) -> list[Article]:
    """Cluster near-duplicate articles across sources/languages, keep the most detailed one per cluster."""
    if len(articles) <= 1:
        return articles

    texts = [f"{a.title}. {(a.content or '')[:200]}" for a in articles]
    try:
        embeddings = get_embeddings(texts)
    except Exception as e:
        print(f"[dedup] embedding call failed, skipping dedup: {e}")
        return articles

    n = len(articles)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for i, j in combinations(range(n), 2):
        if cosine_sim(embeddings[i], embeddings[j]) > SIMILARITY_THRESHOLD:
            union(i, j)

    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    deduped = [
        articles[max(idxs, key=lambda idx: len(articles[idx].content or ""))]
        for idxs in clusters.values()
    ]
    print(f"[dedup] {n} articles -> {len(deduped)} after clustering")
    return deduped
