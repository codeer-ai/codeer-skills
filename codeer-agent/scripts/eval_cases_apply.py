"""Reusable: create eval cases (with per-evaluator rubrics) from a JSON file.

Usage:
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/eval_cases_apply.py \
        --cases ./eval_cases.json \
        --agent <agent_id> \
        [--workspace <ws_id>] \
        [--attachments-dir ./attachments] \
        [--out eval_case_ids.json]
        [--allow-duplicates]

JSON shape (the "rubrics" map is keyed by evaluator UUID — get them via the
UI or `codeer get /eval/evaluators --param wid=<ws>`):

    {
      "cases": [
        {
          "label": "A. Personal career confusion",
          "input": "I am ... can you help me?",
          "expected_output": null,                       # optional
          "attachment_files": ["cat_selfie.jpg"],        # optional — see below
          "meta": {                                       # optional — multi-turn seed
            "previous_conversations": {
              "source_history_id": 10197,                 # int, History.id from /histories
              "target_conversation_id": 43350,            # int, Conversation.id where input replaces this turn
              "previous_conversation_count": 6            # int, number of replayed user/assistant turns before input
            }
          },
          "rubrics": {
            "<style_evaluator_id>": "...",
            "<content_evaluator_id>": "..."
          }
        },
        ...
      ]
    }

If you pass `"shared_style_rubric": "..."` at the top level of the JSON, every
case will get that rubric for every evaluator id listed in
`"shared_style_evaluators": ["...", "..."]` — useful when the style rubric
is the same across cases. Per-case rubrics in `rubrics` override.

Attachments (optional):
- Each case may list filenames in ``attachment_files`` (relative to
  ``--attachments-dir``).
- Each file is uploaded via POST /retrieval/upload-file with
  ``is_evaluation_context=true`` and the resulting ``data.uuid`` is attached
  to the case. ``--workspace`` is required when ``attachment_files`` is used.
- Common image MIMEs (jpg/png/webp/gif/pdf) are inferred from the extension.

By default, this script is idempotent by exact ``input``. If a case with the
same input already exists for the agent, the script reuses that case and
updates its rubrics instead of creating a duplicate. Pass
``--allow-duplicates`` only when duplicate inputs are intentional.

Writes JSON to stdout:
    {"case_ids": ["...", ...], "labels": ["...", ...], "created": [...], "reused": [...]}
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient  # noqa: E402
from codeer_cli import eval_ as eval_mod  # noqa: E402


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _upload_attachment(c: CodeerClient, *, file_path: Path, workspace_id: str) -> str:
    """Upload a single file as an evaluation-context attachment, return its uuid."""
    ct, _ = mimetypes.guess_type(file_path.name)
    ct = ct or "application/octet-stream"
    files = {"file": (file_path.name, file_path.read_bytes(), ct)}
    data = {"data": json.dumps({
        "workspace_id": workspace_id,
        "scope": "persistent",
        "is_evaluation_context": True,
    })}
    uploaded = c.post("/retrieval/upload-file", files=files, data=data)
    uuid = uploaded.get("uuid") if isinstance(uploaded, dict) else None
    if not uuid:
        raise RuntimeError(f"upload-file response missing uuid for {file_path.name}: {uploaded}")
    return uuid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True, help="Path to eval_cases.json")
    ap.add_argument("--agent", required=True, help="Agent UUID these cases belong to")
    ap.add_argument("--workspace", default=None,
                    help="Workspace UUID — required when any case has attachment_files. "
                         "Defaults to CODEER_WORKSPACE_ID env if not passed.")
    ap.add_argument("--attachments-dir", default=None, dest="attachments_dir",
                    help="Directory holding the files referenced in attachment_files")
    ap.add_argument("--allow-duplicates", action="store_true",
                    help="Create a new case even when an existing case has the same exact input")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    payload = json.loads(Path(args.cases).read_text())
    cases = payload.get("cases") or []
    if not cases:
        _log("error: no cases in payload")
        return 2

    shared_style_rubric = payload.get("shared_style_rubric")
    shared_style_evals = payload.get("shared_style_evaluators") or []

    needs_attach = any(case.get("attachment_files") for case in cases)
    attach_dir: Optional[Path] = Path(args.attachments_dir) if args.attachments_dir else None
    if needs_attach and attach_dir is None:
        _log("error: at least one case has attachment_files, but --attachments-dir was not provided")
        return 2
    if needs_attach and attach_dir and not attach_dir.is_dir():
        _log(f"error: --attachments-dir does not exist or is not a directory: {attach_dir}")
        return 2

    with CodeerClient.from_env() as c:
        workspace_id = args.workspace or c.workspace_id
        if needs_attach and not workspace_id:
            _log("error: attachment uploads require --workspace or CODEER_WORKSPACE_ID")
            return 2

        existing_by_input: dict[str, dict] = {}
        if not args.allow_duplicates:
            for existing in eval_mod.list_cases(c, args.agent):
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
                _log(f"error: case '{case.get('label')}' has no rubrics — provide per-evaluator rubrics")
                return 2

            label = case.get("label", "(unlabeled)")
            attachment_ids: list[str] = []
            for fname in case.get("attachment_files") or []:
                fp = (attach_dir / fname).resolve() if attach_dir else None
                if not fp or not fp.is_file():
                    _log(f"error: attachment file not found for case '{label}': {fname}")
                    return 2
                _log(f"  uploading attachment: {fname}")
                uid = _upload_attachment(c, file_path=fp, workspace_id=workspace_id)  # type: ignore[arg-type]
                attachment_ids.append(uid)

            existing = existing_by_input.get(case["input"])
            if existing is not None:
                case_id = existing["id"]
                _log(f"reusing existing case: {label} ({case_id[:8]})")
                if case.get("expected_output") is not None or attachment_ids or case.get("meta") is not None:
                    eval_mod.update_case(
                        c,
                        case_id,
                        expected_output=case.get("expected_output"),
                        attachment_ids=attachment_ids or None,
                        meta=case.get("meta"),
                    )
                for ev_id, rubric in rubrics.items():
                    eval_mod.set_rubric(c, evaluation_case_id=case_id, evaluator_id=ev_id, rubric=rubric)
                case_ids.append(case_id)
                labels.append(label)
                reused.append({"case_id": case_id, "label": label})
                continue

            _log(f"creating: {label}")
            result = eval_mod.create_case_with_rubrics(
                c,
                agent_id=args.agent,
                input=case["input"],
                expected_output=case.get("expected_output"),
                attachment_ids=attachment_ids or None,
                rubrics_by_evaluator=rubrics,
                meta=case.get("meta"),
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


if __name__ == "__main__":
    raise SystemExit(main())
