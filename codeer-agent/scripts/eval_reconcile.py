"""Reconcile a local eval case manifest with Codeer's server-side eval suite.

This is a read-only audit tool. It compares a local ``.codeer/eval_cases.json``
manifest against the server cases, evaluators, and per-evaluator rubrics for an
agent. It does not create, update, or delete anything.

Usage:
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/eval_reconcile.py \
        --manifest .codeer/eval_cases.json \
        --agent <agent_id> \
        --workspace <ws_id> \
        --out .codeer/eval_reconcile.json

Finds:
- duplicate local manifest inputs
- duplicate server-side case inputs
- local cases missing on server
- server cases missing from the local manifest
- invalid evaluator IDs in the manifest
- missing server rubrics
- rubric drift between local manifest and server state
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _truncate(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


def _normalize_manifest(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return flat local case specs with rubrics expanded from shared fields."""
    cases = payload.get("cases") or []
    shared_style_rubric = payload.get("shared_style_rubric")
    shared_style_evaluators = payload.get("shared_style_evaluators") or []

    out: list[dict[str, Any]] = []
    for idx, case in enumerate(cases):
        rubrics = dict(case.get("rubrics") or case.get("rubrics_by_evaluator") or {})
        if shared_style_rubric:
            for ev_id in shared_style_evaluators:
                rubrics.setdefault(ev_id, shared_style_rubric)
        out.append({
            "index": idx,
            "label": case.get("label") or f"case[{idx}]",
            "input": case.get("input") or "",
            "expected_output": case.get("expected_output"),
            "rubrics_by_evaluator": rubrics,
        })
    return out


def _by_input(rows: list[dict[str, Any]], *, input_key: str = "input") -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row.get(input_key) or ""].append(row)
    return dict(grouped)


