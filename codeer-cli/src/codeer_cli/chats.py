"""Chat V2 creation, structured SSE responses, and persisted message reads."""

from __future__ import annotations

from typing import Any, Iterator, List, Optional

from .client import CodeerClient, TransportError


def create(
    client: CodeerClient,
    *,
    agent_id: str,
    title: Optional[str] = None,
    external_user_id: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {
        "agent_id": agent_id,
        "name": title or "CLI conversation",
    }
    if external_user_id is not None:
        body["external_user_id"] = external_user_id
    return client.post("/chats", api_version="v2", json=body)


def send_published_agent_message(
    client: CodeerClient,
    *,
    chat_id: int,
    message: str,
    agent_id: str,
    external_user_id: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
    stream: bool = True,
    timeout: Optional[float] = None,
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
        return client.stream_sse(
            "POST",
            path,
            api_version="v2",
            json=body,
            timeout=timeout,
        )
    return client.post(path, api_version="v2", json=body, timeout=timeout)


def send_message(
    client: CodeerClient,
    *,
    chat_id: int,
    message: str,
    agent_history_id: str,
    attachment_ids: Optional[List[str]] = None,
    stream: bool = True,
    timeout: Optional[float] = None,
) -> Iterator[dict] | dict:
    """Use legacy Chat V1 to pin an unpublished agent version.

    Chat V2's API-key external flow only accepts the published ``agent_id``.
    Keep this low-level compatibility helper on V1 until V2 supports external
    ``agent_history_id`` pinning. It remains streaming by default.
    """
    body: dict[str, Any] = {
        "message": message,
        "agent_history_id": agent_history_id,
        "stream": stream,
    }
    if attachment_ids:
        body["attachment_ids"] = attachment_ids

    path = f"/chats/{chat_id}/messages"
    if stream:
        return client.stream_sse(
            "POST",
            path,
            json=body,
            timeout=timeout,
        )
    return client.post(path, json=body, timeout=timeout)


def collect_stream(events: Iterator[dict]) -> dict:
    """Collect a Chat V2 SSE stream and require an explicit completion event."""
    raw_events: list[dict] = []
    parts: list[dict] = []
    interactions: list[dict] = []
    text_deltas: list[str] = []
    final_text: str | None = None
    response_id: str | None = None
    conversation_group_id: str | None = None
    updated_title: str | None = None
    completed = False

    for event in events:
        data = event.get("data")
        if data == "[DONE]":
            continue
        raw_events.append(event)
        if not isinstance(data, dict):
            continue

        event_type = str(data.get("type") or event.get("event") or "message")
        response_id = str(data.get("response_id") or response_id or "") or None
        conversation_group_id = str(
            data.get("conversation_group_id") or conversation_group_id or ""
        ) or None

        if event_type == "response.part.delta":
            delta = data.get("delta")
            if data.get("part_kind") == "text" and isinstance(delta, str):
                text_deltas.append(delta)
        elif event_type in ("response.part.created", "response.part.completed"):
            part = data.get("part")
            if isinstance(part, dict):
                parts.append({"event": event_type, "part": part})
                content = part.get("content")
                if (
                    event_type == "response.part.completed"
                    and part.get("part_kind") == "text"
                    and isinstance(content, dict)
                    and isinstance(content.get("content"), str)
                ):
                    final_text = content["content"]
        elif event_type in ("response.interaction.created", "response.interaction.resolved"):
            interactions.append(data)
        elif event_type == "response.chat.title.updated":
            name = data.get("name")
            if isinstance(name, str):
                updated_title = name
        elif event_type == "response.failed":
            message = data.get("message") or "Chat V2 stream failed"
            raise TransportError(
                str(message),
                {
                    "code": data.get("code"),
                    "response_id": response_id,
                    "conversation_group_id": conversation_group_id,
                    "outcome_uncertain": True,
                    "events": raw_events,
                },
            )
        elif event_type == "response.completed":
            completed = True

    if not completed:
        raise TransportError(
            "Chat V2 stream ended before response.completed. Inspect the history before retrying.",
            {
                "response_id": response_id,
                "conversation_group_id": conversation_group_id,
                "outcome_uncertain": True,
                "events": raw_events,
            },
        )

    return {
        "stream": True,
        "completed": True,
        "response_id": response_id,
        "conversation_group_id": conversation_group_id,
        "final_text": final_text if final_text is not None else "".join(text_deltas),
        "updated_title": updated_title,
        "parts": parts,
        "interactions": interactions,
        "events": raw_events,
    }


def list_messages(
    client: CodeerClient,
    chat_id: int,
    *,
    external_user_id: Optional[str] = None,
    limit: int = 500,
) -> dict:
    params: dict[str, Any] = {"limit": limit, "offset": 0}
    if external_user_id is not None:
        params["external_user_id"] = external_user_id
    return client.get(
        f"/chats/{chat_id}/messages",
        api_version="v2",
        params=params,
    )


def list_chats(client: CodeerClient) -> list[dict]:
    """List chats through the legacy v1 endpoint; Chat V2 has no list route."""
    return client.get("/chats")
