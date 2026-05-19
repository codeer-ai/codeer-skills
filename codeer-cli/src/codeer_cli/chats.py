"""Chat creation and SSE-streamed agent responses — the Live Test surface.

The send_message() path is the main dogfood driver: open a chat against a
specific agent version (unpublished draft is fine) and consume the SSE stream
to get tool calls, reasoning, and final text back.
"""

from __future__ import annotations

from typing import Any, Iterator, List, Optional

from .client import CodeerClient


def create(
    client: CodeerClient,
    *,
    agent_id: str,
    title: Optional[str] = None,
    external_user_id: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {"agent_id": agent_id}
    if title is not None:
        body["name"] = title
    if external_user_id is not None:
        body["external_user_id"] = external_user_id
    return client.post("/chats", json=body)


def send_published_agent_message(
    client: CodeerClient,
    *,
    chat_id: int,
    message: str,
    agent_id: str,
    external_user_id: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
    stream: bool = False,
) -> Iterator[dict] | dict:
    """Send a user message through the API-key external chat flow.

    API-key chat endpoints use the agent's published version. They accept
    ``agent_id`` rather than ``agent_history_id``.
    """
    body: dict[str, Any] = {"message": message, "agent_id": agent_id, "stream": stream}
    if external_user_id is not None:
        body["external_user_id"] = external_user_id
    if attachment_ids:
        body["attached_file_uuids"] = attachment_ids

    path = f"/chats/{chat_id}/messages"
    if stream:
        return client.stream_sse("POST", path, json=body)
    return client.post(path, json=body)


def send_message(
    client: CodeerClient,
    *,
    chat_id: int,
    message: str,
    agent_history_id: str,
    attachment_ids: Optional[List[str]] = None,
    stream: bool = True,
) -> Iterator[dict] | dict:
    """Send a user message; yield SSE events (if stream=True) or return the final payload.

    ``agent_history_id`` is required — this is how you pin Live Test to a specific
    (possibly unpublished) agent version without affecting production users.
    """
    body: dict[str, Any] = {"message": message, "agent_history_id": agent_history_id}
    if attachment_ids:
        body["attachment_ids"] = attachment_ids

    path = f"/chats/{chat_id}/messages"
    if stream:
        return client.stream_sse("POST", path, json=body)
    return client.post(path, json=body)


def list_messages(client: CodeerClient, chat_id: int) -> list[dict]:
    return client.get(f"/chats/{chat_id}/messages")


def list_chats(client: CodeerClient) -> list[dict]:
    return client.get("/chats")

