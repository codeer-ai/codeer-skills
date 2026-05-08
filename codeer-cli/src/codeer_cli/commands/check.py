from __future__ import annotations

import os
import sys

from ..client import AuthError, CodeerError


def register(subparsers):
    p = subparsers.add_parser("check", help="Validate auth, workspace, and agent config")
    p.set_defaults(func=run)


def run(args, client) -> int:
    errors = []

    try:
        me = client.get("/accounts/me")
    except AuthError:
        print("FAIL  Auth: session expired or invalid (401/403)", file=sys.stderr)
        print("      Re-grab cookies from Codeer UI -> devtools -> Application -> Cookies", file=sys.stderr)
        return 1
    except CodeerError as e:
        print(f"FAIL  Auth: {e}", file=sys.stderr)
        return 1

    profile = me.get("profile", {})
    email = profile.get("email", "(unknown)")
    print(f"  OK  Auth: logged in as {email}")

    ws_id = client.workspace_id or os.environ.get("CODEER_WORKSPACE_ID")
    org_id = client.organization_id or os.environ.get("CODEER_ORGANIZATION_ID")
    ws_org_map = profile.get("workspace_organization_map", {})

    if not ws_id:
        errors.append("FAIL  Workspace: CODEER_WORKSPACE_ID not set")
        errors.append("      Set it in .claude/settings.json, pass --workspace, or export it in the current shell")
    else:
        ws_name = None
        for ws in profile.get("workspaces", []):
            if str(ws.get("id")) == str(ws_id):
                ws_name = ws.get("name")
                break
        if ws_name:
            print(f"  OK  Workspace: {ws_name} ({ws_id})")
        else:
            errors.append(f"WARN  Workspace: ID {ws_id} not found in your account's workspaces")

    if not org_id:
        if ws_id and str(ws_id) in ws_org_map:
            org_id = str(ws_org_map[str(ws_id)])
            print(f"  OK  Organization: {org_id} (auto-resolved from workspace)")
        else:
            errors.append("FAIL  Organization: CODEER_ORGANIZATION_ID not set and could not auto-resolve")
    else:
        print(f"  OK  Organization: {org_id}")

    agent_id = client.agent_id or os.environ.get("CODEER_AGENT_ID")
    if agent_id:
        try:
            agent = client.get(f"/agents/{agent_id}")
            print(f"  OK  Agent: {agent.get('name', '(unnamed)')} ({agent_id})")
        except CodeerError:
            errors.append(f"WARN  Agent: ID {agent_id} could not be read (may be in a different workspace)")
    else:
        print("  --  Agent: CODEER_AGENT_ID not set (optional)")

    for err in errors:
        print(err, file=sys.stderr)

    return 1 if any(e.startswith("FAIL") for e in errors) else 0
