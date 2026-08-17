from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    source: str
    title: str
    url: str
    published_at: Optional[datetime]
    content: Optional[str]
    language: str
    summary: Optional[str] = None
