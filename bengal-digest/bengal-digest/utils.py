import re
import html


def clean_text(text: str) -> str:
    """Strip HTML tags/entities that leak through RSS feeds (e.g. ABP's &lt;p&gt;&lt;strong&gt;)."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()
