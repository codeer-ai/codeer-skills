from __future__ import annotations

import csv
import json
import mimetypes
import os
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .. import agents as agents_mod
from .. import eval_ as eval_mod
from ..client import CodeerClient
from ..parse import parse_eval_result, parse_eval_tool_calls, summarize_eval_tool_calls
from ._util import log, truncate

POLL_INTERVAL = 5
POLL_TIMEOUT = 900


def _ids(csv_text: str | None) -> list[str] | None:
    if not csv_text:
        return None
    return [x.strip() for x in csv_text.split(",") if x.strip()]


def register(subparsers):
    ev = subparsers.add_parser("eval", help="Eval suite operations")
    sub = ev.add_subparsers(dest="action", required=True)

    # codeer eval list
    p = sub.add_parser("list", help="List eval cases for an agent")
    p.add_argument("--agent", required=True)
    p.set_defaults(func=run_list)

    # codeer eval evaluators
    p = sub.add_parser("evaluators", help="List evaluators in workspace")
    p.set_defaults(func=run_evaluators)

    # codeer eval evaluator-create
    p = sub.add_parser("evaluator-create", help="Create an evaluator in the workspace")
    p.add_argument("--name", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--system-prompt-template", help="Evaluator system prompt template text")
    g.add_argument("--system-prompt-template-file", help="Path to evaluator system prompt template")
    p.add_argument("--description", default=None)
    p.set_defaults(func=run_evaluator_create)

    # codeer eval run
    p = sub.add_parser("run", help="Trigger eval run, poll for results, print scores")
    p.add_argument("--agent", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--history", default=None, help="History UUID to pin the run to")
    g.add_argument("--latest", action="store_true",
                   help="Auto-select the newest AgentHistory (default)")
    p.add_argument("--cases", default=None, help="Comma-separated case UUIDs (default: all)")
    p.add_argument("--evaluators", required=True, help="Comma-separated evaluator UUIDs")
    p.add_argument("--poll-timeout", type=int, default=POLL_TIMEOUT)
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_run)

    # codeer eval export
    p = sub.add_parser("export", help="Export eval table (CSV + JSON + summary MD)")
    p.add_argument("--agent", default=None)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--version", type=int, help="AgentHistory version_number")
    g.add_argument("--published", action="store_true", help="Use the published history")
    p.add_argument("--cases", default=None, help="Comma-separated case UUIDs")
    p.add_argument("--evaluators", default=None, help="Comma-separated evaluator UUIDs")
    p.add_argument("--out-dir", default=".codeer/eval_table")
    p.set_defaults(func=run_export)

    # codeer eval reconcile
    p = sub.add_parser("reconcile", help="Audit local manifest vs server eval suite (read-only)")
    p.add_argument("--manifest", default=".codeer/eval_cases.json")
    p.add_argument("--agent", default=None)
    p.add_argument("--evaluators", default=None, help="Comma-separated evaluator UUIDs")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_reconcile)

    # codeer eval cases-apply
    p = sub.add_parser("cases-apply", help="Create/update eval cases from JSON manifest")
    p.add_argument("--cases", required=True, help="Path to eval_cases.json")
    p.add_argument("--agent", required=True)
    p.add_argument("--attachments-dir", default=None, dest="attachments_dir")
    p.add_argument("--allow-duplicates", action="store_true")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_cases_apply)

    # codeer eval rubrics
    p = sub.add_parser("rubrics", help="Read per-(case, evaluator) rubrics")
    p.add_argument("--agent", required=True)
    p.add_argument("--evaluators", default=None, help="Comma-separated evaluator UUIDs")
    p.add_argument("--cases", default=None, help="Comma-separated case UUIDs")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_rubrics)

    # codeer eval rubrics-apply
    p = sub.add_parser("rubrics-apply", help="Apply rubric changes from JSON file")
    p.add_argument("--rubrics", required=True, help="Path to rubrics JSON")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="Write all rubrics even if unchanged")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_rubrics_apply)


# ---------------------------------------------------------------------------
# eval list
# ---------------------------------------------------------------------------

def run_list(args, client) -> int:
    cases = eval_mod.list_cases(client, args.agent)
    print(json.dumps(cases, ensure_ascii=False, indent=2, default=str))
    return 0


# ---------------------------------------------------------------------------
# eval evaluators
# ---------------------------------------------------------------------------

