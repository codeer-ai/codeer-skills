from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def truncate(text: str, n: int = 60) -> str:
    text = text.replace("\n", " ").strip()
    return text[:n] + "..." if len(text) > n else text


NOISY_KEYS = {
    "avatar",
    "brand",
    "creator",
    "default_organization_id",
    "default_scopes",
    "default_workspace_id",
    "is_owner",
    "members",
    "my_permissions",
    "owner",
    "profile",
    "source_creator",
    "user_role",
    "workspace_organization_map",
}


def strip_noisy_fields(value: Any) -> Any:
    """Remove server/account metadata that is not useful for agent lifecycle work."""
    if isinstance(value, list):
        return [strip_noisy_fields(item) for item in value]
    if not isinstance(value, dict):
        return value

    out = {}
    for key, item in value.items():
        if key in NOISY_KEYS:
            continue
        if key == "workspace" and isinstance(item, dict):
            out[key] = {
                k: item.get(k)
                for k in ("id", "name", "organization_id")
                if item.get(k) is not None
            }
            continue
        out[key] = strip_noisy_fields(item)
    return out


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def write_json(path: str | None, value: Any) -> None:
    if not path:
        return
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    log(f"wrote full detail to {path}")
