from models import Article
from relevance import get_groq_client, GROQ_MODEL

# Groq's free-tier TPM limit (12k as of testing) means we can't send unlimited
# articles in one prompt - cap it and note omissions rather than erroring out.
MAX_ARTICLES_PER_DIGEST = 15
MAX_CONTENT_CHARS = 200


def build_compose_prompt(articles: list[Article], topic: str = "West Bengal") -> str:
    included = articles[:MAX_ARTICLES_PER_DIGEST]
    overflow_count = len(articles) - len(included)

    blocks = []
    for i, a in enumerate(included, 1):
        blocks.append(f"{i}. [{a.source}] {a.title}\nContent: {(a.content or a.title)[:MAX_CONTENT_CHARS]}\nURL: {a.url}")
    joined = "\n\n".join(blocks)

    overflow_note = f"\n\n(Note: {overflow_count} additional minor stories were omitted for length.)" if overflow_count > 0 else ""

    return f"""You are composing a daily news digest about {topic} for a single reader.
Below are today's new, deduplicated, relevant articles.

{joined}{overflow_note}

Instructions:
- Group related articles under short category headers.
- Order groups by importance, most significant first.
- Write 1-2 original sentences per story from the content given - don't just repeat it verbatim.
- Merge articles covering the same event into one entry rather than listing them separately.
- Keep it concise and skimmable - this is read on a phone.
- Include the source URL after each story.
- Do not invent facts not present in the content above.

Write the final digest now, in Markdown with headers."""


def _fallback_flat_digest(articles: list[Article]) -> str:
    """Degrade gracefully to a flat list if the compose model call fails."""
    lines = [f"Bengal News Digest — {len(articles)} new stories\n"]
    for a in articles:
        lines.append(f"\n[{a.source}] {a.title}\n{(a.content or '')[:200]}\n{a.url}")
    return "\n".join(lines)


def compose_digest(articles: list[Article], topic: str = "West Bengal") -> str:
    if not articles:
        return "No new relevant stories today."

    prompt = build_compose_prompt(articles, topic)
    try:
        completion = get_groq_client().chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[compose_digest] failed, falling back: {e}")
        return _fallback_flat_digest(articles)
