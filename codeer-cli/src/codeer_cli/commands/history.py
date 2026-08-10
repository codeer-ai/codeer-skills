from __future__ import annotations

import json
import math
import os

from .. import agents as agents_mod
from .. import chats as chats_mod
from .. import histories as hist_mod
from ..client import TransportError
from ._util import log, print_json, strip_noisy_fields, truncate, write_json


def register(subparsers):
    h = subparsers.add_parser("history", help="Conversation history analysis")
    sub = h.add_subparsers(dest="action", required=True)

    # codeer history list
    p = sub.add_parser(
        "list",
        help="List conversation histories. Defaults to compact lifecycle fields for LLM context safety.",
    )
    p.add_argument("--agent", default=None)
    p.add_argument("--user", default=None, help="Filter by external_user_id")
    p.add_argument("--feedback", default=None, help="positive / negative / any")
    p.add_argument("--exclude-users", default=None,
                   help="Comma-separated external_user_ids to exclude")
    p.add_argument("--version", type=int, default=None,
                   help="Filter to histories created while this agent version was live (requires --agent)")
    p.add_argument("--limit", type=int, default=50,
                   help="Number of histories to inspect (default: 50; increase deliberately for audits).")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--full", action="store_true",
                   help="Add bounded metadata; complete raw listing should be written with --out.")
    p.add_argument("--out", default=None,
                   help="Write stripped full listing to this file; stdout stays compact.")
    p.set_defaults(func=run_list)

    # codeer history get <id>
    p = sub.add_parser("get", help="Get one history. Defaults to summary; use --full or --out for more.")
    p.add_argument("history_id", type=int)
    p.add_argument("--full", action="store_true",
                   help="Print stripped full history metadata.")
    p.add_argument("--out", default=None,
                   help="Write stripped full history metadata to this file.")
    p.set_defaults(func=run_get)

    # codeer history conversations <id>
    p = sub.add_parser(
        "conversations",
        help="Summarize all Chat V2 parts in a history. Complete parts/tool payloads require --out.",
    )
    p.add_argument("history_id", type=int)
    p.add_argument("--full", action="store_true",
                   help="Require --out and include longer stdout previews; the artifact is always complete.")
    p.add_argument("--out", default=None,
                   help="Write every unmodified client-visible Chat V2 part to this file.")
    p.set_defaults(func=run_conversations)

    # codeer history negative-feedback
    p = sub.add_parser("negative-feedback", help="Surface assistant turns with negative feedback")
    p.add_argument("--agent", required=True)
    p.add_argument("--exclude-users", default=None,
                   help="Comma-separated external_user_ids to exclude")
    p.add_argument("--limit", type=int, default=50,
                   help="Number of histories to scan for feedback (default: 50; increase deliberately).")
    p.add_argument("--full", action="store_true",
                   help="Include longer excerpts; still avoids raw conversation payloads.")
    p.add_argument("--out", default=None,
                   help="Write the same compact negative-feedback rows to this file.")
    p.set_defaults(func=run_negative_feedback)

    # codeer history create --agent <id> --message ...
    p = sub.add_parser("create", help="Create a real persisted conversation history")
    p.add_argument("--agent", default=None, help="Agent ID (defaults to CODEER_AGENT_ID)")
    p.add_argument("--title", default=None, help="Conversation title")
    p.add_argument("--user", default=None, help="external_user_id to associate with the history")
    p.add_argument("--message", action="append", required=True,
                   help="User message to send. Repeat for multi-turn histories.")
    p.add_argument("--timeout", type=float, default=240.0,
                   help="Per-message SSE read timeout in seconds (default: 240).")
    p.add_argument("--out", default=None,
                   help="Write complete create response/conversation artifact to this file; stdout stays compact.")
    p.set_defaults(func=run_create)

    # codeer history send <id> --message ...
    p = sub.add_parser("send", help="Continue an existing persisted conversation history")
    p.add_argument("history_id", type=int)
    p.add_argument("--agent", default=None,
                   help="Agent ID override (defaults to the history's agent or CODEER_AGENT_ID)")
    p.add_argument("--user", default=None,
                   help="external_user_id override (defaults to the history's user)")
    p.add_argument("--message", action="append", required=True,
                   help="User message to send. Repeat to append multiple turns.")
    p.add_argument("--timeout", type=float, default=240.0,
                   help="Per-message SSE read timeout in seconds (default: 240).")
    p.add_argument("--out", default=None,
                   help="Write complete send response/conversation artifact to this file; stdout stays compact.")
    p.set_defaults(func=run_send)


