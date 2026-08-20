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
from ._util import log, print_json, strip_noisy_fields, truncate, write_json

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
    p = sub.add_parser(
        "list",
        help="List eval cases. Defaults to compact case summaries for Codex/Claude lifecycle work.",
    )
    p.add_argument("--agent", required=True)
    p.add_argument("--limit", type=int, default=50,
                   help="Number of cases to print by default (default: 50; use --all for every case).")
    p.add_argument("--all", action="store_true",
                   help="Print every case summary. Prefer --out for large suites.")
    p.add_argument("--full", action="store_true",
                   help="Print stripped full case payloads.")
    p.add_argument("--out", default=None,
                   help="Write stripped full case payloads to this file; stdout stays compact unless --full.")
    p.set_defaults(func=run_list)

    # codeer eval label-list/create/update/delete
    p = sub.add_parser("label-list", help="List eval case labels in the workspace")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_label_list)

    p = sub.add_parser("label-create", help="Create an eval case label; run --dry-run first")
    p.add_argument("--name", required=True)
    p.add_argument("--color", default=None, help="Hex color like #0969da (default: server default)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_label_create)

    p = sub.add_parser("label-update", help="Update an eval case label; run --dry-run first")
    p.add_argument("--label", required=True, dest="label_id", help="Eval case label ID")
    p.add_argument("--name", default=None)
    p.add_argument("--color", default=None, help="Hex color like #0969da")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_label_update)

    p = sub.add_parser("label-delete", help="Delete an eval case label; run --dry-run first")
    p.add_argument("--label", required=True, dest="label_id", help="Eval case label ID")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_label_delete)

    # codeer eval case-update
    p = sub.add_parser("case-update", help="Update one eval case by UUID; run --dry-run first")
    p.add_argument("--case", required=True, dest="case_id", help="Eval case UUID")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--input", help="New eval case input text")
    g.add_argument("--input-file", help="Path to new eval case input text")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--expected-output", help="New expected_output text")
    g.add_argument("--expected-output-file", help="Path to new expected_output text")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--rubric", help="New case-level rubric text")
    g.add_argument("--rubric-file", help="Path to new case-level rubric text")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--note", help="New case note text")
    g.add_argument("--note-file", help="Path to new case note text")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--meta-json", help="New case meta JSON object")
    g.add_argument("--meta-file", help="Path to new case meta JSON object")
    p.add_argument("--attachment-ids", default=None,
                   help="Comma-separated file UUIDs to set as the case attachments")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--label-ids", default=None,
                   help="Comma-separated eval case label IDs to set on the case")
    g.add_argument("--clear-labels", action="store_true",
                   help="Remove all labels from the case")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate inputs and print intended mutation without writing server state.")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_case_update)

    # codeer eval case-delete
    p = sub.add_parser("case-delete", help="Delete one eval case by UUID; run --dry-run first")
    p.add_argument("--case", required=True, dest="case_id", help="Eval case UUID")
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended deletion without writing server state.")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_case_delete)

    # codeer eval evaluators
    p = sub.add_parser(
        "evaluators",
        help="List evaluators. Defaults to prompt metadata, not full prompt text.",
    )
    p.add_argument("--full", action="store_true",
                   help="Print stripped full evaluator payloads, including prompt templates.")
    p.add_argument("--out", default=None,
                   help="Write stripped full evaluator payloads to this file.")
    p.set_defaults(func=run_evaluators)

    # codeer eval evaluator-create
    p = sub.add_parser("evaluator-create", help="Create an evaluator in the workspace; run --dry-run first")
    p.add_argument("--name", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--system-prompt-template", help="Evaluator system prompt template text")
    g.add_argument("--system-prompt-template-file", help="Path to evaluator system prompt template")
    p.add_argument("--description", default=None)
    p.add_argument(
        "--judge-model",
        default=None,
        metavar="MODEL_ID",
        help="Judge LLM model ID (default: system default)",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Validate inputs and print intended mutation without writing server state.")
    p.set_defaults(func=run_evaluator_create)

    # codeer eval evaluator-update
    p = sub.add_parser("evaluator-update", help="Update an evaluator in the workspace; run --dry-run first")
    p.add_argument("--evaluator", required=True, help="Evaluator UUID")
    p.add_argument("--name", default=None)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--system-prompt-template", help="Evaluator system prompt template text")
    g.add_argument("--system-prompt-template-file", help="Path to evaluator system prompt template")
    p.add_argument("--description", default=None)
    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "--judge-model",
        default=None,
        metavar="MODEL_ID",
        help="Set the judge LLM model ID",
    )
    g.add_argument(
        "--clear-judge-model",
        action="store_true",
        help="Clear the evaluator override and use the system default judge model",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Validate inputs and print intended mutation without writing server state.")
    p.set_defaults(func=run_evaluator_update)

    # codeer eval run
    p = sub.add_parser("run", help="Trigger eval run, poll for results, print scores")
    p.add_argument("--agent", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--history", default=None, help="History UUID to pin the run to")
    g.add_argument("--latest", action="store_true",
                   help="Auto-select the newest AgentHistory (default)")
    p.add_argument("--cases", default=None, help="Comma-separated case UUIDs (default: all)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--evaluator", default=None, help="Evaluator UUID; common path for running many cases with one tester")
    g.add_argument("--evaluators", default=None, help="Comma-separated evaluator UUIDs")
    p.add_argument("--poll-timeout", type=int, default=POLL_TIMEOUT)
    p.add_argument("--full", action="store_true",
                   help="Use longer previews in stdout. Raw outputs/tool calls still require --out.")
    p.add_argument("--out", default=None,
                   help="Write complete eval result artifact, including raw outputs/tool calls, to this file.")
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
    p = sub.add_parser("cases-apply", help="Create/update eval cases from JSON manifest; run --dry-run first")
    p.add_argument("--cases", required=True, help="Path to eval_cases.json")
    p.add_argument("--agent", required=True)
    p.add_argument("--attachments-dir", default=None, dest="attachments_dir")
    p.add_argument("--allow-duplicates", action="store_true")
    p.add_argument("--create-labels", action="store_true",
                   help="Create missing labels referenced by manifest case labels.")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate manifest and print intended mutations without writing server state.")
    p.add_argument("--out", default=None)
    p.set_defaults(func=run_cases_apply)

    # codeer eval rubrics
    p = sub.add_parser("rubrics", help="Read assigned per-(case, evaluator) rubrics")
    p.add_argument("--agent", required=True)
    p.add_argument("--evaluators", default=None, help="Comma-separated evaluator UUIDs")
    p.add_argument("--cases", default=None, help="Comma-separated case UUIDs")
    p.add_argument("--all-pairs", action="store_true",
                   help="With omitted --evaluators, scan every workspace evaluator instead of assigned pairs only.")
    p.add_argument("--full", action="store_true",
                   help="Print complete rubric text. Default prints matrix summaries/previews.")
    p.add_argument("--out", default=None,
                   help="Write complete rubric matrix to this file.")
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

def _case_summary(case: dict, *, full: bool = False) -> dict:
    labels = case.get("labels") or []
    row = {
        "id": case.get("id"),
        "input_preview": truncate(case.get("input") or "", 240 if full else 80),
        "input_chars": len(case.get("input") or ""),
        "expected_output_chars": len(case.get("expected_output") or ""),
        "note_preview": truncate(case.get("note") or "", 180 if full else 100),
        "attachment_count": len(case.get("attachments") or case.get("attachment_ids") or []),
        "labels": [
            {"id": label.get("id"), "name": label.get("name"), "color": label.get("color")}
            for label in labels
            if isinstance(label, dict)
        ],
    }
    if full:
        row["created_at"] = case.get("created_at")
        row["updated_at"] = case.get("updated_at")
        row["meta"] = case.get("meta") or {}
        row["expected_output_preview"] = truncate(case.get("expected_output") or "", 600)
    return row


def _evaluator_summary(evaluator: dict, *, full: bool = False) -> dict:
    template = evaluator.get("system_prompt_template") or ""
    row = {
        "id": evaluator.get("id"),
        "name": evaluator.get("name"),
        "description": evaluator.get("description"),
        "judge_llm_model_id": evaluator.get("judge_llm_model_id"),
        "system_prompt_template_chars": len(template),
        "has_tool_steps_placeholder": "{tool_steps}" in template,
        "has_output_placeholder": "{output}" in template,
        "created_at": evaluator.get("created_at"),
        "updated_at": evaluator.get("updated_at"),
    }
    if full:
        row["system_prompt_template"] = template
    else:
        row["system_prompt_template_preview"] = truncate(template, 240)
    return row


def run_list(args, client) -> int:
    cases = eval_mod.list_cases(client, args.agent)
    full_cases = strip_noisy_fields(cases)
    write_json(args.out, full_cases)
    shown = cases if args.all else cases[:args.limit]
    if args.full:
        payload = strip_noisy_fields(shown)
    else:
        payload = [_case_summary(c) for c in shown]
    print_json({
        "agent_id": args.agent,
        "case_count": len(cases),
        "returned_count": len(shown),
        "limit": None if args.all else args.limit,
        "wrote_full_detail": bool(args.out),
        "cases": payload,
    })
    return 0


# ---------------------------------------------------------------------------
# eval case labels
# ---------------------------------------------------------------------------

def _active_workspace(client) -> str:
    ws, _ = client.resolve_scope()
    return ws


def _label_summary(label: dict) -> dict:
    return {
        "id": label.get("id"),
        "name": label.get("name"),
        "color": label.get("color"),
        "workspace_id": label.get("workspace_id"),
    }


def run_label_list(args, client) -> int:
    workspace_id = _active_workspace(client)
    labels = eval_mod.list_case_labels(client)
    out = {
        "workspace_id": workspace_id,
        "label_count": len(labels),
        "labels": [_label_summary(label) for label in labels],
    }
    print_json(out)
    write_json(args.out, out)
    return 0


def run_label_create(args, client) -> int:
    workspace_id = _active_workspace(client)
    if args.dry_run:
        out = {
            "dry_run": True,
            "operation": "label_create",
            "method": "POST",
            "path": "/external/eval/case-labels",
            "workspace_id": workspace_id,
            "name": args.name,
            "color": args.color,
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(out)
        write_json(args.out, out)
        return 0

    label = eval_mod.create_case_label(client, name=args.name, color=args.color)
    out = _label_summary(strip_noisy_fields(label))
    print_json(out)
    write_json(args.out, out)
    return 0


def run_label_update(args, client) -> int:
    if args.name is None and args.color is None:
        log("error: provide --name and/or --color")
        return 2

    if args.dry_run:
        out = {
            "dry_run": True,
            "operation": "label_update",
            "method": "PUT",
            "path": f"/external/eval/case-labels/{args.label_id}",
            "label_id": args.label_id,
            "updates": {"name": args.name, "color": args.color},
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(out)
        write_json(args.out, out)
        return 0

    label = eval_mod.update_case_label(
        client, label_id=args.label_id, name=args.name, color=args.color
    )
    out = _label_summary(strip_noisy_fields(label))
    print_json(out)
    write_json(args.out, out)
    return 0


def run_label_delete(args, client) -> int:
    if args.dry_run:
        out = {
            "dry_run": True,
            "operation": "label_delete",
            "method": "DELETE",
            "path": f"/external/eval/case-labels/{args.label_id}",
            "label_id": args.label_id,
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(out)
        write_json(args.out, out)
        return 0

    deleted = strip_noisy_fields(eval_mod.delete_case_label(client, label_id=args.label_id))
    print_json(deleted)
    write_json(args.out, deleted)
    return 0


# ---------------------------------------------------------------------------
# eval case-update / case-delete
# ---------------------------------------------------------------------------

def _read_text_arg(value: str | None, file_path: str | None) -> str | None:
    if file_path is not None:
        return Path(file_path).read_text()
    return value


def _read_meta_arg(value: str | None, file_path: str | None) -> dict | None:
    if file_path is not None:
        raw = Path(file_path).read_text()
    elif value is not None:
        raw = value
    else:
        return None

    meta = json.loads(raw)
    if not isinstance(meta, dict):
        raise ValueError("case meta must be a JSON object")
    return meta


def run_case_update(args, client) -> int:
    try:
        input_text = _read_text_arg(args.input, args.input_file)
        expected_output = _read_text_arg(args.expected_output, args.expected_output_file)
        rubric = _read_text_arg(args.rubric, args.rubric_file)
        note = _read_text_arg(args.note, args.note_file)
        meta = _read_meta_arg(args.meta_json, args.meta_file)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        log(f"error: {e}")
        return 2
    attachment_ids = _ids(args.attachment_ids)
    label_ids = [] if args.clear_labels else _ids(args.label_ids)

    has_update = any(
        value is not None
        for value in (input_text, expected_output, rubric, note, meta, attachment_ids, label_ids)
    ) or args.clear_labels
    if not has_update:
        log(
            "error: provide at least one of --input, --input-file, --expected-output, "
            "--expected-output-file, --rubric, --rubric-file, --note, --note-file, "
            "--meta-json, --meta-file, --attachment-ids, --label-ids, --clear-labels"
        )
        return 2

    if args.dry_run:
        current = strip_noisy_fields(eval_mod.get_case(client, args.case_id))
        out = {
            "dry_run": True,
            "operation": "case_update",
            "method": "PUT",
            "path": f"/external/eval/cases/{args.case_id}",
            "case_id": args.case_id,
            "current": _case_summary(current, full=True),
            "updates": {
                "input_chars": len(input_text) if input_text is not None else None,
                "expected_output_chars": (
                    len(expected_output) if expected_output is not None else None
                ),
                "rubric_chars": len(rubric) if rubric is not None else None,
                "note_chars": len(note) if note is not None else None,
                "meta": meta,
                "attachment_ids": attachment_ids,
                "label_ids": label_ids,
            },
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(out)
        write_json(args.out, out)
        return 0

    updated = eval_mod.update_case(
        client,
        args.case_id,
        input=input_text,
        expected_output=expected_output,
        rubric=rubric,
        attachment_ids=attachment_ids,
        label_ids=label_ids,
        meta=meta,
        note=note,
    )
    out = strip_noisy_fields(updated)
    print_json(out)
    write_json(args.out, out)
    return 0


def run_case_delete(args, client) -> int:
    if args.dry_run:
        current = strip_noisy_fields(eval_mod.get_case(client, args.case_id))
        out = {
            "dry_run": True,
            "operation": "case_delete",
            "method": "DELETE",
            "path": f"/external/eval/cases/{args.case_id}",
            "case_id": args.case_id,
            "current": _case_summary(current, full=True),
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(out)
        write_json(args.out, out)
        return 0

    deleted = strip_noisy_fields(eval_mod.delete_case(client, args.case_id))
    print_json(deleted)
    write_json(args.out, deleted)
    return 0


# ---------------------------------------------------------------------------
# eval evaluators
# ---------------------------------------------------------------------------

def run_evaluators(args, client) -> int:
    ws, _ = client.resolve_scope()
    evaluators = eval_mod.list_evaluators(client, ws)
    full_evaluators = strip_noisy_fields(evaluators)
    write_json(args.out, full_evaluators)
    print_json(full_evaluators if args.full else [_evaluator_summary(e) for e in evaluators])
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
    if args.dry_run:
        print_json({
            "dry_run": True,
            "operation": "create_evaluator",
            "workspace_id": workspace_id,
            "name": args.name,
            "description": args.description,
            "judge_model": {
                "action": "set" if args.judge_model is not None else "use_system_default",
                "model_id": args.judge_model,
            },
            "system_prompt_template_chars": len(system_prompt_template or ""),
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        })
        return 0
    evaluator = eval_mod.create_evaluator(
        client,
        workspace_id=workspace_id,
        name=args.name,
        system_prompt_template=system_prompt_template,
        description=args.description,
        judge_llm_model_id=args.judge_model,
    )
    print_json(_evaluator_summary(evaluator, full=True))
    return 0


# ---------------------------------------------------------------------------
# eval evaluator-update
# ---------------------------------------------------------------------------

def run_evaluator_update(args, client) -> int:
    if args.system_prompt_template_file:
        system_prompt_template = Path(args.system_prompt_template_file).read_text()
    else:
        system_prompt_template = args.system_prompt_template

    if (
        args.name is None
        and args.description is None
        and system_prompt_template is None
        and args.judge_model is None
        and not args.clear_judge_model
    ):
        log(
            "error: provide at least one of --name, --description, "
            "--system-prompt-template, --system-prompt-template-file, "
            "--judge-model, --clear-judge-model"
        )
        return 2

    if args.clear_judge_model:
        judge_model = {"action": "clear_to_system_default", "model_id": None}
    elif args.judge_model is not None:
        judge_model = {"action": "set", "model_id": args.judge_model}
    else:
        judge_model = {"action": "unchanged"}

    if args.dry_run:
        print_json({
            "dry_run": True,
            "operation": "update_evaluator",
            "evaluator_id": args.evaluator,
            "name": args.name,
            "description": args.description,
            "judge_model": judge_model,
            "system_prompt_template_chars": (
                len(system_prompt_template) if system_prompt_template is not None else None
            ),
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        })
        return 0

    evaluator_kwargs: dict[str, Any] = {
        "name": args.name,
        "system_prompt_template": system_prompt_template,
        "description": args.description,
    }
    if args.clear_judge_model:
        evaluator_kwargs["judge_llm_model_id"] = None
    elif args.judge_model is not None:
        evaluator_kwargs["judge_llm_model_id"] = args.judge_model

    evaluator = eval_mod.update_evaluator(
        client,
        evaluator_id=args.evaluator,
        **evaluator_kwargs,
    )
    print_json(_evaluator_summary(evaluator, full=True))
    return 0


# ---------------------------------------------------------------------------
# eval run
# ---------------------------------------------------------------------------

def _assigned_evaluators_by_case(info_rows: list[dict]) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for row in info_rows:
        case_id = row.get("case_id")
        if not case_id:
            continue
        out[str(case_id)] = {
            str(info.get("evaluator_id")): info
            for info in (row.get("evaluators") or [])
            if info.get("evaluator_id")
        }
    return out


def _planned_eval_pairs(
    *,
    case_ids: list[str],
    assigned_by_case: dict[str, dict[str, dict]],
    requested_evaluator_ids: list[str] | None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    pairs: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    if requested_evaluator_ids:
        for case_id in case_ids:
            assigned = assigned_by_case.get(case_id, {})
            for evaluator_id in requested_evaluator_ids:
                if evaluator_id in assigned:
                    pairs.append({"case_id": case_id, "evaluator_id": evaluator_id})
                else:
                    skipped.append({
                        "case_id": case_id,
                        "evaluator_id": evaluator_id,
                        "reason": "not_assigned",
                    })
        return pairs, skipped

    for case_id in case_ids:
        for evaluator_id in assigned_by_case.get(case_id, {}):
            pairs.append({"case_id": case_id, "evaluator_id": evaluator_id})
    return pairs, skipped


def _group_case_ids_by_evaluator(pairs: list[dict[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for pair in pairs:
        grouped[pair["evaluator_id"]].append(pair["case_id"])
    return dict(grouped)


def _pairs_from_rubric_batches(
    client,
    *,
    case_ids: list[str],
    evaluator_ids: list[str],
) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    for evaluator_id in evaluator_ids:
        for row in eval_mod.get_rubrics_batch(client, case_ids=case_ids, evaluator_id=evaluator_id):
            if row.get("rubric"):
                case_id = row.get("case_id") or row.get("evaluation_case_id")
                if case_id:
                    pairs.append({"case_id": str(case_id), "evaluator_id": evaluator_id})
    return pairs


def _pair_key(pair: dict[str, str]) -> tuple[str, str]:
    return pair["case_id"], pair["evaluator_id"]


def _skipped_pairs_from_trigger_response(response: Any) -> list[dict[str, str]]:
    if not isinstance(response, dict):
        return []
    payload = response.get("data") if isinstance(response.get("data"), dict) else response
    skipped = payload.get("skipped_pairs") if isinstance(payload, dict) else None
    if not isinstance(skipped, list):
        return []

    out: list[dict[str, str]] = []
    for row in skipped:
        if not isinstance(row, dict):
            continue
        case_id = row.get("case_id")
        evaluator_id = row.get("evaluator_id")
        if not case_id or not evaluator_id:
            continue
        out.append({
            "case_id": str(case_id),
            "evaluator_id": str(evaluator_id),
            "reason": str(row.get("reason") or "skipped"),
        })
    return out


def _remove_non_runnable_skipped_pairs(
    pairs: list[dict[str, str]],
    skipped_pairs: list[dict[str, str]],
) -> list[dict[str, str]]:
    non_runnable = {
        _pair_key(pair)
        for pair in skipped_pairs
        if pair.get("reason") == "not_assigned"
    }
    if not non_runnable:
        return pairs
    return [pair for pair in pairs if _pair_key(pair) not in non_runnable]


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

    evaluator_ids = [args.evaluator] if args.evaluator else (_ids(args.evaluators) or [])
    requested_evaluator_ids = evaluator_ids or None

    skipped_unassigned: list[dict[str, str]] = []
    if requested_evaluator_ids:
        pairs = [
            {"case_id": case_id, "evaluator_id": evaluator_id}
            for evaluator_id in requested_evaluator_ids
            for case_id in case_ids
        ]
    else:
        evaluator_ids = [e["id"] for e in eval_mod.list_evaluators(client, workspace_id)]
        pairs = _pairs_from_rubric_batches(
            client,
            case_ids=case_ids,
            evaluator_ids=evaluator_ids,
        )
    if not pairs:
        log("error: no case/evaluator pairs to run")
        print_json({
            "agent_id": args.agent,
            "history_id": args.history,
            "requested_case_count": len(case_ids),
            "requested_evaluator_count": len(evaluator_ids),
            "triggered_pair_count": 0,
            "skipped_unassigned": skipped_unassigned,
        })
        return 2

    evaluator_ids = _dedupe_preserve_order([pair["evaluator_id"] for pair in pairs])
    evaluators = [eval_mod.get_evaluator(client, eid) for eid in evaluator_ids]

    case_label_by_id = {c["id"]: truncate(c.get("input") or "", 60) for c in case_objs}
    evaluator_name_by_id = {e["id"]: e.get("name", e["id"]) for e in evaluators}

    requested_pairs = list(pairs)
    requested_pair_count = len(requested_pairs)
    log(f"triggering: {requested_pair_count} case/evaluator pairs on history {args.history}")
    trigger_response: list[dict[str, Any]] = []
    skipped_pairs: list[dict[str, str]] = []
    for ev_id, ev_case_ids in _group_case_ids_by_evaluator(pairs).items():
        response = eval_mod.trigger(
            client,
            case_ids=ev_case_ids,
            evaluator_ids=[ev_id],
            agent_history_id=args.history,
        )
        response_skipped = _skipped_pairs_from_trigger_response(response)
        skipped_pairs.extend(response_skipped)
        trigger_response.append({
            "evaluator_id": ev_id,
            "case_ids": ev_case_ids,
            "response": response,
            "skipped_pairs": response_skipped,
        })

    pairs = _remove_non_runnable_skipped_pairs(pairs, skipped_pairs)
    skipped_unassigned = [pair for pair in skipped_pairs if pair.get("reason") == "not_assigned"]
    if skipped_unassigned:
        log(f"skipping {len(skipped_unassigned)} not-assigned pairs from polling")
    if not pairs:
        log("error: no runnable case/evaluator pairs after trigger response")
        print_json({
            "agent_id": args.agent,
            "history_id": args.history,
            "requested_case_count": len(case_ids),
            "requested_evaluator_count": len(requested_evaluator_ids or evaluator_ids),
            "requested_pair_count": requested_pair_count,
            "triggered_pair_count": 0,
            "skipped_pair_count": len(skipped_pairs),
            "skipped_unassigned_count": len(skipped_unassigned),
            "trigger_response": trigger_response,
            "skipped_pairs": skipped_pairs,
            "skipped_unassigned": skipped_unassigned,
        })
        return 2

    deadline = time.time() + args.poll_timeout
    results_by_eval: dict[str, list[dict]] = {}
    case_ids_by_evaluator = _group_case_ids_by_evaluator(pairs)
    target_pair_keys = {(pair["case_id"], pair["evaluator_id"]) for pair in pairs}
    while time.time() < deadline:
        results_by_eval = {}
        done_pairs: set[tuple[str, str]] = set()
        total = len(pairs)
        for ev_id, ev_case_ids in case_ids_by_evaluator.items():
            rows = eval_mod.get_results(
                client, case_ids=ev_case_ids, evaluator_id=ev_id,
                agent_history_id=args.history, workspace_id=workspace_id,
                include_output=True, include_reasoning_steps=True,
            )
            results_by_eval[ev_id] = rows
            for row in rows:
                key = (row.get("case_id") or row.get("evaluation_case_id"), ev_id)
                if key in target_pair_keys and row.get("score") is not None:
                    done_pairs.add(key)
        log(f"  progress: {len(done_pairs)}/{total}")
        if len(done_pairs) >= total:
            break
        time.sleep(POLL_INTERVAL)

    flat: list[dict] = []
    for ev_id, rows in results_by_eval.items():
        for r in rows:
            row_case_id = r.get("case_id") or r.get("evaluation_case_id")
            if (row_case_id, ev_id) not in target_pair_keys:
                continue
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

    scored_pair_keys = {
        (r.get("case_id"), r.get("evaluator_id"))
        for r in flat
        if r.get("score") is not None
    }
    all_perfect = (
        len(scored_pair_keys) == len(target_pair_keys)
        and all((r.get("score") or 0.0) >= 1.0 for r in flat)
    )
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

    preview_chars = 1200 if args.full else 360
    result_summaries = []
    for r in flat:
        result_summaries.append({
            "case_id": r.get("case_id"),
            "case_label": r.get("case_label"),
            "evaluator_id": r.get("evaluator_id"),
            "evaluator_name": r.get("evaluator_name"),
            "score": r.get("score"),
            "status": r.get("status"),
            "reason_preview": truncate(r.get("reason") or "", preview_chars),
            "output_preview": truncate(r.get("output") or "", preview_chars),
            "execution_time_s": r.get("execution_time_s"),
            "cost_credits": r.get("cost_credits"),
            "tool_call_count": r.get("tool_call_count"),
            "tool_total_duration_ms": r.get("tool_total_duration_ms"),
            "tool_calls_summary": truncate(r.get("tool_calls_summary") or "", preview_chars),
        })

    out = {
        "agent_id": args.agent,
        "history_id": args.history,
        "requested_case_count": len(case_ids),
        "requested_evaluator_count": len(requested_evaluator_ids or evaluator_ids),
        "requested_pair_count": requested_pair_count,
        "triggered_pair_count": len(pairs),
        "scored_pair_count": len(scored_pair_keys),
        "skipped_pair_count": len(skipped_pairs),
        "skipped_unassigned_count": len(skipped_unassigned),
        "all_perfect": all_perfect,
        "result_count": len(result_summaries),
        "non_perfect_count": len(non_perfect),
        "wrote_full_detail": bool(args.out),
        "trigger_response": trigger_response,
        "skipped_pairs": skipped_pairs,
        "skipped_unassigned": skipped_unassigned,
        "results": result_summaries,
    }
    full_out = {
        "agent_id": args.agent,
        "history_id": args.history,
        "requested_pairs": requested_pairs,
        "triggered_pairs": pairs,
        "trigger_response": trigger_response,
        "skipped_pairs": skipped_pairs,
        "skipped_unassigned": skipped_unassigned,
        "all_perfect": all_perfect,
        "results": flat,
    }
    write_json(args.out, full_out)
    print_json(out)
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


def _manifest_label_names(case: dict) -> list[str]:
    raw = case.get("labels")
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"case '{case.get('label')}' labels must be a list of label names")
    return [item.strip() for item in raw if item.strip()]


def _manifest_label_ids(case: dict) -> list[str] | None:
    raw = case.get("label_ids")
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"case '{case.get('label')}' label_ids must be a list of label ID strings")
    return [item.strip() for item in raw if item.strip()]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _resolve_case_label_ids(case: dict, labels_by_name: dict[str, dict]) -> tuple[list[str] | None, list[str]]:
    explicit_ids = _manifest_label_ids(case)
    label_names = _manifest_label_names(case)
    if explicit_ids is None and not label_names:
        return None, []

    resolved_ids = list(explicit_ids or [])
    for name in label_names:
        label = labels_by_name.get(name.casefold())
        if label is None:
            raise ValueError(f"case '{case.get('label')}' references unknown label '{name}'")
        resolved_ids.append(str(label["id"]))
    return _dedupe_preserve_order(resolved_ids), label_names


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
    try:
        manifest_label_names = sorted({
            name
            for case in cases
            for name in _manifest_label_names(case)
        }, key=str.casefold)
        for case in cases:
            _manifest_label_ids(case)
    except ValueError as e:
        log(f"error: {e}")
        return 2

    labels_by_name: dict[str, dict] = {}
    created_labels: list[dict] = []
    would_create_labels: list[str] = []
    if manifest_label_names:
        labels_by_name = {
            (label.get("name") or "").casefold(): label
            for label in eval_mod.list_case_labels(client)
            if label.get("name")
        }
        missing_label_names = [
            name for name in manifest_label_names
            if name.casefold() not in labels_by_name
        ]
        if missing_label_names and not args.create_labels:
            log(
                "error: manifest references missing labels: "
                + ", ".join(missing_label_names)
                + ". Create them first with `codeer eval label-create`, "
                + "or rerun cases-apply with --create-labels."
            )
            return 2
        if args.dry_run:
            would_create_labels = missing_label_names
            for name in missing_label_names:
                labels_by_name[name.casefold()] = {
                    "id": f"(new:{name})",
                    "name": name,
                    "color": "#0969da",
                }
        else:
            for name in missing_label_names:
                log(f"creating label: {name}")
                label = eval_mod.create_case_label(client, name=name)
                labels_by_name[name.casefold()] = label
                created_labels.append(_label_summary(label))

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
    dry_run_updates: list[dict] = []
    for case in cases:
        rubrics = dict(case.get("rubrics") or {})
        if shared_style_rubric:
            for ev_id in shared_style_evals:
                rubrics.setdefault(ev_id, shared_style_rubric)
        if not rubrics:
            log(f"error: case '{case.get('label')}' has no rubrics")
            return 2

        label = case.get("label", "(unlabeled)")
        try:
            case_label_ids, case_label_names = _resolve_case_label_ids(case, labels_by_name)
        except ValueError as e:
            log(f"error: {e}")
            return 2
        attachment_ids: list[str] = []
        for fname in case.get("attachment_files") or []:
            fp = (attach_dir / fname).resolve() if attach_dir else None
            if not fp or not fp.is_file():
                log(f"error: attachment file not found for case '{label}': {fname}")
                return 2
            if args.dry_run:
                attachment_ids.append(fname)
                continue
            log(f"  uploading attachment: {fname}")
            uid = _upload_attachment(client, file_path=fp, workspace_id=workspace_id)
            attachment_ids.append(uid)

        existing = existing_by_input.get(case["input"])
        if existing is not None:
            case_id = existing["id"]
            if args.dry_run:
                case_ids.append(case_id)
                labels.append(label)
                reused.append({"case_id": case_id, "label": label})
                dry_run_updates.append({
                    "case_id": case_id,
                    "label": label,
                    "would_update_case_metadata": bool(
                        case.get("expected_output") is not None
                        or attachment_ids
                        or case.get("meta") is not None
                        or case.get("note") is not None
                        or case_label_ids is not None
                    ),
                    "labels": case_label_names,
                    "label_ids": case_label_ids,
                    "rubric_count": len(rubrics),
                })
                continue
            log(f"reusing existing case: {label} ({case_id[:8]})")
            if (
                case.get("expected_output") is not None
                or attachment_ids
                or case.get("meta") is not None
                or case.get("note") is not None
                or case_label_ids is not None
            ):
                eval_mod.update_case(
                    client, case_id,
                    expected_output=case.get("expected_output"),
                    attachment_ids=attachment_ids or None,
                    label_ids=case_label_ids,
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

        if args.dry_run:
            labels.append(label)
            created.append({
                "label": label,
                "input_chars": len(case.get("input") or ""),
                "expected_output_chars": len(case.get("expected_output") or ""),
                "attachment_count": len(attachment_ids),
                "labels": case_label_names,
                "label_ids": case_label_ids,
                "rubric_count": len(rubrics),
            })
            continue

        log(f"creating: {label}")
        result = eval_mod.create_case_with_rubrics(
            client, agent_id=args.agent, input=case["input"],
            expected_output=case.get("expected_output"),
            attachment_ids=attachment_ids or None,
            label_ids=case_label_ids,
            rubrics_by_evaluator=rubrics, meta=case.get("meta"),
            note=case.get("note"),
        )
        case_ids.append(result["id"])
        labels.append(label)
        created.append({"case_id": result["id"], "label": label})

    out = {
        "case_ids": case_ids,
        "labels": labels,
        "created": created,
        "reused": reused,
        "created_case_labels": created_labels,
    }
    if args.dry_run:
        out.update({
            "dry_run": True,
            "operation": "cases_apply",
            "agent_id": args.agent,
            "would_create_case_labels": would_create_labels,
            "updates": dry_run_updates,
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        })
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

    rubrics = eval_mod.get_case_rubrics(
        client, agent_id=args.agent, workspace_id=workspace_id,
        evaluator_ids=evaluator_ids, case_ids=case_ids,
    )
    assigned_by_case = {
        cid: {
            ev_id: {"evaluator_id": ev_id, "rubric": rubric_text}
            for ev_id, rubric_text in (rubrics.get(cid) or {}).items()
            if rubric_text
        }
        for cid in case_ids
    }

    if args.evaluators or args.all_pairs:
        pass
    else:
        evaluator_ids = _dedupe_preserve_order([
            evaluator_id
            for case_id in case_ids
            for evaluator_id in assigned_by_case.get(case_id, {})
        ])
        evaluator_id_set = set(evaluator_ids)
        evaluators = [e for e in evaluators if e["id"] in evaluator_id_set]
    evaluator_name = {e["id"]: e.get("name", e["id"]) for e in evaluators}
    if not evaluator_ids:
        log("error: no evaluators with configured rubrics for these cases")
        return 2

    mode = "all requested pairs" if args.evaluators or args.all_pairs else "pairs with configured rubrics"
    log(f"reading {mode}: {len(case_ids)} cases, {len(evaluator_ids)} evaluators...")

    if args.full:
        for cid in case_ids:
            log("=" * 80)
            log(f"CASE {cid}")
            log(f"  input: {truncate(case_input.get(cid, ''), 120)}")
            for ev_id in evaluator_ids:
                is_assigned = ev_id in assigned_by_case.get(cid, {})
                if not is_assigned and not (args.evaluators or args.all_pairs):
                    continue
                ev_name = evaluator_name.get(ev_id, ev_id)
                rubric_text = (rubrics.get(cid) or {}).get(ev_id, "")
                if not is_assigned:
                    log(f"  [{ev_name}] (not assigned)")
                    continue
                if not rubric_text:
                    log(f"  [{ev_name}] (rubric not set)")
                else:
                    log(f"  [{ev_name}]")
                    for line in rubric_text.splitlines():
                        log(f"    {line}")

    summary_cases = []
    for cid in case_ids:
        rubrics_summary = {}
        for ev_id in evaluator_ids:
            is_assigned = ev_id in assigned_by_case.get(cid, {})
            if not is_assigned and not (args.evaluators or args.all_pairs):
                continue
            rubric_text = (rubrics.get(cid) or {}).get(ev_id, "")
            rubrics_summary[ev_id] = {
                "evaluator_name": evaluator_name.get(ev_id, ev_id),
                "is_assigned": is_assigned,
                "is_set": bool(rubric_text),
                "chars": len(rubric_text),
                "preview": truncate(rubric_text, 240),
            }
        summary_cases.append({
            "case_id": cid,
            "input_preview": truncate(case_input.get(cid, ""), 160),
            "rubrics_by_evaluator": rubrics_summary,
        })

    out = {
        "agent_id": args.agent,
        "workspace_id": workspace_id,
        "mode": mode,
        "evaluators": [{"id": e["id"], "name": e.get("name")} for e in evaluators],
        "cases": [
            {
                "case_id": cid,
                "input": case_input.get(cid, ""),
                "rubrics_by_evaluator": {
                    ev_id: (rubrics.get(cid) or {}).get(ev_id)
                    for ev_id in evaluator_ids
                    if ev_id in assigned_by_case.get(cid, {}) or args.evaluators or args.all_pairs
                },
                "assigned_evaluator_ids": list(assigned_by_case.get(cid, {})),
            }
            for cid in case_ids
        ],
    }
    write_json(args.out, out)
    if args.full:
        print_json(out)
    else:
        print_json({
            "agent_id": args.agent,
            "workspace_id": workspace_id,
            "mode": mode,
            "evaluator_count": len(evaluators),
            "case_count": len(case_ids),
            "wrote_full_detail": bool(args.out),
            "evaluators": [{"id": e["id"], "name": e.get("name")} for e in evaluators],
            "cases": summary_cases,
        })
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
