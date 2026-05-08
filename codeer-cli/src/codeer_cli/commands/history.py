from __future__ import annotations

import json
import os

from .. import agents as agents_mod
from .. import histories as hist_mod
from ._util import log


def register(subparsers):
    h = subparsers.add_parser("history", help="Conversation history analysis")
    sub = h.add_subparsers(dest="action", required=True)

    # codeer history list
    p = sub.add_parser("list", help="List conversation histories")
    p.add_argument("--agent", default=None)
    p.add_argument("--workspace", default=None)
    p.add_argument("--org", default=None)
    p.add_argument("--user", default=None, help="Filter by external_user_id")
    p.add_argument("--feedback", default=None, help="positive / negative / any")
    p.add_argument("--exclude-users", default=None,
                   help="Comma-separated external_user_ids to exclude")
    p.add_argument("--version", type=int, default=None,
                   help="Filter to histories created while this agent version was live (requires --agent)")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--offset", type=int, default=0)
    p.set_defaults(func=run_list)

    # codeer history get <id>
    p = sub.add_parser("get", help="Get single history metadata")
    p.add_argument("history_id", type=int)
    p.set_defaults(func=run_get)

    # codeer history conversations <id>
    p = sub.add_parser("conversations", help="Get all turns in a history")
    p.add_argument("history_id", type=int)
    p.set_defaults(func=run_conversations)

    # codeer history negative-feedback
    p = sub.add_parser("negative-feedback", help="Surface assistant turns with negative feedback")
    p.add_argument("--agent", required=True)
    p.add_argument("--workspace", default=None)
    p.add_argument("--org", default=None)
    p.add_argument("--exclude-users", default=None,
                   help="Comma-separated external_user_ids to exclude")
    p.add_argument("--limit", type=int, default=500)
    p.set_defaults(func=run_negative_feedback)


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


def run_list(args, client) -> int:
    agent_id = args.agent or os.environ.get("CODEER_AGENT_ID")
    exclude = _parse_exclude(args.exclude_users)

    if args.version is not None and not agent_id:
        log("error: --version requires --agent")
        return 2

    rows = hist_mod.list(
        client,
        agent_id=agent_id,
        workspace_id=args.workspace or os.environ.get("CODEER_WORKSPACE_ID"),
        organization_id=args.org or os.environ.get("CODEER_ORGANIZATION_ID"),
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

    print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
    return 0


def run_get(args, client) -> int:
    result = hist_mod.get(client, args.history_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def run_conversations(args, client) -> int:
    result = hist_mod.get_conversations(client, args.history_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def run_negative_feedback(args, client) -> int:
    exclude = _parse_exclude(args.exclude_users)
    rows = hist_mod.list_negative_feedback_turns(
        client,
        agent_id=args.agent,
        workspace_id=args.workspace or os.environ.get("CODEER_WORKSPACE_ID"),
        organization_id=args.org or os.environ.get("CODEER_ORGANIZATION_ID"),
        exclude_users=exclude,
        limit=args.limit,
    )
    print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
    return 0
