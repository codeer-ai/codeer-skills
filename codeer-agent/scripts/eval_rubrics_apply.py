"""Apply rubric changes from a JSON file.

Pairs with ``eval_rubrics.py`` (read) to form a read → edit → apply cycle:

    # 1. Dump current rubrics
    uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_rubrics.py \
        --agent <agent_id> --workspace <ws_id> --out rubrics.json

    # 2. Edit rubrics.json — change rubric text for specific (case, evaluator) pairs

    # 3. Apply
    uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/eval_rubrics_apply.py \
        --rubrics rubrics.json [--dry-run]

Input JSON must match the shape ``eval_rubrics.py`` outputs:

    {
      "agent_id": "...",
      "workspace_id": "...",
      "cases": [
        {
          "case_id": "...",
          "input": "...",
          "rubrics_by_evaluator": {
            "<evaluator_id>": "rubric text",
            ...
          }
        }
      ]
    }

Before writing, the script validates that the referenced case IDs belong to
the target agent and that evaluator IDs exist in the target workspace. Bad
UUIDs are reported per pair and skipped instead of failing the whole apply.

Only valid (case, evaluator) pairs whose rubric text differs from the current
value are written — unchanged pairs are skipped. Pass ``--force`` to write
all valid pairs regardless.

Writes a summary JSON to stdout: which pairs were updated, skipped, or
failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient  # noqa: E402
from codeer_cli import eval_ as eval_mod  # noqa: E402


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _truncate(s: str, n: int = 60) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rubrics", required=True, help="Path to rubrics JSON (same shape as eval_rubrics.py output)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    ap.add_argument("--force", action="store_true", help="Write all rubrics even if unchanged")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    payload = json.loads(Path(args.rubrics).read_text())
    cases = payload.get("cases") or []
    if not cases:
        _log("error: no cases in payload")
        return 2

    agent_id = payload.get("agent_id")
    workspace_id = payload.get("workspace_id")

    all_case_ids = [c["case_id"] for c in cases]
    all_evaluator_ids: set[str] = set()
    for c in cases:
        all_evaluator_ids.update((c.get("rubrics_by_evaluator") or {}).keys())

    with CodeerClient.from_env() as client:
        failed: list[dict] = []
        valid_case_ids = set(all_case_ids)
        valid_evaluator_ids = set(all_evaluator_ids)

        if agent_id:
            known_case_ids = {c["id"] for c in eval_mod.list_cases(client, agent_id)}
            invalid_case_ids = valid_case_ids - known_case_ids
            valid_case_ids &= known_case_ids
            if invalid_case_ids:
                _log(f"warning: {len(invalid_case_ids)} case IDs are not part of agent {agent_id}")

        resolved_workspace_id = workspace_id or client.workspace_id
        if resolved_workspace_id:
            known_evaluator_ids = {e["id"] for e in eval_mod.list_evaluators(client, resolved_workspace_id)}
            invalid_evaluator_ids = valid_evaluator_ids - known_evaluator_ids
            valid_evaluator_ids &= known_evaluator_ids
            if invalid_evaluator_ids:
                _log(f"warning: {len(invalid_evaluator_ids)} evaluator IDs are not part of workspace {resolved_workspace_id}")

        current: dict[str, dict[str, str]] = {}
        if not args.force:
            if not valid_case_ids or not valid_evaluator_ids:
                _log("reading current rubrics skipped: no valid case/evaluator pairs")
            else:
                _log(f"reading current rubrics for {len(valid_case_ids)} cases × {len(valid_evaluator_ids)} evaluators…")
                current = eval_mod.get_case_rubrics(
                    client,
                    agent_id=agent_id or "",
                    workspace_id=resolved_workspace_id or "",
                    evaluator_ids=list(valid_evaluator_ids),
                    case_ids=list(valid_case_ids),
                )

        updated: list[dict] = []
        skipped: list[dict] = []

        for case in cases:
            case_id = case["case_id"]
            case_input = _truncate(case.get("input", ""))
            rubrics = case.get("rubrics_by_evaluator") or {}

            for ev_id, new_rubric in rubrics.items():
                entry = {
                    "case_id": case_id,
                    "evaluator_id": ev_id,
                    "case_input": case_input,
                    "new_rubric_preview": _truncate(new_rubric, 80),
                }

                if case_id not in valid_case_ids:
                    failed.append({**entry, "error": "case_id not found for agent"})
                    continue
                if ev_id not in valid_evaluator_ids:
                    failed.append({**entry, "error": "evaluator_id not found for workspace"})
                    continue

                old_rubric = (current.get(case_id) or {}).get(ev_id, "")
                entry["old_rubric_preview"] = _truncate(old_rubric, 80)
                if not args.force and new_rubric == old_rubric:
                    skipped.append({"case_id": case_id, "evaluator_id": ev_id, "reason": "unchanged"})
                    continue

                if args.dry_run:
                    _log(f"  [dry-run] would update: {case_input} × {ev_id[:8]}…")
                    updated.append(entry)
                    continue

                try:
                    eval_mod.set_rubric(
                        client,
                        evaluation_case_id=case_id,
                        evaluator_id=ev_id,
                        rubric=new_rubric,
                    )
                    _log(f"  updated: {case_input} × {ev_id[:8]}…")
                    updated.append(entry)
                except Exception as e:
                    _log(f"  FAILED: {case_input} × {ev_id[:8]}… — {e}")
                    failed.append({**entry, "error": str(e)})

    _log(f"\ndone: {len(updated)} updated, {len(skipped)} skipped (unchanged), {len(failed)} failed")

    out = {"updated": updated, "skipped": skipped, "failed": failed}
    out_text = json.dumps(out, indent=2, ensure_ascii=False)
    print(out_text)
    if args.out:
        Path(args.out).write_text(out_text + "\n")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
