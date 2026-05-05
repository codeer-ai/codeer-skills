"""Tiny curl-like CLI for one-off API calls while iterating.

    codeer get /agents/all
    codeer get /agents/all --param wid=<workspace-id>
    codeer post /agents --json-file body.json
    codeer stream post /chats/1/messages --json '{"message":"hi","agent_history_id":"..."}'

For anything repeated or scripted, import the typed helpers
(`from codeer_cli import agents, kb, eval_, histories, chats`) instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .client import AuthError, CodeerClient, CodeerError


def _load_json(json_str: str | None, json_file: str | None) -> Any:
    if json_file:
        with open(json_file) as fh:
            return json.load(fh)
    if json_str:
        return json.loads(json_str)
    return None


def _run_check(client: CodeerClient) -> int:
    """Validate auth + workspace config, print active identity."""
    errors = []

    # 1. Auth check
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

    # 2. Workspace / org check
    ws_id = client.workspace_id or os.environ.get("CODEER_WORKSPACE_ID")
    org_id = client.organization_id or os.environ.get("CODEER_ORGANIZATION_ID")
    ws_org_map = profile.get("workspace_organization_map", {})

    if not ws_id:
        errors.append("FAIL  Workspace: CODEER_WORKSPACE_ID not set")
        errors.append("      Set it in .claude/settings.json env block for this project")
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

    # 3. Agent ID (optional)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codeer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Validate auth, workspace, and agent config")

    for method in ("get", "post", "put", "patch", "delete"):
        p = sub.add_parser(method)
        p.add_argument("path")
        p.add_argument("--param", action="append", default=[], help="key=value, repeatable")
        if method != "get" and method != "delete":
            p.add_argument("--json", dest="json_str")
            p.add_argument("--json-file")

    stream = sub.add_parser("stream")
    stream.add_argument("method", choices=["get", "post"])
    stream.add_argument("path")
    stream.add_argument("--json", dest="json_str")
    stream.add_argument("--json-file")

    args = parser.parse_args(argv)

    try:
        client = CodeerClient.from_env()
    except AuthError as e:
        if args.cmd == "check":
            print(f"FAIL  Auth: {e}", file=sys.stderr)
            print("      Create ~/.codeer/session.env with CODEER_API_BASE, CODEER_SESSION_ID, CODEER_CSRF_TOKEN", file=sys.stderr)
            return 1
        print(f"auth error: {e}", file=sys.stderr)
        return 2

    if args.cmd == "check":
        try:
            return _run_check(client)
        finally:
            client.close()

    params = {}
    for kv in getattr(args, "param", []) or []:
        if "=" not in kv:
            print(f"bad --param (expected key=value): {kv}", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        params[k] = v

    try:
        if args.cmd == "stream":
            body = _load_json(args.json_str, args.json_file)
            for ev in client.stream_sse(args.method.upper(), args.path, json=body):
                print(json.dumps(ev, ensure_ascii=False))
            return 0

        body = None
        if args.cmd in ("post", "put", "patch"):
            body = _load_json(getattr(args, "json_str", None), getattr(args, "json_file", None))

        result = client.request(args.cmd.upper(), args.path, params=params or None, json=body)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0

    except AuthError as e:
        print(f"auth: {e}", file=sys.stderr)
        return 3
    except CodeerError as e:
        print(f"error: {e}", file=sys.stderr)
        if e.body:
            print(json.dumps(e.body, ensure_ascii=False, indent=2, default=str), file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
