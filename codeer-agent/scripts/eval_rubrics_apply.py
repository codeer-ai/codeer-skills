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

Only (case, evaluator) pairs whose rubric text differs from the current
value are written — unchanged pairs are skipped. Pass ``--force`` to write
all pairs regardless.

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
        current: dict[str, dict[str, str]] = {}
        if not args.force:
            _log(f"reading current rubrics for {len(all_case_ids)} cases × {len(all_evaluator_ids)} evaluators…")
            current = eval_mod.get_case_rubrics(
                client,
                agent_id=agent_id or "",
                workspace_id=workspace_id or client.workspace_id or "",
                evaluator_ids=list(all_evaluator_ids) if all_evaluator_ids else None,
                case_ids=all_case_ids,
            )

        updated: list[dict] = []
        skipped: list[dict] = []
        failed: list[dict] = []

        for case in cases:
            case_id = case["case_id"]
            case_input = _truncate(case.get("input", ""))
            rubrics = case.get("rubrics_by_evaluator") or {}

            for ev_id, new_rubric in rubrics.items():
                old_rubric = (current.get(case_id) or {}).get(ev_id, "")
                if not args.force and new_rubric == old_rubric:
                    skipped.append({"case_id": case_id, "evaluator_id": ev_id, "reason": "unchanged"})
                    continue

                entry = {
                    "case_id": case_id,
                    "evaluator_id": ev_id,
                    "case_input": case_input,
                    "old_rubric_preview": _truncate(old_rubric, 80),
                    "new_rubric_preview": _truncate(new_rubric, 80),
                }

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