def _duplicate_inputs(grouped: dict[str, list[dict[str, Any]]], *, kind: str) -> list[dict[str, Any]]:
    out = []
    for input_text, rows in grouped.items():
        if len(rows) <= 1:
            continue
        out.append({
            "input_preview": _truncate(input_text),
            "count": len(rows),
            "items": [
                {
                    "case_id": row.get("id") or row.get("case_id"),
                    "label": row.get("label"),
                    "index": row.get("index"),
                }
                for row in rows
            ],
            "kind": kind,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=".codeer/eval_cases.json",
                    help="Local eval cases manifest. Defaults to .codeer/eval_cases.json")
    ap.add_argument("--agent", default=None, help="Agent UUID. Defaults to CODEER_AGENT_ID")
    ap.add_argument("--workspace", default=None, help="Workspace UUID. Defaults to CODEER_WORKSPACE_ID")
    ap.add_argument("--evaluators", default=None,
                    help="Comma-separated evaluator UUIDs to compare. Defaults to all evaluators in workspace")
    ap.add_argument("--out", default=None, help="Write report JSON to this path")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        _log(f"error: manifest not found: {manifest_path}")
        return 2

    payload = json.loads(manifest_path.read_text())
    local_cases = _normalize_manifest(payload)
    local_by_input = _by_input(local_cases)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from codeer_cli import CodeerClient  # noqa: PLC0415
    from codeer_cli import eval_ as eval_mod  # noqa: PLC0415

    with CodeerClient.from_env() as client:
        agent_id = args.agent or client.agent_id
        workspace_id = args.workspace or client.workspace_id
        if not agent_id:
            _log("error: --agent or CODEER_AGENT_ID is required")
            return 2
        if not workspace_id:
            _log("error: --workspace or CODEER_WORKSPACE_ID is required")
            return 2

        server_cases = eval_mod.list_cases(client, agent_id)
        server_by_input = _by_input(server_cases)

        all_evaluators = eval_mod.list_evaluators(client, workspace_id)
        evaluator_by_id = {e["id"]: e for e in all_evaluators}
        if args.evaluators:
            evaluator_ids = [s.strip() for s in args.evaluators.split(",") if s.strip()]
        else:
            evaluator_ids = [e["id"] for e in all_evaluators]

        manifest_evaluator_ids = {
            ev_id
            for case in local_cases
            for ev_id in (case.get("rubrics_by_evaluator") or {}).keys()
        }
        invalid_manifest_evaluator_ids = sorted(manifest_evaluator_ids - set(evaluator_by_id))
        invalid_requested_evaluator_ids = sorted(set(evaluator_ids) - set(evaluator_by_id))
        valid_evaluator_ids = [ev_id for ev_id in evaluator_ids if ev_id in evaluator_by_id]

        server_case_ids = [c["id"] for c in server_cases]
        rubrics_by_case = eval_mod.get_case_rubrics(
            client,
            agent_id=agent_id,
            workspace_id=workspace_id,
            evaluator_ids=valid_evaluator_ids,
            case_ids=server_case_ids,
        ) if server_case_ids and valid_evaluator_ids else {}

    local_missing_on_server = []
    server_missing_in_manifest = []
    rubric_drift = []
    missing_server_rubrics = []

    for local in local_cases:
        matches = server_by_input.get(local["input"], [])
        if not matches:
            local_missing_on_server.append({
                "label": local["label"],
                "index": local["index"],
                "input_preview": _truncate(local["input"]),
            })
            continue

        # If server has duplicates for this input, compare against the first one
        # only and report the duplication separately.
        server = matches[0]
        server_rubrics = rubrics_by_case.get(server["id"]) or {}
        for ev_id, local_rubric in (local.get("rubrics_by_evaluator") or {}).items():
            if ev_id not in evaluator_by_id:
                continue
            if valid_evaluator_ids and ev_id not in valid_evaluator_ids:
                continue
            server_rubric = server_rubrics.get(ev_id, "")
            if not server_rubric:
                missing_server_rubrics.append({
                    "case_id": server["id"],
                    "label": local["label"],
                    "evaluator_id": ev_id,
                    "evaluator_name": evaluator_by_id[ev_id].get("name"),
                    "input_preview": _truncate(local["input"]),
                })
            elif server_rubric != local_rubric:
                rubric_drift.append({
                    "case_id": server["id"],
                    "label": local["label"],
                    "evaluator_id": ev_id,
                    "evaluator_name": evaluator_by_id[ev_id].get("name"),
                    "input_preview": _truncate(local["input"]),
                    "local_rubric_preview": _truncate(local_rubric),
                    "server_rubric_preview": _truncate(server_rubric),
                })

    for server in server_cases:
        if server.get("input") not in local_by_input:
            server_missing_in_manifest.append({
                "case_id": server["id"],
                "input_preview": _truncate(server.get("input") or ""),
            })

    duplicate_local_inputs = _duplicate_inputs(local_by_input, kind="local")
    duplicate_server_inputs = _duplicate_inputs(server_by_input, kind="server")

    issue_counts = {
        "duplicate_local_inputs": len(duplicate_local_inputs),
        "duplicate_server_inputs": len(duplicate_server_inputs),
        "local_missing_on_server": len(local_missing_on_server),
        "server_missing_in_manifest": len(server_missing_in_manifest),
        "invalid_manifest_evaluator_ids": len(invalid_manifest_evaluator_ids),
        "invalid_requested_evaluator_ids": len(invalid_requested_evaluator_ids),
        "missing_server_rubrics": len(missing_server_rubrics),
        "rubric_drift": len(rubric_drift),
    }
    total_issues = sum(issue_counts.values())

    report = {
        "agent_id": agent_id,
        "workspace_id": workspace_id,
        "manifest": str(manifest_path),
        "local_case_count": len(local_cases),
        "server_case_count": len(server_cases),
        "compared_evaluators": [
            {"id": ev_id, "name": evaluator_by_id[ev_id].get("name")}
            for ev_id in valid_evaluator_ids
        ],
        "issue_counts": issue_counts,
        "issues": {
            "duplicate_local_inputs": duplicate_local_inputs,
            "duplicate_server_inputs": duplicate_server_inputs,
            "local_missing_on_server": local_missing_on_server,
            "server_missing_in_manifest": server_missing_in_manifest,
            "invalid_manifest_evaluator_ids": invalid_manifest_evaluator_ids,
            "invalid_requested_evaluator_ids": invalid_requested_evaluator_ids,
            "missing_server_rubrics": missing_server_rubrics,
            "rubric_drift": rubric_drift,
        },
    }

    _log(
        "reconcile: "
        f"{len(local_cases)} local cases, {len(server_cases)} server cases, "
        f"{len(valid_evaluator_ids)} evaluators, {total_issues} issues"
    )
    for key, count in issue_counts.items():
        if count:
            _log(f"  {key}: {count}")

    out_text = json.dumps(report, indent=2, ensure_ascii=False)
    print(out_text)
    if args.out:
        Path(args.out).write_text(out_text + "\n")

    return 1 if total_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
