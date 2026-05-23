from __future__ import annotations

import json
import sys

from ..client import AuthError, CodeerError


def register(subparsers):
    p = subparsers.add_parser("check", help="Validate auth, workspace, and agent config")
    p.add_argument("--json", action="store_true", help="Print machine-readable setup status")
    p.set_defaults(func=run)


def run(args, client) -> int:
    errors = []
    report = {
        "status": "ok",
        "auth": {"ok": False},
        "workspace": {"ok": False},
        "organization": {"ok": False},
        "agent": {"ok": False, "configured": False, "optional": True},
    }

    try:
        me = client.get_me()
    except AuthError:
        if args.json:
            report["status"] = "fail"
            report["auth"]["error"] = "API key missing, invalid, expired, or revoked (401/403)"
            report["next_step"] = "Create an admin workspace API key and export CODEER_API_KEY before running codeer"
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        print("FAIL  Auth: API key missing, invalid, expired, or revoked (401/403)", file=sys.stderr)
        print("      Create an admin workspace API key and export CODEER_API_KEY before running codeer", file=sys.stderr)
        return 1
    except CodeerError as e:
        if args.json:
            report["status"] = "fail"
            report["auth"]["error"] = str(e)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        print(f"FAIL  Auth: {e}", file=sys.stderr)
        return 1

    profile = me.get("profile", {})
    email = me.get("email") or "(unknown)"
    report["auth"] = {"ok": True, "email": email}
    if not args.json:
        print(f"  OK  Auth: logged in as {email}")

    try:
        ws_id, org_id = client.resolve_scope()
    except CodeerError as e:
        errors.append(f"FAIL  Scope: {e.message if hasattr(e, 'message') else str(e)}")
        ws_id, org_id = None, None

    if ws_id:
        ws_name = _workspace_name(profile, ws_id)
        report["workspace"] = {"ok": True, "id": ws_id, "name": ws_name}
        if ws_name:
            if not args.json:
                print(f"  OK  Workspace: {ws_name} ({ws_id})")
        else:
            if not args.json:
                print(f"  OK  Workspace: {ws_id}")

    if org_id:
        report["organization"] = {"ok": True, "id": org_id}
        if not args.json:
            print(f"  OK  Organization: {org_id}")

    agent_id = client.agent_id
    if agent_id:
        report["agent"] = {"ok": False, "configured": True, "optional": True, "id": agent_id}
        try:
            agent = client.get(f"/external/agents/{agent_id}")
            report["agent"].update({"ok": True, "name": agent.get("name", "(unnamed)")})
            if not args.json:
                print(f"  OK  Agent: {agent.get('name', '(unnamed)')} ({agent_id})")
        except CodeerError:
            errors.append(f"WARN  Agent: ID {agent_id} could not be read (may be in a different workspace)")
    else:
        if not args.json:
            print("  --  Agent: CODEER_AGENT_ID not set (optional)")

    if errors:
        report["messages"] = errors
        if any(e.startswith("FAIL") for e in errors):
            report["status"] = "fail"
        elif report["status"] == "ok":
            report["status"] = "warn"

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for err in errors:
            print(err, file=sys.stderr)

    return 1 if any(e.startswith("FAIL") for e in errors) else 0


def _workspace_name(profile: dict, workspace_id: str) -> str | None:
    for ws in profile.get("workspaces", []) or []:
        if str(ws.get("id")) == str(workspace_id):
            return ws.get("name")
    return None
