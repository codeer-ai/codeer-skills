"""Tiny curl-like CLI for one-off API calls while iterating.

    codeer get /agents/all
    codeer get /agents/all
    codeer post /agents --json-file body.json
    codeer stream post /chats/1/messages --json '{"message":"hi","version_id":"..."}'

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

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codeer")
    sub = parser.add_subparsers(dest="cmd", required=True)

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
        print(f"auth error: {e}", file=sys.stderr)
        return 2

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
