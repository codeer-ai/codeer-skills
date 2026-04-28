"""Show what changed between two AgentHistory versions.

Usage:
    uv run --with 'httpx>=0.27' python $SKILL_DIR/scripts/agent_diff.py \
        --agent <agent_id> \
        --from <history_id_a> \
        --to <history_id_b> \
        [--field system_prompt|tools|all]   # default: all

Or, with versions referenced by number ("the v40 → v42 diff"):
    ... --from-version 40 --to-version 42

Prints a unified diff to stdout. Useful for explaining "what did v41 change?"
without manually dumping prompts to /tmp and shelling out to ``diff``.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient  # noqa: E402
from codeer_cli import agents as agents_mod  # noqa: E402


def _resolve(c: CodeerClient, agent_id: str, hid: Optional[str], version: Optional[int]) -> dict:
    if hid:
        return agents_mod.get_version(c, agent_id, hid)
    if version is not None:
        for v in agents_mod.list_versions(c, agent_id):
            if v.get("version_number") == version:
                return agents_mod.get_version(c, agent_id, v["id"])
        raise SystemExit(f"no version {version} on agent {agent_id}")
    raise SystemExit("must pass --from/--to (history id) or --from-version/--to-version")


def _label(snap: dict) -> str:
    vn = snap.get("version_number")
    note = (snap.get("version_note") or "").strip().replace("\n", " ")
    pub = " (published)" if snap.get("status") == "published" else ""
    return f"v{vn}{pub}: {note[:60]}"


def _diff_text(a: str, b: str, label_a: str, label_b: str) -> str:
    return "".join(difflib.unified_diff(
        (a or "").splitlines(keepends=True),
        (b or "").splitlines(keepends=True),
        fromfile=label_a, tofile=label_b,
    ))


def _summarize_tool(t: dict) -> str:
    """Stable, hashable text representation for one tool — for diffing."""
    keep_keys = ("type", "name", "description", "invocation_instruction",
                 "knowledge_node_ids", "domain", "agent_id",
                 "custom_form_schema", "http_request")
    safe = {k: t.get(k) for k in keep_keys if t.get(k) is not None}
    return json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True)


def _diff_tools(snap_a: dict, snap_b: dict, label_a: str, label_b: str) -> str:
    a_tools = snap_a.get("unified_tools") or []
    b_tools = snap_b.get("unified_tools") or []
    a_text = "\n".join(_summarize_tool(t) for t in a_tools) + "\n"
    b_text = "\n".join(_summarize_tool(t) for t in b_tools) + "\n"
    return _diff_text(a_text, b_text, f"{label_a} [tools]", f"{label_b} [tools]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--from", dest="frm", default=None, help="From history_id")
    ap.add_argument("--to", default=None, help="To history_id")
    ap.add_argument("--from-version", type=int, default=None)
    ap.add_argument("--to-version", type=int, default=None)
    ap.add_argument("--field", choices=("system_prompt", "tools", "all"), default="all")
    args = ap.parse_args()

    with CodeerClient.from_env() as c:
        snap_a = _resolve(c, args.agent, args.frm, args.from_version)
        snap_b = _resolve(c, args.agent, args.to, args.to_version)
        la, lb = _label(snap_a), _label(snap_b)

        if args.field in ("system_prompt", "all"):
            d = _diff_text(snap_a.get("system_prompt", ""), snap_b.get("system_prompt", ""),
                           f"{la} [system_prompt]", f"{lb} [system_prompt]")
            if d.strip():
                print(d)
            else:
                print(f"# system_prompt unchanged between {la} and {lb}")

        if args.field in ("tools", "all"):
            d = _diff_tools(snap_a, snap_b, la, lb)
            if d.strip():
                print(d)
            else:
                print(f"# tools unchanged between {la} and {lb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
