"""Shared helper for reading JSON out of a model's raw reply."""

import json
from typing import Any


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply, tolerating a surrounding markdown fence."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    return json.loads(cleaned)
