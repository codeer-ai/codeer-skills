from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path
from typing import Optional

from .. import agents as agents_mod
from ..client import CodeerClient
from ._util import log


def register(subparsers):
    agent = subparsers.add_parser("agent", help="Agent CRUD, versioning, publishing")
    sub = agent.add_subparsers(dest="action", required=True)

    # codeer agent list
    p = sub.add_parser("list", help="List agents in workspace")
    p.add_argument("--workspace", default=None)
    p.add_argument("--org", default=None)
    p.set_defaults(func=run_list)

    # codeer agent get <id>
    p = sub.add_parser("get", help="Read agent details")
    p.add_argument("agent_id")
    p.set_defaults(func=run_get)

    # codeer agent apply --payload agent.json
    p = sub.add_parser("apply", help="Create or update agent from JSON payload")
    p.add_argument("--payload", required=True, help="Path to agent payload JSON")
    p.add_argument("--agent-id", default=None, help="If set, PUT (update). Else POST (create).")
    p.add_argument("--note", default="", help="version_note for PUT")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_apply)

    # codeer agent diff --from-version 41 --to-version 42
    p = sub.add_parser("diff", help="Diff system_prompt + tools between two versions")
    p.add_argument("--agent", required=True)
    p.add_argument("--from", dest="frm", default=None, help="From history_id")
    p.add_argument("--to", default=None, help="To history_id")
    p.add_argument("--from-version", type=int, default=None)
    p.add_argument("--to-version", type=int, default=None)
    p.add_argument("--field", choices=("system_prompt", "tools", "all"), default="all")
    p.set_defaults(func=run_diff)

    # codeer agent versions --agent <id>
    p = sub.add_parser("versions", help="List version history for an agent")
    p.add_argument("--agent", required=True)
    p.set_defaults(func=run_versions)



def run_list(args, client) -> int:
    import os
    ws = args.workspace or client.workspace_id or os.environ.get("CODEER_WORKSPACE_ID")
    org = args.org or client.organization_id or os.environ.get("CODEER_ORGANIZATION_ID")
    if not ws:
        log("error: --workspace required (or set CODEER_WORKSPACE_ID)")
        return 2
    if org:
        result = agents_mod.list_all(client, workspace_id=ws, organization_id=org)
    else:
        result = agents_mod.list_in_workspace(client, ws)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def run_get(args, client) -> int:
    result = agents_mod.get(client, args.agent_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def run_apply(args, client) -> int:
    body = json.loads(Path(args.payload).read_text())

    if args.agent_id:
        body.pop("workspace_id", None)
        agents_mod.update(
            client, args.agent_id,
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
        log(f"PUT /agents/{agent_id} ok")
    else:
        if not body.get("workspace_id"):
            log("error: payload missing workspace_id (required for create)")
            return 2
        agent = agents_mod.create(
            client,
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
        log(f"POST /agents ok, id={agent_id}")

    histories = agents_mod.list_versions(client, agent_id)
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


def run_versions(args, client) -> int:
    versions = agents_mod.list_versions(client, args.agent)
    print(json.dumps(versions, ensure_ascii=False, indent=2, default=str))
    return 0



# --- diff helpers ---

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
    keep_keys = ("type", "name", "description", "invocation_instruction",
                 "knowledge_node_ids", "domain", "agent_id",
                 "custom_form_schema", "http_request")
    safe = {k: t.get(k) for k in keep_keys if t.get(k) is not None}
    return json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True)


def run_diff(args, client) -> int:
    snap_a = _resolve(client, args.agent, args.frm, args.from_version)
    snap_b = _resolve(client, args.agent, args.to, args.to_version)
    la, lb = _label(snap_a), _label(snap_b)

    if args.field in ("system_prompt", "all"):
        d = _diff_text(snap_a.get("system_prompt", ""), snap_b.get("system_prompt", ""),
                       f"{la} [system_prompt]", f"{lb} [system_prompt]")
        if d.strip():
            print(d)
        else:
            print(f"# system_prompt unchanged between {la} and {lb}")

    if args.field in ("tools", "all"):
        a_tools = snap_a.get("unified_tools") or []
        b_tools = snap_b.get("unified_tools") or []
        a_text = "\n".join(_summarize_tool(t) for t in a_tools) + "\n"
        b_text = "\n".join(_summarize_tool(t) for t in b_tools) + "\n"
        d = _diff_text(a_text, b_text, f"{la} [tools]", f"{lb} [tools]")
        if d.strip():
            print(d)
        else:
            print(f"# tools unchanged between {la} and {lb}")

    return 0
