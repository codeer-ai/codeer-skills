from __future__ import annotations

import json
import sys

def register(subparsers):
    api = subparsers.add_parser("api", help="Read-only API calls")
    api_sub = api.add_subparsers(dest="method", required=True)

    p = api_sub.add_parser("get")
    p.add_argument("path")
    p.add_argument("--param", action="append", default=[], help="key=value, repeatable")
    p.set_defaults(func=run)

    stream = api_sub.add_parser("stream")
    stream.add_argument("stream_method", choices=["get"], metavar="method")
    stream.add_argument("path")
    stream.set_defaults(func=run_stream)


def run(args, client) -> int:
    params = {}
    for kv in getattr(args, "param", []) or []:
        if "=" not in kv:
            print(f"bad --param (expected key=value): {kv}", file=sys.stderr)
            return 2
        k, v = kv.split("=", 1)
        params[k] = v

    result = client.request("GET", args.path, params=params or None)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def run_stream(args, client) -> int:
    for ev in client.stream_sse(args.stream_method.upper(), args.path):
        print(json.dumps(ev, ensure_ascii=False))
    return 0
