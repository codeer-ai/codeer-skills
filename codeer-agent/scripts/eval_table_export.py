#!/usr/bin/env python3
"""Export a Codeer eval table without uv or third-party dependencies.

This script intentionally uses only the Python standard library. It is meant
for read-only eval-table pulls from any customer directory without touching
uv's package cache.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
                os.environ[key] = value


def _load_project_settings() -> None:
    """Load .claude/settings.json env from cwd or ancestors when available."""
    for root in [Path.cwd(), *Path.cwd().parents]:
        path = root / ".claude" / "settings.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise SystemExit(f"invalid JSON in {path}: {e}") from e
        env = data.get("env") or {}
        if not isinstance(env, dict):
            return
        for key, value in env.items():
            if key and key not in os.environ:
                os.environ[key] = str(value)
        return


def _load_env() -> None:
    explicit = os.environ.get("CODEER_ENV_FILE")
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(Path.home() / ".codeer" / "session.env")
    candidates.append(Path.cwd() / ".env")
    for candidate in candidates:
        if candidate.exists():
            _load_dotenv(candidate)
            break


class Client:
    def __init__(self) -> None:
        _load_env()
        missing = [
            key
            for key in ("CODEER_API_BASE", "CODEER_SESSION_ID", "CODEER_CSRF_TOKEN")
            if not os.environ.get(key)
        ]
        if missing:
            raise SystemExit(f"missing required env vars: {', '.join(missing)}")
        self.base = os.environ["CODEER_API_BASE"].rstrip("/")
        self.csrf = os.environ["CODEER_CSRF_TOKEN"]
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.cookie_header = (
            f"sessionid={os.environ['CODEER_SESSION_ID']}; "
            f"csrftoken={os.environ['CODEER_CSRF_TOKEN']}"
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
    ) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base}/api/v1{path if path.startswith('/') else '/' + path}{query}"
        data = None
        headers = {
            "Accept": "application/json",
            "Cookie": self.cookie_header,
            "Referer": self.base,
        }
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["X-CSRFToken"] = self.csrf
        req = Request(url, data=data, headers=headers, method=method.upper())
        try:
            with self.opener.open(req, timeout=60) as resp:
                text = resp.read().decode("utf-8")
        except HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise SystemExit(f"HTTP {e.code} for {method} {path}: {detail}") from e
        payload = json.loads(text) if text else None
        if isinstance(payload, dict) and "error_code" in payload and "data" in payload:
            if payload.get("error_code") not in (0, None):
                raise SystemExit(f"Codeer error: {payload.get('message') or payload}")
            return payload["data"]
        return payload

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, body: Any) -> Any:
        return self.request("POST", path, body=body)


def _ids(csv_text: str | None) -> list[str] | None:
    if not csv_text:
        return None
    return [x.strip() for x in csv_text.split(",") if x.strip()]


def _version_by_number(versions: list[dict[str, Any]], number: int) -> dict[str, Any]:
    for version in versions:
        if version.get("version_number") == number:
            return version
    raise SystemExit(f"no AgentHistory with version_number={number}")


def _pick_history(versions: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    if args.history:
        for version in versions:
            if version.get("id") == args.history:
                return version
        return {"id": args.history, "version_number": None, "status": None}
    if args.version is not None:
        return _version_by_number(versions, args.version)
    if args.latest:
        return sorted(versions, key=lambda v: v.get("version_number") or 0, reverse=True)[0]
    for version in versions:
        if version.get("status") == "published" or version.get("was_published"):
            return version
    return sorted(versions, key=lambda v: v.get("version_number") or 0, reverse=True)[0]


def _truncate(text: str, n: int = 80) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text[: n - 1] + "…" if len(text) > n else text


def main() -> int:
    _load_project_settings()
    _load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default=os.environ.get("CODEER_AGENT_ID"))
    ap.add_argument("--workspace", default=os.environ.get("CODEER_WORKSPACE_ID"))
    ap.add_argument("--history", help="AgentHistory UUID; default is published history")
    ap.add_argument("--version", type=int, help="AgentHistory version_number")
    ap.add_argument("--latest", action="store_true", help="Use latest history, including drafts")
    ap.add_argument("--cases", help="Comma-separated case UUIDs; default all agent cases")
    ap.add_argument("--evaluators", help="Comma-separated evaluator UUIDs; default all workspace evaluators")
    ap.add_argument("--out-dir", default=".codeer/eval_table")
    args = ap.parse_args()

    if not args.agent:
        raise SystemExit("--agent is required or set CODEER_AGENT_ID")
    if not args.workspace:
        raise SystemExit("--workspace is required or set CODEER_WORKSPACE_ID")

    c = Client()
    cases = c.get(f"/eval/agents/{args.agent}/cases")
    wanted_cases = set(_ids(args.cases) or [])
    if wanted_cases:
        cases = [case for case in cases if case["id"] in wanted_cases]
    case_ids = [case["id"] for case in cases]
    if not case_ids:
        raise SystemExit("no eval cases matched")

    if args.evaluators:
        evaluators = [c.get(f"/eval/evaluators/{eid}") for eid in _ids(args.evaluators) or []]
    else:
        evaluators = c.get("/eval/evaluators", params={"wid": args.workspace})
    if not evaluators:
        raise SystemExit("no evaluators matched")

    versions = c.get(f"/agents/{args.agent}/histories")
    history = _pick_history(versions, args)

    rows: list[dict[str, Any]] = []
    all_rubrics: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []
    for evaluator in evaluators:
        evaluator_id = evaluator["id"]
        rubrics = c.post(
            "/eval/rubrics/batch",
            body={"case_ids": case_ids, "evaluator_id": evaluator_id},
        )
        results = c.post(
            "/eval/results/batch",
            body={
                "case_ids": case_ids,
                "evaluator_id": evaluator_id,
                "agent_history_id": history["id"],
                "workspace_id": args.workspace,
                "include_output": True,
            },
        )
        all_rubrics.extend(rubrics)
        all_results.extend({**result, "evaluator_id": evaluator_id} for result in results)
        rubric_by_case = {
            (row.get("case_id") or row.get("evaluation_case_id")): row.get("rubric", "")
            for row in rubrics
        }
        result_by_case = {
            (row.get("case_id") or row.get("evaluation_case_id")): row
            for row in results
        }
        for order, case in enumerate(cases, 1):
            case_id = case["id"]
            result = result_by_case.get(case_id, {})
            rows.append(
                {
                    "order": order,
                    "case_id": case_id,
                    "input": case.get("input") or "",
                    "evaluator_id": evaluator_id,
                    "evaluator_name": evaluator.get("name") or evaluator_id,
                    "score": result.get("score"),
                    "reason": result.get("reason") or "",
                    "output": result.get("output") or result.get("actual_output") or "",
                    "rubric": rubric_by_case.get(case_id, ""),
                }
            )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    full = {
        "agent_id": args.agent,
        "workspace_id": args.workspace,
        "history": {
            "id": history["id"],
            "version_number": history.get("version_number"),
            "status": history.get("status"),
            "was_published": history.get("was_published"),
            "version_note": history.get("version_note"),
            "created_at": history.get("created_at"),
        },
        "evaluators": [
            {"id": evaluator["id"], "name": evaluator.get("name"), "description": evaluator.get("description")}
            for evaluator in evaluators
        ],
        "cases": cases,
        "rubrics": all_rubrics,
        "results": all_results,
        "table": rows,
    }
    (out_dir / "eval_table_full.json").write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n")
    with (out_dir / "eval_table.csv").open("w", newline="") as fh:
        fields = ["order", "case_id", "input", "evaluator_name", "score", "reason", "output", "rubric", "evaluator_id"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with (out_dir / "eval_table_summary.md").open("w") as fh:
        fh.write("# Codeer Eval Table Export\n\n")
        fh.write(f"Agent: `{args.agent}`\n\n")
        fh.write(f"History: v{history.get('version_number')} `{history['id']}`\n\n")
        fh.write("| # | Evaluator | Score | Case ID | Input |\n")
        fh.write("|---:|---|---:|---|---|\n")
        for row in rows:
            inp = _truncate(row["input"]).replace("|", "\\|")
            fh.write(
                f"| {row['order']} | {row['evaluator_name']} | {row['score']} | "
                f"`{row['case_id']}` | {inp} |\n"
            )

    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "cases": len(cases),
                "evaluators": len(evaluators),
                "rows": len(rows),
                "history_id": history["id"],
                "version_number": history.get("version_number"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
