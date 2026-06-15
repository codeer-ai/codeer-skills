from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
import sys
from typing import Any

from ..session_client import CodeerSessionClient
from ._util import print_json, write_json


METHODS = ("get", "post", "put", "patch", "delete")


def register(subparsers):
    api = subparsers.add_parser(
        "api",
        help="Raw session-cookie API calls for production or preview platform endpoints",
    )
    api.set_defaults(no_client=True)
    api.add_argument("--env-file", default=None, help="Read CODEER_API_BASE/sessionid/csrftoken from this file")
    api.add_argument("--api-base", default=None, help="Override CODEER_API_BASE")
    api.add_argument("--app-base", default=None, help="Frontend origin for Origin/Referer headers")
    api.add_argument("--timeout", type=float, default=30.0)
    api.add_argument("--unwrap", action="store_true", help="Print envelope.data for Codeer envelope responses")
    api.add_argument("--out", default=None, help="Write the full response JSON to this file too")

    sub = api.add_subparsers(dest="method", required=True)
    for method in METHODS:
        p = sub.add_parser(method, help=f"{method.upper()} a raw platform API path")
        _add_request_args(p)
        p.set_defaults(func=run, no_client=True, request_method=method.upper())

    stream = sub.add_parser("stream", help="Stream an SSE endpoint as JSON lines")
    stream.add_argument("stream_method", choices=("get", "post"), metavar="method")
    _add_request_args(stream, include_files=False)
    stream.set_defaults(func=run_stream, no_client=True)


def _add_request_args(parser, *, include_files: bool = True) -> None:
    parser.add_argument("path", help="API path. /accounts/me becomes /api/v1/accounts/me; /api/... is unchanged.")
    parser.add_argument("--param", action="append", default=[], help="Query param as key=value; repeatable")
    parser.add_argument("--header", action="append", default=[], help="Extra header as key=value; repeatable")
    body = parser.add_mutually_exclusive_group()
    body.add_argument("--json", default=None, help="JSON request body")
    body.add_argument("--json-file", default=None, help="Path to JSON request body")
    parser.add_argument("--form", action="append", default=[], help="Form field as key=value; repeatable")
    if include_files:
        parser.add_argument("--file", action="append", default=[], help="Multipart file as field=path or path")


def run(args, client=None) -> int:
    try:
        params = _parse_pairs(args.param, "--param")
        headers = _parse_pairs(args.header, "--header")
        json_body = _load_json_body(args)
        form = _parse_pairs(args.form, "--form")

        if json_body is not None and (form or getattr(args, "file", [])):
            raise ValueError("--json/--json-file cannot be combined with --form or --file")

        with ExitStack() as stack:
            files = _open_files(stack, getattr(args, "file", []))
            with CodeerSessionClient.from_env(
                env_file=args.env_file,
                api_base=args.api_base,
                app_base=args.app_base,
                timeout=args.timeout,
            ) as session:
                result = session.request(
                    args.request_method,
                    args.path,
                    params=params or None,
                    json=json_body,
                    data=form or None,
                    files=files or None,
                    headers=headers or None,
                    unwrap=args.unwrap,
                )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    write_json(args.out, result)
    print_json(result)
    return 0


def run_stream(args, client=None) -> int:
    try:
        params = _parse_pairs(args.param, "--param")
        headers = _parse_pairs(args.header, "--header")
        json_body = _load_json_body(args)
        form = _parse_pairs(args.form, "--form")
        if json_body is not None and form:
            raise ValueError("--json/--json-file cannot be combined with --form")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    with ExitStack() as stack:
        out = stack.enter_context(Path(args.out).open("w", encoding="utf-8")) if args.out else None
        session = stack.enter_context(CodeerSessionClient.from_env(
            env_file=args.env_file,
            api_base=args.api_base,
            app_base=args.app_base,
            timeout=args.timeout,
        ))
        for event in session.stream_sse(
            args.stream_method.upper(),
            args.path,
            params=params or None,
            json=json_body,
            data=form or None,
            headers=headers or None,
        ):
            line = json.dumps(event, ensure_ascii=False, default=str)
            print(line)
            if out:
                out.write(line + "\n")
    return 0


def _parse_pairs(values: list[str], flag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in values or []:
        if "=" not in raw:
            raise ValueError(f"{flag} expects key=value: {raw}")
        key, value = raw.split("=", 1)
        if not key:
            raise ValueError(f"{flag} has an empty key: {raw}")
        out[key] = value
    return out


def _load_json_body(args) -> Any:
    if args.json_file:
        return json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    if args.json is not None:
        return json.loads(args.json)
    return None


def _open_files(stack: ExitStack, values: list[str]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for raw in values or []:
        if "=" in raw:
            field, path_raw = raw.split("=", 1)
            if not field:
                raise ValueError(f"--file has an empty field: {raw}")
        else:
            field, path_raw = "file", raw
        path = Path(path_raw)
        handle = stack.enter_context(path.open("rb"))
        files[field] = (path.name, handle)
    return files
