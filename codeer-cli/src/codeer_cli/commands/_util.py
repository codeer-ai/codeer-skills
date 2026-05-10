from __future__ import annotations

import sys


def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def truncate(text: str, n: int = 60) -> str:
    text = text.replace("\n", " ").strip()
    return text[:n] + "..." if len(text) > n else text
