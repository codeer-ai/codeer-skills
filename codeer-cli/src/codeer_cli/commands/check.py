from __future__ import annotations

import sys

from ..client import AuthError, CodeerError


def register(subparsers):
    p = subparsers.add_parser("check", help="Validate auth, workspace, and agent config")
    p.set_defaults(func=run)


def run(args, client) -> int:
    errors = []

    try:
        me = client.get_me()
    except AuthError:
        print("FAIL  Auth: API key missing, invalid, expired, or revoked (401/403)", file=sys.stderr)
        print("      Create an admin workspace API key and export CODEER_API_KEY before running codeer", file=sys.stderr)
        return 1
    except CodeerError as e:
        print(f"FAIL  Auth: {e}", file=sys.stderr)
        return 1

    profile = me.get("profile", {})
    email = me.get("email") or "(unknown)"
    print(f"  OK  Auth: logged in as {email}")

    try:
        ws_id, org_id = client.resolve_scope()
    except CodeerError as e:
        errors.append(f"FAIL  Scope: {e.message if hasattr(e, 'message') else str(e)}")
        ws_id, org_id = None, None

    if ws_id:
        ws_name = _workspace_name(profile, ws_id)
        if ws_name:
            print(f"  OK  Workspace: {ws_name} ({ws_id})")
        else:
            print(f"  OK  Workspace: {ws_id}")

    if org_id:
        print(f"  OK  Organization: {org_id}")

    agent_id = client.agent_id
    if agent_id:
        try:
            agent = client.get(f"/external/agents/{agent_id}")
            print(f"  OK  Agent: {agent.get('name', '(unnamed)')} ({agent_id})")
        except CodeerError:
            errors.append(f"WARN  Agent: ID {agent_id} could not be read (may be in a different workspace)")
    else:
        print("  --  Agent: CODEER_AGENT_ID not set (optional)")

    for err in errors:
        print(err, file=sys.stderr)

    return 1 if any(e.startswith("FAIL") for e in errors) else 0


def _workspace_name(profile: dict, workspace_id: str) -> str | None:
    for ws in profile.get("workspaces", []) or []:
        if str(ws.get("id")) == str(workspace_id):
            return ws.get("name")
    return None
