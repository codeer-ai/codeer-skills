"""Print per-(case, evaluator) rubrics for an agent.

Reads rubrics directly via ``POST /eval/rubrics/batch`` — this is the same
field ``set_rubric`` writes to (``CaseEvaluatorInfo.rubric``), so what you
see is exactly what the judge sees. Use this when reviewing what an agent's
eval suite is currently checking, or when designing new cases against the
same evaluators.

Usage:
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/eval_rubrics.py \
        --agent <agent_id> --workspace <ws_id> \
        [--evaluators <id,id>]   # default: all evaluators in workspace
        [--cases <id,id>]        # default: all cases for this agent
        [--out rubrics.json]

Stderr gets a human-readable per-case table; stdout gets structured JSON.
A case+evaluator with empty rubric is shown as "(rubric not set)".
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


def _truncate(s: str, n: int = 120) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--evaluators", default=None,
                    help="Comma-separated evaluator UUIDs (default: all in workspace)")
    ap.add_argument("--cases", default=None,
                    help="Comma-separated case UUIDs (default: all for this agent)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with CodeerClient.from_env() as c:
        cases = eval_mod.list_cases(c, args.agent)
        if args.cases:
            wanted = {s.strip() for s in args.cases.split(",") if s.strip()}
            cases = [x for x in cases if x["id"] in wanted]
        case_ids = [x["id"] for x in cases]
        case_input = {x["id"]: (x.get("input") or "") for x in cases}
        if not case_ids:
            _log("error: no cases for this agent")
            return 2

        if args.evaluators:
            evaluator_ids = [s.strip() for s in args.evaluators.split(",") if s.strip()]
            evaluators = [eval_mod.get_evaluator(c, eid) for eid in evaluator_ids]
        else:
            evaluators = eval_mod.list_evaluators(c, args.workspace)
            evaluator_ids = [e["id"] for e in evaluators]
        evaluator_name = {e["id"]: e.get("name", e["id"]) for e in evaluators}
        if not evaluator_ids:
            _log("error: no evaluators in workspace")
            return 2

        _log(f"reading {len(case_ids)} cases × {len(evaluator_ids)} evaluators…")

        rubrics = eval_mod.get_case_rubrics(
            c, agent_id=args.agent, workspace_id=args.workspace,
            evaluator_ids=evaluator_ids, case_ids=case_ids,
        )

        for cid in case_ids:
            _log("=" * 80)
            _log(f"CASE {cid}")
            _log(f"  input: {_truncate(case_input.get(cid, ''))}")
            for ev_id in evaluator_ids:
                ev_name = evaluator_name.get(ev_id, ev_id)
                rubric_text = (rubrics.get(cid) or {}).get(ev_id, "")
                if not rubric_text:
                    _log(f"  [{ev_name}] (rubric not set)")
                else:
                    _log(f"  [{ev_name}]")
                    for line in rubric_text.splitlines():
                        _log(f"    {line}")

        out = {
            "agent_id": args.agent,
            "workspace_id": args.workspace,
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


if __name__ == "__main__":
    raise SystemExit(main())