def run_evaluators(args, client) -> int:
    ws, _ = client.resolve_scope()
    evaluators = eval_mod.list_evaluators(client, ws)
    print(json.dumps(evaluators, ensure_ascii=False, indent=2, default=str))
    return 0


# ---------------------------------------------------------------------------
# eval evaluator-create
# ---------------------------------------------------------------------------

def run_evaluator_create(args, client) -> int:
    workspace_id, _ = client.resolve_scope()
    if args.system_prompt_template_file:
        system_prompt_template = Path(args.system_prompt_template_file).read_text()
    else:
        system_prompt_template = args.system_prompt_template
    evaluator = eval_mod.create_evaluator(
        client,
        workspace_id=workspace_id,
        name=args.name,
        system_prompt_template=system_prompt_template,
        description=args.description,
    )
    print(json.dumps(evaluator, ensure_ascii=False, indent=2, default=str))
    return 0


# ---------------------------------------------------------------------------
# eval run
# ---------------------------------------------------------------------------

def run_run(args, client) -> int:
    workspace_id, _ = client.resolve_scope()
    if args.latest or not args.history:
        history_id = agents_mod.get_latest_history_id(client, args.agent)
        if not history_id:
            log("error: agent has no history versions; pass --history instead")
            return 2
        log(f"--latest -> {history_id}")
        args.history = history_id

    if args.cases:
        case_ids = _ids(args.cases) or []
        case_objs: list[dict] = []
        for cid in case_ids:
            try:
                case_objs.append(eval_mod.get_case(client, cid))
            except Exception as e:
                log(f"warning: could not fetch case {cid}: {e}")
                case_objs.append({"id": cid, "input": ""})
    else:
        case_objs = eval_mod.list_cases(client, args.agent)
        case_ids = [c["id"] for c in case_objs]
    if not case_ids:
        log("error: no cases to run")
        return 2

    evaluator_ids = _ids(args.evaluators) or []
    if not evaluator_ids:
        log("error: --evaluators is required")
        return 2
    evaluators = [eval_mod.get_evaluator(client, eid) for eid in evaluator_ids]

    case_label_by_id = {c["id"]: truncate(c.get("input") or "", 60) for c in case_objs}
    evaluator_name_by_id = {e["id"]: e.get("name", e["id"]) for e in evaluators}

    log(f"triggering: {len(case_ids)} cases x {len(evaluator_ids)} evaluators on history {args.history}")
    eval_mod.trigger(client, case_ids=case_ids, evaluator_ids=evaluator_ids,
                     agent_history_id=args.history)

    deadline = time.time() + args.poll_timeout
    results_by_eval: dict[str, list[dict]] = {}
    while time.time() < deadline:
        results_by_eval = {}
        done = 0
        total = len(case_ids) * len(evaluator_ids)
        for ev_id in evaluator_ids:
            rows = eval_mod.get_results(
                client, case_ids=case_ids, evaluator_id=ev_id,
                agent_history_id=args.history, workspace_id=workspace_id,
                include_output=True, include_reasoning_steps=True,
            )
            results_by_eval[ev_id] = rows
            done += sum(1 for r in rows if r.get("score") is not None)
        log(f"  progress: {done}/{total}")
        if done >= total:
            break
        time.sleep(POLL_INTERVAL)

    flat: list[dict] = []
    for ev_id, rows in results_by_eval.items():
        for r in rows:
            result_summary = parse_eval_result(r)
            tool_calls = parse_eval_tool_calls(r)
            total_tool_duration_ms = sum(
                tc.duration_ms for tc in tool_calls if tc.duration_ms is not None
            )
            flat.append({
                "case_id": r.get("case_id") or r.get("evaluation_case_id"),
                "case_label": case_label_by_id.get(
                    r.get("case_id") or r.get("evaluation_case_id"), "?"),
                "evaluator_id": ev_id,
                "evaluator_name": evaluator_name_by_id.get(ev_id, ev_id),
                "score": r.get("score"),
                "status": result_summary.status,
                "reason": r.get("reason"),
                "output": r.get("output") or r.get("actual_output"),
                "execution_time_s": result_summary.execution_time_s,
                "cost_credits": result_summary.cost_credits,
                "tool_call_count": len(tool_calls),
                "tool_total_duration_ms": total_tool_duration_ms or None,
                "tool_calls_summary": summarize_eval_tool_calls(tool_calls),
                "tool_calls": [asdict(tc) for tc in tool_calls],
                "raw_result": r,
            })

    all_perfect = all((r.get("score") or 0.0) >= 1.0 for r in flat) if flat else False
    log("\n" + "=" * 80)
    log(f"RESULTS  agent={args.agent}  history={args.history}")
    log("=" * 80)
    log(f"{'score':>6}  {'evaluator':<35}  case")
    for r in sorted(flat, key=lambda x: (x.get("score") or 0.0, x["evaluator_name"])):
        score = r.get("score")
        score_str = f"{score:.2f}" if score is not None else "  - "
        log(f"{score_str:>6}  {r['evaluator_name'][:35]:<35}  {r['case_label']}")

    non_perfect = [r for r in flat if (r.get("score") or 0.0) < 1.0]
    if non_perfect:
        log("\nNON-PERFECT RESULTS:\n")
        for r in non_perfect:
            log(f"  [{r.get('score') or 0:.2f}] {r['evaluator_name']} — {r['case_label']}")
            if r.get("tool_calls_summary"):
                log(f"     tools: {r['tool_calls_summary'][:600]}")
            log(f"     reason: {(r.get('reason') or '').strip()[:600]}")
            log("")

    out = {
        "agent_id": args.agent,
        "history_id": args.history,
        "all_perfect": all_perfect,
        "results": flat,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0 if all_perfect else 1


# ---------------------------------------------------------------------------
# eval export
# ---------------------------------------------------------------------------

def _pick_history(versions: list[dict], args) -> dict:
    if args.version is not None:
        for v in versions:
            if v.get("version_number") == args.version:
                return v
        raise SystemExit(f"no AgentHistory with version_number={args.version}")
    if args.published:
        current = [v for v in versions if v.get("status") == "published"]
        if current:
            return sorted(current, key=lambda v: v.get("version_number") or 0, reverse=True)[0]
        previous = [v for v in versions if v.get("was_published")]
        if previous:
            return sorted(previous, key=lambda v: v.get("version_number") or 0, reverse=True)[0]
        raise SystemExit("no published AgentHistory found")
    return sorted(versions, key=lambda v: v.get("version_number") or 0, reverse=True)[0]


def run_export(args, client) -> int:
    agent_id = args.agent or client.agent_id or os.environ.get("CODEER_AGENT_ID")
    workspace_id, _ = client.resolve_scope()
    if not agent_id:
        log("error: --agent is required or set CODEER_AGENT_ID")
        return 2

    cases = eval_mod.list_cases(client, agent_id)
    wanted_cases = set(_ids(args.cases) or [])
    if wanted_cases:
        cases = [c for c in cases if c["id"] in wanted_cases]
    case_ids = [c["id"] for c in cases]
    if not case_ids:
        log("error: no eval cases matched")
        return 2

    if args.evaluators:
        evaluators = [eval_mod.get_evaluator(client, eid) for eid in (_ids(args.evaluators) or [])]
    else:
        evaluators = eval_mod.list_evaluators(client, workspace_id)
    if not evaluators:
        log("error: no evaluators matched")
        return 2

    versions = agents_mod.list_versions(client, agent_id)
    history = _pick_history(versions, args)

    rows: list[dict[str, Any]] = []
    all_rubrics: list[dict] = []
    all_results: list[dict] = []
    for evaluator in evaluators:
        evaluator_id = evaluator["id"]
        rubrics = eval_mod.get_rubrics_batch(
            client, case_ids=case_ids, evaluator_id=evaluator_id)
        results = eval_mod.get_results(
            client, case_ids=case_ids, evaluator_id=evaluator_id,
            agent_history_id=history["id"], workspace_id=workspace_id,
            include_output=True, include_reasoning_steps=True,
        )
        all_rubrics.extend(rubrics)
        all_results.extend({**r, "evaluator_id": evaluator_id} for r in results)
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
            tool_calls = parse_eval_tool_calls(result)
            total_tool_duration_ms = sum(
                tc.duration_ms for tc in tool_calls if tc.duration_ms is not None
            )
            rows.append({
                "order": order,
                "case_id": case_id,
                "input": case.get("input") or "",
                "note": case.get("note") or "",
                "evaluator_id": evaluator_id,
                "evaluator_name": evaluator.get("name") or evaluator_id,
                "score": result.get("score"),
                "reason": result.get("reason") or "",
                "output": result.get("output") or result.get("actual_output") or "",
                "rubric": rubric_by_case.get(case_id, ""),
                "tool_call_count": len(tool_calls),
                "tool_total_duration_ms": total_tool_duration_ms or "",
                "tool_calls_summary": summarize_eval_tool_calls(tool_calls),
                "tool_calls_json": json.dumps(
                    [asdict(tc) for tc in tool_calls], ensure_ascii=False),
            })

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    full = {
        "agent_id": agent_id,
        "workspace_id": workspace_id,
        "history": {
            "id": history["id"],
            "version_number": history.get("version_number"),
            "status": history.get("status"),
            "was_published": history.get("was_published"),
            "version_note": history.get("version_note"),
            "created_at": history.get("created_at"),
        },
        "evaluators": [
            {"id": e["id"], "name": e.get("name"), "description": e.get("description")}
            for e in evaluators
        ],
        "cases": cases,
        "rubrics": all_rubrics,
        "results": all_results,
        "table": rows,
    }
    (out_dir / "eval_table_full.json").write_text(
        json.dumps(full, ensure_ascii=False, indent=2) + "\n")
    with (out_dir / "eval_table.csv").open("w", newline="") as fh:
        fields = [
            "order", "case_id", "input", "note", "evaluator_name", "score",
            "reason", "output", "rubric", "tool_call_count",
            "tool_calls_summary", "tool_total_duration_ms", "tool_calls_json",
            "evaluator_id",
        ]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with (out_dir / "eval_table_summary.md").open("w") as fh:
        fh.write("# Codeer Eval Table Export\n\n")
        fh.write(f"Agent: `{agent_id}`\n\n")
        fh.write(f"History: v{history.get('version_number')} `{history['id']}`\n\n")
        fh.write("| # | Evaluator | Score | Case ID | Input |\n")
        fh.write("|---:|---|---:|---|---|\n")
        for row in rows:
            inp = truncate(row["input"], 80).replace("|", "\\|")
            fh.write(
                f"| {row['order']} | {row['evaluator_name']} | {row['score']} | "
                f"`{row['case_id']}` | {inp} |\n")

    print(json.dumps({
        "out_dir": str(out_dir),
        "cases": len(cases),
        "evaluators": len(evaluators),
        "rows": len(rows),
        "history_id": history["id"],
        "version_number": history.get("version_number"),
    }, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# eval reconcile
# ---------------------------------------------------------------------------

def _normalize_manifest(payload: dict[str, Any]) -> list[dict[str, Any]]:
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


def _by_input(rows: list[dict], *, input_key: str = "input") -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row.get(input_key) or ""].append(row)
    return dict(grouped)


def _duplicate_inputs(grouped: dict[str, list[dict]], *, kind: str) -> list[dict]:
    out = []
    for input_text, rows in grouped.items():
        if len(rows) <= 1:
            continue
        out.append({
            "input_preview": truncate(input_text, 120),
            "count": len(rows),
            "items": [
                {"case_id": r.get("id") or r.get("case_id"),
                 "label": r.get("label"), "index": r.get("index")}
                for r in rows
            ],
            "kind": kind,
        })
    return out


def run_reconcile(args, client) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        log(f"error: manifest not found: {manifest_path}")
        return 2

    payload = json.loads(manifest_path.read_text())
    local_cases = _normalize_manifest(payload)
    local_by_input = _by_input(local_cases)

    agent_id = args.agent or client.agent_id or os.environ.get("CODEER_AGENT_ID")
    workspace_id, _ = client.resolve_scope()
    if not agent_id:
        log("error: --agent or CODEER_AGENT_ID is required")
        return 2

    server_cases = eval_mod.list_cases(client, agent_id)
    server_by_input = _by_input(server_cases)

    all_evaluators = eval_mod.list_evaluators(client, workspace_id)
    evaluator_by_id = {e["id"]: e for e in all_evaluators}
    if args.evaluators:
        evaluator_ids = _ids(args.evaluators) or []
    else:
        evaluator_ids = [e["id"] for e in all_evaluators]

    manifest_evaluator_ids = {
        ev_id for case in local_cases
        for ev_id in (case.get("rubrics_by_evaluator") or {}).keys()
    }
    invalid_manifest_evaluator_ids = sorted(manifest_evaluator_ids - set(evaluator_by_id))
    invalid_requested_evaluator_ids = sorted(set(evaluator_ids) - set(evaluator_by_id))
    valid_evaluator_ids = [eid for eid in evaluator_ids if eid in evaluator_by_id]

    server_case_ids = [c["id"] for c in server_cases]
    rubrics_by_case = eval_mod.get_case_rubrics(
        client, agent_id=agent_id, workspace_id=workspace_id,
        evaluator_ids=valid_evaluator_ids, case_ids=server_case_ids,
    ) if server_case_ids and valid_evaluator_ids else {}

    local_missing_on_server = []
    server_missing_in_manifest = []
    rubric_drift = []
    missing_server_rubrics = []

    for local in local_cases:
        matches = server_by_input.get(local["input"], [])
        if not matches:
            local_missing_on_server.append({
                "label": local["label"], "index": local["index"],
                "input_preview": truncate(local["input"], 120),
            })
            continue
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
                    "case_id": server["id"], "label": local["label"],
                    "evaluator_id": ev_id,
                    "evaluator_name": evaluator_by_id[ev_id].get("name"),
                    "input_preview": truncate(local["input"], 120),
                })
            elif server_rubric != local_rubric:
                rubric_drift.append({
                    "case_id": server["id"], "label": local["label"],
                    "evaluator_id": ev_id,
                    "evaluator_name": evaluator_by_id[ev_id].get("name"),
                    "input_preview": truncate(local["input"], 120),
                    "local_rubric_preview": truncate(local_rubric, 120),
                    "server_rubric_preview": truncate(server_rubric, 120),
                })

    for server in server_cases:
        if server.get("input") not in local_by_input:
            server_missing_in_manifest.append({
                "case_id": server["id"],
                "input_preview": truncate(server.get("input") or "", 120),
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
        "agent_id": agent_id, "workspace_id": workspace_id,
        "manifest": str(manifest_path),
        "local_case_count": len(local_cases),
        "server_case_count": len(server_cases),
        "compared_evaluators": [
            {"id": eid, "name": evaluator_by_id[eid].get("name")}
            for eid in valid_evaluator_ids
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

    log(f"reconcile: {len(local_cases)} local cases, {len(server_cases)} server cases, "
        f"{len(valid_evaluator_ids)} evaluators, {total_issues} issues")
    for key, count in issue_counts.items():
        if count:
            log(f"  {key}: {count}")

    out_text = json.dumps(report, indent=2, ensure_ascii=False)
    print(out_text)
    if args.out:
        Path(args.out).write_text(out_text + "\n")
    return 1 if total_issues else 0


# ---------------------------------------------------------------------------
# eval cases-apply
# ---------------------------------------------------------------------------

def _upload_attachment(client: CodeerClient, *, file_path: Path, workspace_id: str) -> str:
    ct, _ = mimetypes.guess_type(file_path.name)
    ct = ct or "application/octet-stream"
    files = {"file": (file_path.name, file_path.read_bytes(), ct)}
    data = {"scope": "persistent", "purpose": "evaluation_context"}
    uploaded = client.post("/external/files", files=files, data=data)
    uuid = uploaded.get("uuid") if isinstance(uploaded, dict) else None
    if not uuid:
        raise RuntimeError(f"upload-file response missing uuid for {file_path.name}: {uploaded}")
    return uuid


def run_cases_apply(args, client) -> int:
    payload = json.loads(Path(args.cases).read_text())
    cases = payload.get("cases") or []
    if not cases:
        log("error: no cases in payload")
        return 2

    shared_style_rubric = payload.get("shared_style_rubric")
    shared_style_evals = payload.get("shared_style_evaluators") or []

    needs_attach = any(case.get("attachment_files") for case in cases)
    attach_dir: Path | None = Path(args.attachments_dir) if args.attachments_dir else None
    if needs_attach and attach_dir is None:
        log("error: at least one case has attachment_files, but --attachments-dir was not provided")
        return 2
    if needs_attach and attach_dir and not attach_dir.is_dir():
        log(f"error: --attachments-dir does not exist or is not a directory: {attach_dir}")
        return 2

    workspace_id, _ = client.resolve_scope()

    existing_by_input: dict[str, dict] = {}
    if not args.allow_duplicates:
        for existing in eval_mod.list_cases(client, args.agent):
            existing_input = existing.get("input")
            if isinstance(existing_input, str) and existing_input not in existing_by_input:
                existing_by_input[existing_input] = existing

    case_ids: list[str] = []
    labels: list[str] = []
    created: list[dict] = []
    reused: list[dict] = []
    for case in cases:
        rubrics = dict(case.get("rubrics") or {})
        if shared_style_rubric:
            for ev_id in shared_style_evals:
                rubrics.setdefault(ev_id, shared_style_rubric)
        if not rubrics:
            log(f"error: case '{case.get('label')}' has no rubrics")
            return 2

        label = case.get("label", "(unlabeled)")
        attachment_ids: list[str] = []
        for fname in case.get("attachment_files") or []:
            fp = (attach_dir / fname).resolve() if attach_dir else None
            if not fp or not fp.is_file():
                log(f"error: attachment file not found for case '{label}': {fname}")
                return 2
            log(f"  uploading attachment: {fname}")
            uid = _upload_attachment(client, file_path=fp, workspace_id=workspace_id)
            attachment_ids.append(uid)

        existing = existing_by_input.get(case["input"])
        if existing is not None:
            case_id = existing["id"]
            log(f"reusing existing case: {label} ({case_id[:8]})")
            if case.get("expected_output") is not None or attachment_ids or case.get("meta") is not None or case.get("note") is not None:
                eval_mod.update_case(
                    client, case_id,
                    expected_output=case.get("expected_output"),
                    attachment_ids=attachment_ids or None,
                    meta=case.get("meta"),
                    note=case.get("note"),
                )
            for ev_id, rubric in rubrics.items():
                eval_mod.set_rubric(client, evaluation_case_id=case_id,
                                    evaluator_id=ev_id, rubric=rubric)
            case_ids.append(case_id)
            labels.append(label)
            reused.append({"case_id": case_id, "label": label})
            continue

        log(f"creating: {label}")
        result = eval_mod.create_case_with_rubrics(
            client, agent_id=args.agent, input=case["input"],
            expected_output=case.get("expected_output"),
            attachment_ids=attachment_ids or None,
            rubrics_by_evaluator=rubrics, meta=case.get("meta"),
            note=case.get("note"),
        )
        case_ids.append(result["id"])
        labels.append(label)
        created.append({"case_id": result["id"], "label": label})

    out = {"case_ids": case_ids, "labels": labels, "created": created, "reused": reused}
    out_text = json.dumps(out, indent=2, ensure_ascii=False)
    print(out_text)
    if args.out:
        Path(args.out).write_text(out_text + "\n")
    return 0


# ---------------------------------------------------------------------------
# eval rubrics
# ---------------------------------------------------------------------------

def run_rubrics(args, client) -> int:
    workspace_id, _ = client.resolve_scope()
    cases = eval_mod.list_cases(client, args.agent)
    if args.cases:
        wanted = set(_ids(args.cases) or [])
        cases = [x for x in cases if x["id"] in wanted]
    case_ids = [x["id"] for x in cases]
    case_input = {x["id"]: (x.get("input") or "") for x in cases}
    if not case_ids:
        log("error: no cases for this agent")
        return 2

    if args.evaluators:
        evaluator_ids = _ids(args.evaluators) or []
        evaluators = [eval_mod.get_evaluator(client, eid) for eid in evaluator_ids]
    else:
        evaluators = eval_mod.list_evaluators(client, workspace_id)
        evaluator_ids = [e["id"] for e in evaluators]
    evaluator_name = {e["id"]: e.get("name", e["id"]) for e in evaluators}
    if not evaluator_ids:
        log("error: no evaluators in workspace")
        return 2

    log(f"reading {len(case_ids)} cases x {len(evaluator_ids)} evaluators...")

    rubrics = eval_mod.get_case_rubrics(
        client, agent_id=args.agent, workspace_id=workspace_id,
        evaluator_ids=evaluator_ids, case_ids=case_ids,
    )

    for cid in case_ids:
        log("=" * 80)
        log(f"CASE {cid}")
        log(f"  input: {truncate(case_input.get(cid, ''), 120)}")
        for ev_id in evaluator_ids:
            ev_name = evaluator_name.get(ev_id, ev_id)
            rubric_text = (rubrics.get(cid) or {}).get(ev_id, "")
            if not rubric_text:
                log(f"  [{ev_name}] (rubric not set)")
            else:
                log(f"  [{ev_name}]")
                for line in rubric_text.splitlines():
                    log(f"    {line}")

    out = {
        "agent_id": args.agent,
        "workspace_id": workspace_id,
        "evaluators": [{"id": e["id"], "name": e.get("name")} for e in evaluators],
        "cases": [
            {
                "case_id": cid,
                "input": case_input.get(cid, ""),
                "rubrics_by_evaluator": {
                    ev_id: (rubrics.get(cid) or {}).get(ev_id)
                    for ev_id in evaluator_ids
                },
            }
            for cid in case_ids
        ],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


# ---------------------------------------------------------------------------
# eval rubrics-apply
# ---------------------------------------------------------------------------

def run_rubrics_apply(args, client) -> int:
    payload = json.loads(Path(args.rubrics).read_text())
    cases = payload.get("cases") or []
    if not cases:
        log("error: no cases in payload")
        return 2

    agent_id = payload.get("agent_id")
    workspace_id, _ = client.resolve_scope()

    all_case_ids = [c["case_id"] for c in cases]
    all_evaluator_ids: set[str] = set()
    for c in cases:
        all_evaluator_ids.update((c.get("rubrics_by_evaluator") or {}).keys())

    failed: list[dict] = []
    valid_case_ids = set(all_case_ids)
    valid_evaluator_ids = set(all_evaluator_ids)

    if agent_id:
        known_case_ids = {c["id"] for c in eval_mod.list_cases(client, agent_id)}
        invalid_case_ids = valid_case_ids - known_case_ids
        valid_case_ids &= known_case_ids
        if invalid_case_ids:
            log(f"warning: {len(invalid_case_ids)} case IDs are not part of agent {agent_id}")

    known_evaluator_ids = {e["id"] for e in eval_mod.list_evaluators(client, workspace_id)}
    invalid_evaluator_ids = valid_evaluator_ids - known_evaluator_ids
    valid_evaluator_ids &= known_evaluator_ids
    if invalid_evaluator_ids:
        log(f"warning: {len(invalid_evaluator_ids)} evaluator IDs not in workspace {workspace_id}")

    current: dict[str, dict[str, str]] = {}
    if not args.force:
        if not valid_case_ids or not valid_evaluator_ids:
            log("reading current rubrics skipped: no valid case/evaluator pairs")
        else:
            log(f"reading current rubrics for {len(valid_case_ids)} cases x {len(valid_evaluator_ids)} evaluators...")
            current = eval_mod.get_case_rubrics(
                client, agent_id=agent_id or "", workspace_id=workspace_id,
                evaluator_ids=list(valid_evaluator_ids), case_ids=list(valid_case_ids),
            )

    updated: list[dict] = []
    skipped: list[dict] = []

    for case in cases:
        case_id = case["case_id"]
        case_input = truncate(case.get("input") or "")
        rubrics_map = case.get("rubrics_by_evaluator") or {}

        for ev_id, new_rubric in rubrics_map.items():
            entry = {
                "case_id": case_id, "evaluator_id": ev_id,
                "case_input": case_input,
                "new_rubric_preview": truncate(new_rubric, 80),
            }
            if case_id not in valid_case_ids:
                failed.append({**entry, "error": "case_id not found for agent"})
                continue
            if ev_id not in valid_evaluator_ids:
                failed.append({**entry, "error": "evaluator_id not found for workspace"})
                continue

            old_rubric = (current.get(case_id) or {}).get(ev_id, "")
            entry["old_rubric_preview"] = truncate(old_rubric, 80)
            if not args.force and new_rubric == old_rubric:
                skipped.append({"case_id": case_id, "evaluator_id": ev_id, "reason": "unchanged"})
                continue

            if args.dry_run:
                log(f"  [dry-run] would update: {case_input} x {ev_id[:8]}...")
                updated.append(entry)
                continue

            try:
                eval_mod.set_rubric(client, evaluation_case_id=case_id,
                                    evaluator_id=ev_id, rubric=new_rubric)
                log(f"  updated: {case_input} x {ev_id[:8]}...")
                updated.append(entry)
            except Exception as e:
                log(f"  FAILED: {case_input} x {ev_id[:8]}... -- {e}")
                failed.append({**entry, "error": str(e)})

    log(f"\ndone: {len(updated)} updated, {len(skipped)} skipped (unchanged), {len(failed)} failed")

    out = {"updated": updated, "skipped": skipped, "failed": failed}
    out_text = json.dumps(out, indent=2, ensure_ascii=False)
    print(out_text)
    if args.out:
        Path(args.out).write_text(out_text + "\n")
    return 1 if failed else 0