def _parse_exclude(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _version_window(client, agent_id: str, version_number: int) -> tuple[str | None, str | None]:
    """Compute (start, end) ISO timestamps for when a version was the live published one."""
    versions = agents_mod.list_versions(client, agent_id)
    published = sorted(
        [v for v in versions if v.get("was_published") or v.get("status") == "published"],
        key=lambda v: v.get("version_number") or 0,
    )
    target = None
    next_version = None
    for i, v in enumerate(published):
        if v.get("version_number") == version_number:
            target = v
            if i + 1 < len(published):
                next_version = published[i + 1]
            break
    if target is None:
        return None, None
    start = target.get("published_at") or target.get("created_at")
    end = next_version.get("published_at") or next_version.get("created_at") if next_version else None
    return start, end


def _feedback_counts(row: dict) -> dict:
    return row.get("feedback_conversation_counts") or row.get("feedback_counts") or {}


def _history_summary(row: dict, *, full: bool = False) -> dict:
    out = {
        "id": row.get("id"),
        "name": row.get("name") or row.get("title"),
        "agent_id": row.get("agent_id") or (row.get("agent") or {}).get("id"),
        "agent_name": row.get("agent_name") or (row.get("agent") or {}).get("name"),
        "external_user_id": row.get("external_user_id"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "total_cost_credits": row.get("total_cost_credits"),
        "feedback_counts": _feedback_counts(row),
        "snippet_preview": truncate(row.get("snippet") or "", 240),
    }
    if full:
        out["share_type"] = row.get("share_type")
        meta = row.get("meta") or {}
        out["meta"] = {
            "evaluation_mode": meta.get("evaluation_mode"),
            "external_user_id": meta.get("external_user_id"),
            "conversation_agent_id": meta.get("conversation_agent_id"),
            "channel_id": meta.get("channel_id"),
        }
    return out


def _part_summary(part: dict, idx: int, *, full: bool = False) -> dict:
    raw_content = part.get("content")
    if isinstance(raw_content, dict):
        content_value = raw_content.get("content")
        if content_value is None and part.get("part_kind") == "tool-call":
            content_value = raw_content.get("args")
    else:
        content_value = raw_content
    if isinstance(content_value, str):
        content = content_value
    elif content_value is None:
        content = ""
    else:
        content = json.dumps(content_value, ensure_ascii=False, default=str)
    row = {
        "part_idx": idx,
        "id": part.get("id"),
        "conversation_id": part.get("conversation_id"),
        "conversation_group_id": part.get("conversation_group_id"),
        "sequence": part.get("sequence"),
        "part_kind": part.get("part_kind"),
        "source": part.get("source"),
        "created_at": part.get("created_at"),
        "content_preview": truncate(content, 600 if full else 240),
        "content_chars": len(content),
        "attachment_count": len(part.get("attached_files") or []),
        "feedback_count": len(part.get("feedbacks") or []),
    }
    if full:
        row["feedbacks"] = [
            {
                "type": fb.get("type"),
                "tag": fb.get("tag"),
                "content_preview": truncate(fb.get("content") or "", 240),
            }
            for fb in (part.get("feedbacks") or [])
        ]
    return row


def run_list(args, client) -> int:
    agent_id = args.agent or os.environ.get("CODEER_AGENT_ID")
    exclude = _parse_exclude(args.exclude_users)
    workspace_id, organization_id = client.resolve_scope()

    if args.version is not None and not agent_id:
        log("error: --version requires --agent")
        return 2

    rows = hist_mod.list(
        client,
        agent_id=agent_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        external_user_id=args.user,
        feedback_filter=args.feedback,
        exclude_users=exclude,
        limit=args.limit,
        offset=args.offset,
    )

    if args.version is not None:
        start, end = _version_window(client, agent_id, args.version)
        if start is None:
            log(f"error: version {args.version} not found among published versions")
            return 2
        log(f"filtering to version {args.version} window: {start} .. {end or 'now'}")
        filtered = []
        for h in rows:
            created = h.get("created_at") or ""
            if created < start:
                continue
            if end and created >= end:
                continue
            filtered.append(h)
        rows = filtered

    write_json(args.out, strip_noisy_fields(rows))
    print_json([_history_summary(h, full=args.full) for h in rows])
    return 0


def run_get(args, client) -> int:
    result = hist_mod.get(client, args.history_id)
    full_result = strip_noisy_fields(result)
    write_json(args.out, full_result)
    print_json(full_result if args.full else _history_summary(result))
    return 0


def run_conversations(args, client) -> int:
    result = chats_mod.list_messages(client, args.history_id)
    parts = result.get("messages") or []
    if args.full and not args.out:
        log("error: full conversation payloads are unbounded; pass --out <path>")
        return 2
    write_json(args.out, result)
    group_ids = {
        p.get("conversation_group_id")
        for p in parts
        if p.get("conversation_group_id")
    }
    print_json({
        "history_id": args.history_id,
        "turn_count": len(group_ids),
        "part_count": len(parts),
        "wrote_full_detail": bool(args.out),
        "stdout_is_summary": True,
        "parts": [_part_summary(p, i, full=args.full) for i, p in enumerate(parts)],
    })
    return 0


def run_negative_feedback(args, client) -> int:
    exclude = _parse_exclude(args.exclude_users)
    workspace_id, organization_id = client.resolve_scope()
    rows = hist_mod.list_negative_feedback_turns(
        client,
        agent_id=args.agent,
        workspace_id=workspace_id,
        organization_id=organization_id,
        exclude_users=exclude,
        limit=args.limit,
    )
    if args.full:
        for row in rows:
            row["user_message"] = truncate(row.get("user_message") or "", 600)
            row["assistant_excerpt"] = truncate(row.get("assistant_excerpt") or "", 1200)
    write_json(args.out, rows)
    print_json(rows)
    return 0


def _history_url(client, workspace_id: str, history_id: int) -> str:
    base = client.base_url.rstrip("/")
    if base.startswith("https://api."):
        base = "https://" + base[len("https://api."):]
    return f"{base}/workspaces/{workspace_id}/histories/{history_id}"


def _send_messages(
    client,
    *,
    history_id: int,
    agent_id: str,
    external_user_id: str | None,
    messages: list[str],
    timeout: float,
) -> list[dict]:
    results = []
    for idx, message in enumerate(messages, 1):
        log(f"sending turn {idx}/{len(messages)}")
        try:
            stream = chats_mod.send_published_agent_message(
                client,
                chat_id=history_id,
                message=message,
                agent_id=agent_id,
                external_user_id=external_user_id,
                stream=True,
                timeout=timeout,
            )
            if isinstance(stream, dict):
                result = stream
            else:
                result = chats_mod.collect_stream(stream)
        except TransportError as exc:
            body = dict(exc.body) if isinstance(exc.body, dict) else {}
            body.update({"history_id": history_id, "turn": idx, "turn_count": len(messages)})
            raise TransportError(
                f"Failed while sending turn {idx}/{len(messages)} to history {history_id}: {exc.message}",
                body,
            ) from exc
        results.append(result)
    return results


def _valid_timeout(timeout: float) -> bool:
    return math.isfinite(timeout) and timeout > 0


def run_create(args, client) -> int:
    agent_id = args.agent or os.environ.get("CODEER_AGENT_ID")
    if not agent_id:
        log("error: --agent is required or set CODEER_AGENT_ID")
        return 2
    if not _valid_timeout(args.timeout):
        log("error: --timeout must be a finite number greater than zero")
        return 2

    workspace_id, _ = client.resolve_scope()
    title = args.title or (args.message[0].strip()[:80] if args.message else "CLI conversation")

    chat = chats_mod.create(
        client,
        agent_id=agent_id,
        title=title,
        external_user_id=args.user,
    )
    history_id = chat["id"]
    message_results = _send_messages(
        client,
        history_id=history_id,
        agent_id=agent_id,
        external_user_id=args.user,
        messages=args.message,
        timeout=args.timeout,
    )

    chat_messages = chats_mod.list_messages(
        client,
        history_id,
        external_user_id=args.user,
    )
    conversation_parts = chat_messages.get("messages") or []
    out = {
        "agent_id": agent_id,
        "history_id": history_id,
        "external_user_id": args.user,
        "url": _history_url(client, workspace_id, history_id),
        "messages": message_results,
        "conversation_parts": conversation_parts,
    }
    write_json(args.out, out)
    print_json({
        "agent_id": agent_id,
        "history_id": history_id,
        "external_user_id": args.user,
        "url": out["url"],
        "message_count": len(message_results),
        "part_count": len(conversation_parts),
        "wrote_full_detail": bool(args.out),
    })
    return 0


def run_send(args, client) -> int:
    if not _valid_timeout(args.timeout):
        log("error: --timeout must be a finite number greater than zero")
        return 2

    history = hist_mod.get(client, args.history_id)
    history_agent = history.get("agent") or {}
    history_meta = history.get("meta") or {}
    agent_id = (
        args.agent
        or history.get("agent_id")
        or history_agent.get("id")
        or history_meta.get("conversation_agent_id")
        or os.environ.get("CODEER_AGENT_ID")
    )
    if not agent_id:
        log("error: could not resolve agent from history; pass --agent or set CODEER_AGENT_ID")
        return 2

    external_user_id = (
        args.user
        if args.user is not None
        else (
            history.get("external_user_id")
            or history_meta.get("external_user_id")
        )
    )
    workspace_id, _ = client.resolve_scope()
    message_results = _send_messages(
        client,
        history_id=args.history_id,
        agent_id=agent_id,
        external_user_id=external_user_id,
        messages=args.message,
        timeout=args.timeout,
    )
    chat_messages = chats_mod.list_messages(
        client,
        args.history_id,
        external_user_id=external_user_id,
    )
    conversation_parts = chat_messages.get("messages") or []
    out = {
        "agent_id": agent_id,
        "history_id": args.history_id,
        "external_user_id": external_user_id,
        "url": _history_url(client, workspace_id, args.history_id),
        "messages": message_results,
        "conversation_parts": conversation_parts,
    }
    write_json(args.out, out)
    print_json({
        "agent_id": agent_id,
        "history_id": args.history_id,
        "external_user_id": external_user_id,
        "url": out["url"],
        "message_count": len(message_results),
        "part_count": len(conversation_parts),
        "wrote_full_detail": bool(args.out),
    })
    return 0
