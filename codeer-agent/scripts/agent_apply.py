"""Reusable: create or update a Codeer agent from a JSON payload.

Usage:
    # Create a new agent:
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/agent_apply.py \
        --payload ./agent_payload.json

    # Update an existing agent (PUT — auto-creates a new draft AgentHistory):
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/agent_apply.py \
        --payload ./agent_payload.json \
        --agent-id <id> \
        --note "tightened URL discipline"

JSON payload shape (matches POST /agents body — workspace_id only required for create):
    {
      "name": "...",
      "workspace_id": "<ws_id>",        # only required for --create (no --agent-id)
      "description": "...",
      "system_prompt": "...",
      "unified_tools": [...],
      "primary_object_ids": [],
      "attachment_ids": [],
      "use_search": false,
      "suggested_questions": [...],
      "llm_model": "litellm_proxy/azure/gpt-4.1"  # optional
    }

Writes JSON to stdout:
    {"agent_id": "...", "history_id": "...", "version_number": N, "status": "draft"}

The history_id is the draft snapshot — pin chat & eval runs to it via
agent_history_id.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient, agents  # noqa: E402


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True, help="Path to agent payload JSON")
    ap.add_argument("--agent-id", default=None, help="If set, PUT (update). Else POST (create).")
    ap.add_argument("--note", default="", help="version_note for PUT")
    ap.add_argument("--out", default=None, help="Write result JSON to this file too")
    args = ap.parse_args()

    body = json.loads(Path(args.payload).read_text())

    with CodeerClient.from_env() as c:
        if args.agent_id:
            body.pop("workspace_id", None)
            agent = agents.update(
                c, args.agent_id,
                name=body["name"],
                system_prompt=body["system_prompt"],
                unified_tools=body.get("unified_tools") or [],
                use_search=body.get("use_search", False),
                version_note=args.note,
                description=body.get("description"),
                llm_model=body.get("llm_model"),
                suggested_questions=body.get("suggested_questions") or [],
                primary_object_ids=body.get("primary_object_ids") or [],
                attachment_ids=body.get("attachment_ids") or [],
            )
            agent_id = args.agent_id
            _log(f"PUT /agents/{agent_id} ok")
        else:
            if not body.get("workspace_id"):
                _log("error: payload missing workspace_id (required for create)")
                return 2
            agent = agents.create(
                c,
                workspace_id=body["workspace_id"],
                name=body["name"],
                system_prompt=body["system_prompt"],
                unified_tools=body.get("unified_tools") or [],
                use_search=body.get("use_search", False),
                description=body.get("description"),
                llm_model=body.get("llm_model"),
                suggested_questions=body.get("suggested_questions") or [],
                primary_object_ids=body.get("primary_object_ids") or [],
                attachment_ids=body.get("attachment_ids") or [],
            )
            agent_id = agent["id"]
            _log(f"POST /agents ok, id={agent_id}")

        histories = agents.list_versions(c, agent_id)
        latest = max(histories, key=lambda h: h.get("version_number", 0))
        result = {
            "agent_id": agent_id,
            "history_id": latest["id"],
            "version_number": latest.get("version_number"),
            "status": latest.get("status"),
        }
        out_text = json.dumps(result, indent=2)
        print(out_text)
        if args.out:
            Path(args.out).write_text(out_text + "\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
