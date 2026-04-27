"""Utility functions for research artifact management."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a URL-friendly slug.

    Lowercase, replace spaces/special chars with hyphens, truncate.
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:max_length].rstrip("-")


def create_research_dir(query: str, base_dir: str = "reports") -> str:
    """Create a timestamped research directory and return its path."""
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    slug = slugify(query)
    dir_name = f"{date_str}-{slug}"
    full_path = os.path.join(base_dir, dir_name)
    if os.path.exists(full_path):
        counter = 1
        while os.path.exists(f"{full_path}-{counter}"):
            counter += 1
        full_path = f"{full_path}-{counter}"
    os.makedirs(full_path, exist_ok=True)
    return full_path


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text using a simple regex."""
    return re.findall(r"https?://[^\s\)\]\"'>]+", text)


def save_json(path: str, data: object) -> None:
    """Write data as formatted JSON to a file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_text(path: str, content: str) -> None:
    """Write text content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
