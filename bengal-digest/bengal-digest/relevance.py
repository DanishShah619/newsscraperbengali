import os
import re
import json
from groq import Groq
from models import Article

GROQ_MODEL = "llama-3.3-70b-versatile"

_groq_client: Groq | None = None


def get_groq_client() -> Groq:
    """Lazily initialise the Groq client on first use (SEC-1)."""
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def build_relevance_batch_prompt(articles: list[Article], topic: str) -> str:
    lines = [f"{i}: {a.title} — {(a.content or '')[:150].strip()}" for i, a in enumerate(articles)]
    joined = "\n".join(lines)
    return f"""Below is a numbered list of article titles and snippets. For each, decide if it is
genuinely about {topic} specifically (current politics, people, places, culture, or events) —
NOT a generic wiki/tourism/reference page, NOT primarily about Bangladesh, NOT a homepage/section listing.

{joined}

Respond with ONLY a JSON array of the relevant numbers, nothing else. Example: [0, 2, 5, 7]"""


def filter_relevant(articles: list[Article], topic: str = "West Bengal") -> list[Article]:
    """Single batched call for all articles - avoids per-article API cost."""
    if not articles:
        return []

    prompt = build_relevance_batch_prompt(articles, topic)
    try:
        completion = get_groq_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )
        raw = completion.choices[0].message.content.strip()
        match = re.search(r"\[[\d,\s]*\]", raw)
        if not match:
            print(f"[relevance] could not parse JSON array from model response, keeping all. Raw: {raw!r}")
            return articles  # fail-safe: don't drop everything on parse failure
        relevant_indices = set(json.loads(match.group()))
    except Exception as e:
        print(f"[relevance] batch check failed, keeping all: {e}")
        return articles  # fail-safe: don't drop everything on API error

    relevant = [a for i, a in enumerate(articles) if i in relevant_indices]
    print(f"[relevance] {len(articles)} -> {len(relevant)} relevant")
    return relevant
