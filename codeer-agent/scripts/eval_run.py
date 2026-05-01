"""Reusable: trigger an eval run pinned to an agent history, then read scores.

Usage:
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/eval_run.py \
        --agent <agent_id> \
        ( --history <history_id> | --latest-draft ) \
        --workspace <ws_id> \
        [--cases <id,id,...>] \
        [--evaluators <id,id>] \
        [--diff-vs <prev_history_id>] \
        [--poll-timeout 600] \
        [--out eval_results.json]

If --cases is omitted, runs every case for the agent.
If --evaluators is omitted, runs every evaluator in the workspace.
--latest-draft auto-selects the newest unpublished AgentHistory (the version
your last `agent_apply.py` PUT just created). Use it in iteration loops so you
don't have to look up the new history id each time.
--diff-vs prints a regression report: every case that scored ≥1.0 on the
previous history but <1.0 now, plus every case that improved. Catches the
"fixed N1 but accidentally regressed Case 4" class of failure that's invisible
when only re-running the case you targeted.

Polls until each (case, evaluator) result row has a non-null score, then
prints a summary table to stderr and a structured JSON to stdout (and --out).

Exit code: 0 if every score == 1.0; 1 otherwise. Use this in a script to gate
publish on perfect scores.

Output shape:
    {
      "agent_id": "...",
      "history_id": "...",
      "all_perfect": false,
      "results": [
        {
          "case_id": "...",
          "case_label": "...",   # input prefix, for human reading
          "evaluator_id": "...",
          "evaluator_name": "...",
          "score": 0.3,
          "reason": "violated negative constraint X — ...",
          "output": "<assistant text>"
        },
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient  # noqa: E402
from codeer_cli import agents as agents_mod  # noqa: E402
from codeer_cli import eval_ as eval_mod  # noqa: E402
from codeer_cli.parse import parse_eval_result, parse_eval_tool_calls, summarize_eval_tool_calls  # noqa: E402

POLL_INTERVAL = 5


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _truncate(s: str, n: int = 60) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[: n - 1] + "…" if len(s) > n else s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--history", default=None, help="History UUID to pin the run to")
    g.add_argument("--latest-draft", action="store_true",
                   help="Auto-select the newest unpublished AgentHistory")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--cases", default=None, help="Comma-separated case UUIDs (default: all for this agent)")
    ap.add_argument("--evaluators", default=None, help="Comma-separated evaluator UUIDs (default: all in workspace)")
    ap.add_argument("--diff-vs", default=None, dest="diff_vs",
                    help="Compare scores against this prior history_id; print regressions + improvements")
    ap.add_argument("--poll-timeout", type=int, default=900)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with CodeerClient.from_env() as c:
        if args.latest_draft:
            history_id = agents_mod.get_latest_draft_history_id(c, args.agent)
            if not history_id:
                _log("error: --latest-draft set but agent has no draft versions; pass --history instead")
                return 2
            _log(f"--latest-draft → {history_id}")
            args.history = history_id
        if args.cases:
            case_ids = [s.strip() for s in args.cases.split(",") if s.strip()]
            case_objs = []
            for cid in case_ids:
                try:
                    case_objs.append(eval_mod.get_case(c, cid))
                except Exception as e:
                    _log(f"warning: could not fetch case {cid}: {e}")
                    case_objs.append({"id": cid, "input": ""})
        else:
            case_objs = eval_mod.list_cases(c, args.agent)
            case_ids = [c_["id"] for c_ in case_objs]
        if not case_ids:
            _log("error: no cases to run")
            return 2

        if args.evaluators:
            evaluator_ids = [s.strip() for s in args.evaluators.split(",") if s.strip()]
            evaluators = [eval_mod.get_evaluator(c, eid) for eid in evaluator_ids]
        else:
            evaluators = eval_mod.list_evaluators(c, args.workspace)
            evaluator_ids = [e["id"] for e in evaluators]
        if not evaluator_ids:
            _log("error: no evaluators in workspace")
            return 2

        case_label_by_id = {c_["id"]: _truncate(c_.get("input", ""), 60) for c_ in case_objs}
        evaluator_name_by_id = {e["id"]: e.get("name", e["id"]) for e in evaluators}

        _log(f"triggering: {len(case_ids)} cases × {len(evaluator_ids)} evaluators on history {args.history}")
        eval_mod.trigger(
            c, case_ids=case_ids, evaluator_ids=evaluator_ids,
            agent_history_id=args.history,
        )

        deadline = time.time() + args.poll_timeout
        results_by_eval: dict[str, list[dict]] = {}
        while time.time() < deadline:
            results_by_eval = {}
            done = 0
            total = len(case_ids) * len(evaluator_ids)
            for ev_id in evaluator_ids:
                rows = eval_mod.get_results(
                    c, case_ids=case_ids, evaluator_id=ev_id,
                    agent_history_id=args.history, workspace_id=args.workspace,
                    include_output=True,
                    include_reasoning_steps=True,
                )
                results_by_eval[ev_id] = rows
                done += sum(1 for r in rows if r.get("score") is not None)
            _log(f"  progress: {done}/{total}")
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
                    "case_label": case_label_by_id.get(r.get("case_id") or r.get("evaluation_case_id"), "?"),
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

        _log("\n" + "=" * 80)
        _log(f"RESULTS  agent={args.agent}  history={args.history}")
        _log("=" * 80)
        _log(f"{'score':>6}  {'evaluator':<35}  case")
        for r in sorted(flat, key=lambda x: (x.get("score") or 0.0, x["evaluator_name"])):
            score = r.get("score")
            score_str = f"{score:.2f}" if score is not None else "  - "
            _log(f"{score_str:>6}  {r['evaluator_name'][:35]:<35}  {r['case_label']}")

        non_perfect = [r for r in flat if (r.get("score") or 0.0) < 1.0]
        if non_perfect:
            _log("\nNON-PERFECT RESULTS — analysis:\n")
            for r in non_perfect:
                _log(f"  [{r.get('score') or 0:.2f}] {r['evaluator_name']} — {r['case_label']}")
                if r.get("tool_calls_summary"):
                    _log(f"     tools: {r['tool_calls_summary'][:600]}")
                _log(f"     reason: {(r.get('reason') or '').strip()[:600]}")
                _log("")

        diff_summary: dict[str, list[dict]] = {"regressions": [], "improvements": [], "stable": []}
        if args.diff_vs:
            _log(f"\n{'=' * 80}\nREGRESSION CHECK vs history {args.diff_vs}\n{'=' * 80}")
            prev_by_key: dict[tuple[str, str], float] = {}
            for ev_id in evaluator_ids:
                try:
                    prev_rows = eval_mod.get_results(
                        c, case_ids=case_ids, evaluator_id=ev_id,
                        agent_history_id=args.diff_vs, workspace_id=args.workspace,
                        include_output=False,
                        include_reasoning_steps=False,
                    )
                except Exception as e:
                    _log(f"  warning: prev fetch failed for evaluator {ev_id[:8]}: {e}")
                    continue
                for r in prev_rows:
                    cid = r.get("evaluation_case_id") or r.get("case_id")
                    if r.get("score") is not None:
                        prev_by_key[(cid, ev_id)] = r["score"]
            for r in flat:
                key = (r["case_id"], r["evaluator_id"])
                prev = prev_by_key.get(key)
                cur = r.get("score")
                if prev is None or cur is None:
                    continue
                delta = round(cur - prev, 2)
                row = {**r, "prev_score": prev, "delta": delta}
                if delta < 0:
                    diff_summary["regressions"].append(row)
                elif delta > 0:
                    diff_summary["improvements"].append(row)
                else:
                    diff_summary["stable"].append(row)
            for label in ("regressions", "improvements"):
                rows = diff_summary[label]
                if not rows:
                    _log(f"  ({label}: none)")
                    continue
                _log(f"\n  {label.upper()}:")
                for r in sorted(rows, key=lambda x: x.get("delta") or 0):
                    _log(f"    {r['prev_score']:.2f} → {r['score']:.2f}  ({r.get('delta'):+0.2f})  "
                         f"{r['evaluator_name'][:25]} — {r['case_label']}")

        out = {
            "agent_id": args.agent,
            "history_id": args.history,
            "all_perfect": all_perfect,
            "results": flat,
            "diff_vs": args.diff_vs,
            "regressions": diff_summary["regressions"] if args.diff_vs else None,
            "improvements": diff_summary["improvements"] if args.diff_vs else None,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        if args.out:
            Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        return 0 if all_perfect else 1


if __name__ == "__main__":
    raise SystemExit(main())
