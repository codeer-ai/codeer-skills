"""Available LLM model discovery."""

from __future__ import annotations

from typing import Optional

from .client import CodeerClient


def list_available(
    client: CodeerClient,
    *,
    model_type: Optional[str] = None,
) -> list[dict]:
    params = {"model_type": model_type} if model_type else None
    return client.get("/llm/models", params=params)
