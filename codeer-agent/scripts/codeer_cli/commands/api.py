from __future__ import annotations

import json
import sys
from typing import Any

from ..client import CodeerError


def _load_json(json_str: str | None, json_file: str | None) -> Any:
    if json_file:
        with open(json_file) as fh:
            return json.load(fh)
    if json_str:
        return json.loads(json_str)
    return None


def register(subparsers):
    api = subparsers.add_parser("api", help="Raw API calls (escape hatch)")
    api_sub = api.add_subparsers(dest="method", required=True)

    for method in ("get", "post", "put", "patch", "delete"):
        p = api_sub.add_parser(method)
        p.add_argument("path")
        p.add_argument("--param", action="append", default=[], help="key=value, repeatable")
        if method not in ("get", "delete"):
            p.add_argument("--json", dest="json_str")
            p.add_argument("--json-file")
        p.set_defaults(func=run)

    stream = api_sub.add_parser("stream")
    stream.add_argument("stream_method", choices=["get", "post"], metavar="method")
    stream.add_argument("path")
    stream.add_argument("--json", dest="json_str")
    stream.add_argument("--json-file")
    stream.set_defaults(func=run_stream)


def run(args, client) -> int:
    params = {}
    for kv in getattr(args, "param", []) or []:
        if "=" not in kv:
            print(f"bad --param (expected key=value): {kv}", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        params[k] = v

    body = None
    if args.method in ("post", "put", "patch"):
        body = _load_json(getattr(args, "json_str", None), getattr(args, "json_file", None))

    result = client.request(args.method.upper(), args.path, params=params or None, json=body)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def run_stream(args, client) -> int:
    body = _load_json(getattr(args, "json_str", None), getattr(args, "json_file", None))
    for ev in client.stream_sse(args.stream_method.upper(), args.path, json=body):
        print(json.dumps(ev, ensure_ascii=False))
    return 0
