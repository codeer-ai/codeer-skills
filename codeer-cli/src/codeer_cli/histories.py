"""Post-release analysis: read conversation histories and their feedback signals.

Use this after an agent has been published and running for a while, to pull
recent traffic, filter by feedback, and feed the failing cases back into the
evaluation loop.

Pagination: ``/histories`` uses ``limit`` + ``offset`` (NOT ``page`` /
``page_size``). Default ``limit=500`` here is a deliberate choice for analysis
workflows — the backend caps responses anyway and returning everything in one
call removes a common foot-gun where the caller silently truncates at 10.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from .client import CodeerClient


def list(
    client: CodeerClient,
    *,
    agent_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    external_user_id: Optional[str] = None,
    feedback_filter: Optional[str] = None,
    exclude_users: Iterable[str] = (),
    limit: int = 500,
    offset: int = 0,
    order_by: str = "desc",
) -> list[dict]:
    """List conversation histories, optionally filtered by agent and feedback state.

    ``exclude_users`` filters out histories whose ``external_user_id`` matches
    any of the given values (case-insensitive). Use this to exclude internal
    testing accounts from production analysis.

    feedback_filter values are defined by FeedbackFilterType in the backend —
    typical values include 'positive' / 'negative' / 'any'. Check the current
    enum before assuming.
    """
    params: dict[str, Any] = {"limit": limit, "offset": offset, "order_by": order_by}
    if agent_id:
        params["agent_id"] = agent_id
    if external_user_id:
        params["external_user_id"] = external_user_id
    if feedback_filter:
        params["feedback_filter"] = feedback_filter
    rows = client.get("/external/histories", params=params)
    drop = {e.lower() for e in exclude_users}
    if drop:
        rows = [h for h in rows if (h.get("external_user_id") or "").lower() not in drop]
    return rows


def list_negative_feedback_turns(
    client: CodeerClient,
    *,
    agent_id: str,
    workspace_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    exclude_users: Iterable[str] = (),
    feedback_types: Iterable[str] = ("sys_improve",),
    limit: int = 500,
    user_excerpt_chars: int = 200,
    assistant_excerpt_chars: int = 400,
) -> list[dict]:
    """Walk every (filtered) history and surface assistant turns flagged by users.

    Returns a flat list of dicts, one per matching turn:
        {
            "history_id": int,
            "history_title": str,
            "external_user_id": str,
            "created_at": str,
            "turn_idx": int,
            "feedback_type": str,       # 'sys_improve' / 'sys_helpful' / etc.
            "feedback_text": str,
            "user_message": str,        # the user turn that preceded this assistant
            "assistant_excerpt": str,   # the assistant text (tool markers stripped)
        }

    Designed for "what's failing in production?" analysis: piping the result
    straight into a dataframe / spreadsheet should let you cluster failure
    modes without ever loading raw conversation JSON.

    The conversation feedback row shape is::

        {"id": N, "tag": "system", "type": "sys_improve",
         "identity": {...}, "content": "...", "created_at": "..."}

    The user-meaningful sentiment lives in ``type`` (NOT ``tag``, which is
    the source channel — usually "system"). Pass the desired sentiment(s)
    in ``feedback_types``.

    Cost: O(N histories) paginated Chat V2 reads. Filter aggressively via
    ``exclude_users`` and ``limit`` before invoking on a busy agent.
    """
    from . import chats

    type_set = {t.lower() for t in feedback_types}
    histories = list(
        client,
        agent_id=agent_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        exclude_users=exclude_users,
        limit=limit,
    )
    out: list[dict] = []
    for h in histories:
        hid = h.get("id")
        if hid is None:
            continue
        try:
            parts = (chats.list_messages(client, hid).get("messages") or [])
        except Exception:
            continue

        turn_indexes: dict[str, int] = {}
        user_messages: dict[str, str] = {}
        next_turn_idx = 0
        for part_idx, part in enumerate(parts):
            group_id = str(part.get("conversation_group_id") or "")
            part_kind = part.get("part_kind") or ""
            if group_id and group_id not in turn_indexes:
                turn_indexes[group_id] = next_turn_idx
                next_turn_idx += 1
            if part_kind == "user-prompt":
                user_messages[group_id] = _part_text(part)
                continue
            if part_kind != "text":
                continue
            fbs = part.get("feedbacks") or []
            for fb in fbs:
                ftype = (fb.get("type") or "").lower()
                if ftype not in type_set:
                    continue
                out.append({
                    "history_id": hid,
                    "history_title": h.get("name") or h.get("title") or "",
                    "external_user_id": h.get("external_user_id") or "",
                    "created_at": h.get("created_at"),
                    "turn_idx": turn_indexes.get(group_id),
                    "part_idx": part_idx,
                    "conversation_group_id": group_id or None,
                    "conversation_part_id": part.get("id"),
                    "feedback_type": ftype,
                    "feedback_text": fb.get("content") or "",
                    "user_message": user_messages.get(group_id, "")[:user_excerpt_chars],
                    "assistant_excerpt": _part_text(part)[:assistant_excerpt_chars],
                })
    return out


def get(client: CodeerClient, history_id: int) -> dict:
    return client.get(f"/external/histories/{history_id}")


def get_conversations(client: CodeerClient, history_id: int) -> list[dict]:
    """Return legacy V1 conversation rows.

    Prefer ``codeer_cli.chats.list_messages`` whenever exact Chat V2 parts,
    tool inputs/results, or event order matter.
    """
    return client.get(f"/external/histories/{history_id}/conversations")


def _part_text(part: dict) -> str:
    content = part.get("content")
    if isinstance(content, dict):
        value = content.get("content")
    else:
        value = content
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)
