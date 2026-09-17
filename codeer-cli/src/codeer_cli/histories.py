"""Post-release analysis: read conversation histories and their feedback signals.

Use this after an agent has been published and running for a while, to pull
recent traffic, filter by feedback, and feed the failing cases back into the
evaluation loop.

Pagination: ``/histories`` and the management parts export use ``limit`` +
``offset`` (NOT ``page`` / ``page_size``). History metadata remains a bounded
caller-selected page. The parts export follows every server page and rejects a
cross-page revision change instead of returning a mixed snapshot.
"""

from __future__ import annotations

import builtins
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

    Cost: O(N histories) paginated management parts reads. Filter aggressively via
    ``exclude_users`` and ``limit`` before invoking on a busy agent.
    """
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
        parts = (list_messages(client, hid).get("messages") or [])

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


def list_messages(
    client: CodeerClient,
    history_id: int,
    *,
    limit: int = 100,
) -> dict:
    """Return every persisted diagnostic part through the management export.

    This route is for workspace editors analyzing a History. It is distinct
    from the external client-owner Chat V2 route and must return the explicit
    ``history-parts-v1`` contract. Tool calls and returns are preserved in the
    returned artifact. System prompts and provider raw traces are outside the
    contract.
    """
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    offset = 0
    pages_fetched = 0
    total_records: int | None = None
    part_revision: str | None = None
    result: dict[str, Any] | None = None
    messages: list[dict] = []

    while True:
        page = client.get(
            f"/external/histories/{history_id}/messages",
            params={"limit": limit, "offset": offset},
        )
        if not isinstance(page, dict):
            raise ValueError("History parts response must be an object")
        if page.get("export_contract") != "history-parts-v1":
            raise ValueError("History parts response is missing export_contract=history-parts-v1")

        page_messages = page.get("messages")
        page_info = page.get("page")
        revision = page.get("part_revision")
        if not isinstance(page_messages, builtins.list):
            raise ValueError("History parts response must contain a messages list")
        if not isinstance(page_info, dict):
            raise ValueError("History parts response must contain page metadata")
        if not isinstance(revision, str) or not revision:
            raise ValueError("History parts response must contain part_revision")

        page_offset = page_info.get("offset")
        page_total = page_info.get("total_records")
        page_limit = page_info.get("limit")
        if not all(isinstance(value, int) for value in (page_offset, page_total, page_limit)):
            raise ValueError("History parts page metadata must contain integer limit/offset/total_records")
        if page_offset != offset:
            raise ValueError(f"History parts page offset mismatch: requested {offset}, received {page_offset}")
        if page_total < 0 or page_limit <= 0:
            raise ValueError("History parts page metadata is invalid")

        if total_records is None:
            total_records = page_total
        elif page_total != total_records:
            raise ValueError("History parts total_records changed while paging; retry the export")
        if part_revision is None:
            part_revision = revision
        elif revision != part_revision:
            raise ValueError("History parts changed while paging; retry the export")

        if result is None:
            result = dict(page)
        messages.extend(page_messages)
        pages_fetched += 1
        offset += len(page_messages)

        if offset >= total_records:
            break
        if not page_messages:
            raise ValueError("History parts pagination stopped before total_records was reached")

    assert result is not None
    assert total_records is not None
    result["messages"] = messages
    result["page"] = {
        "limit": result["page"]["limit"],
        "offset": 0,
        "total_records": total_records,
    }
    result["pages_fetched"] = pages_fetched
    return result


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
