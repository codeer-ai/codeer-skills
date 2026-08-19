from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Optional

from .. import agents as agents_mod
from .._validate import validate_human_handoff, validate_unified_tools
from ..client import CodeerClient
from ._util import log, print_json, strip_noisy_fields, truncate, write_json


def register(subparsers):
    agent = subparsers.add_parser("agent", help="Agent CRUD and versioning")
    sub = agent.add_subparsers(dest="action", required=True)

    # codeer agent list
    p = sub.add_parser(
        "list",
        help="List agents in workspace. Defaults to a lifecycle summary safe for Codex/Claude context.",
    )
    p.add_argument("--full", action="store_true",
                   help="Print bounded detail instead of the default lifecycle summary.")
    p.add_argument("--out", default=None,
                   help="Write stripped full server detail to this file; stdout stays compact.")
    p.set_defaults(func=run_list)

    # codeer agent get <id>
    p = sub.add_parser(
        "get",
        help="Read one agent. Defaults to summary; use --full for prompt/tool detail or --out for an artifact.",
    )
    p.add_argument("agent_id")
    p.add_argument("--full", action="store_true",
                   help="Print stripped full agent config, including system_prompt and tools.")
    p.add_argument("--out", default=None,
                   help="Write stripped full agent config to this file.")
    p.set_defaults(func=run_get)

    # codeer agent apply --payload agent.json
    p = sub.add_parser("apply", help="Create or update agent from JSON payload; run --dry-run first")
    p.add_argument("--payload", required=True, help="Path to agent payload JSON")
    p.add_argument("--agent-id", default=None, help="If set, PUT (update). Else POST (create).")
    p.add_argument("--note", default="", help="version_note for PUT")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate payload and print intended mutation without writing server state.")
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
    p = sub.add_parser(
        "versions",
        help="List version history. Defaults to version metadata only; use --out for full snapshots.",
    )
    p.add_argument("--agent", required=True)
    p.add_argument("--full", action="store_true",
                   help="Add bounded prompt/tool size metadata; full snapshots still require --out.")
    p.add_argument("--out", default=None,
                   help="Write stripped full version snapshots to this file; stdout stays compact.")
    p.set_defaults(func=run_versions)

    p = sub.add_parser("impact", help="Check downstream agents affected by this agent")
    p.add_argument("--agent", required=True)
    p.add_argument("--out", default=None, help="Write full impact detail to this file too")
    p.set_defaults(func=run_impact)

    p = sub.add_parser("publish", help="Publish an agent version; run --dry-run first")
    p.add_argument("--agent", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--history", default=None, help="AgentHistory UUID to publish")
    g.add_argument("--version", type=int, default=None, help="AgentHistory version_number to publish")
    p.add_argument("--dry-run", action="store_true",
                   help="Resolve target version and print intended mutation without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_publish)


def _tool_summary(tools: list[dict] | None) -> list[dict]:
    out = []
    for t in tools or []:
        form = t.get("custom_form_schema")
        if not isinstance(form, dict):
            form = {}
        out.append({
            "id": t.get("id"),
            "type": t.get("type"),
            "name": t.get("name"),
            "knowledge_node_count": len(t.get("knowledge_node_ids") or []),
            "form_title": form.get("title"),
            "invocation_preview": truncate(t.get("invocation_instruction") or "", 160),
        })
    return out


def _agent_summary(agent: dict, *, full: bool = False) -> dict:
    tools = agent.get("unified_tools") or agent.get("tools") or []
    human_handoff = agent.get("human_handoff")
    if not isinstance(human_handoff, dict):
        meta = agent.get("meta")
        human_handoff = meta.get("human_handoff") if isinstance(meta, dict) else {}
    if not isinstance(human_handoff, dict):
        human_handoff = {}
    row = {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "workspace": {
            "id": agent.get("workspace_id") or (agent.get("workspace") or {}).get("id"),
            "name": (agent.get("workspace") or {}).get("name"),
        },
        "publish_state": agent.get("publish_state"),
        "version": agent.get("version"),
        "latest_version_number": agent.get("latest_version_number"),
        "published_version_number": agent.get("published_version_number"),
        "publish_history_id": agent.get("publish_history_id"),
        "llm_model": agent.get("llm_model"),
        "agent_type": agent.get("agent_type"),
        "updated_at": agent.get("updated_at"),
        "tool_count": len(tools),
        "human_handoff_enabled": bool(human_handoff.get("enabled")),
        "system_prompt_chars": len(agent.get("system_prompt") or ""),
    }
    if full:
        row["description"] = agent.get("description") or ""
        row["use_search"] = agent.get("use_search")
        row["suggested_questions"] = agent.get("suggested_questions") or []
        row["tools"] = _tool_summary(tools)
        row["human_handoff"] = human_handoff
        row["system_prompt_preview"] = truncate(agent.get("system_prompt") or "", 1200)
    return row



def run_list(args, client) -> int:
    ws, org = client.resolve_scope()
    result = agents_mod.list_all(client, workspace_id=ws, organization_id=org)
    write_json(args.out, strip_noisy_fields(result))
    print_json([_agent_summary(a, full=args.full) for a in result])
    return 0


def run_get(args, client) -> int:
    result = agents_mod.get(client, args.agent_id)
    full_result = strip_noisy_fields(result)
    write_json(args.out, full_result)
    print_json(full_result if args.full else _agent_summary(result))
    return 0


def run_apply(args, client) -> int:
    body = json.loads(Path(args.payload).read_text())
    missing = [field for field in ("name", "system_prompt") if not body.get(field)]
    if missing:
        log(f"error: payload missing required field(s): {', '.join(missing)}")
        return 2

    try:
        validated_tools = validate_unified_tools(body.get("unified_tools") or [])
        validated_handoff = validate_human_handoff(body.get("human_handoff"))
    except ValueError as exc:
        log(f"error: invalid agent payload: {exc}")
        return 2

    llm_model_settings_provided = "llm_model_settings" in body

    if args.dry_run:
        operation = "update" if args.agent_id else "create"
        result = {
            "dry_run": True,
            "operation": operation,
            "agent_id": args.agent_id,
            "payload": str(Path(args.payload)),
            "name": body.get("name"),
            "system_prompt_chars": len(body.get("system_prompt") or ""),
            "tool_count": len(validated_tools),
            "use_search": body.get("use_search", False),
            "llm_model": body.get("llm_model"),
            "llm_model_settings_provided": llm_model_settings_provided,
            "llm_model_settings": body.get("llm_model_settings"),
            "human_handoff": {
                "enabled": bool((validated_handoff or {}).get("enabled")),
                "idle_timeout_minutes": (validated_handoff or {}).get("idle_timeout_minutes"),
                "instructions_chars": len((validated_handoff or {}).get("handoff_instructions") or ""),
            },
            "version_note": args.note if args.agent_id else None,
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(result)
        return 0

    model_settings_kwargs = (
        {"llm_model_settings": body["llm_model_settings"]}
        if llm_model_settings_provided
        else {}
    )

    if args.agent_id:
        body.pop("workspace_id", None)
        agents_mod.update(
            client, args.agent_id,
            name=body["name"],
            system_prompt=body["system_prompt"],
            unified_tools=validated_tools,
            use_search=body.get("use_search", False),
            version_note=args.note,
            description=body.get("description"),
            llm_model=body.get("llm_model"),
            suggested_questions=body.get("suggested_questions") or [],
            primary_object_ids=body.get("primary_object_ids") or [],
            attachment_ids=body.get("attachment_ids") or [],
            human_handoff=validated_handoff,
            **model_settings_kwargs,
        )
        agent_id = args.agent_id
        log(f"PUT /agents/{agent_id} ok")
    else:
        if not body.get("workspace_id"):
            body["workspace_id"] = client.resolve_scope()[0]
        agent = agents_mod.create(
            client,
            workspace_id=body["workspace_id"],
            name=body["name"],
            system_prompt=body["system_prompt"],
            unified_tools=validated_tools,
            use_search=body.get("use_search", False),
            description=body.get("description"),
            llm_model=body.get("llm_model"),
            suggested_questions=body.get("suggested_questions") or [],
            primary_object_ids=body.get("primary_object_ids") or [],
            attachment_ids=body.get("attachment_ids") or [],
            human_handoff=validated_handoff,
            **model_settings_kwargs,
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
    write_json(args.out, strip_noisy_fields(versions))
    rows = []
    for v in versions:
        row = {
            "id": v.get("id"),
            "version_number": v.get("version_number"),
            "status": v.get("status"),
            "was_published": v.get("was_published"),
            "version_note": v.get("version_note") or "",
            "created_at": v.get("created_at"),
        }
        if args.full:
            row["system_prompt_chars"] = len(v.get("system_prompt") or "")
            row["tool_count"] = len(v.get("unified_tools") or v.get("tools") or [])
        rows.append(row)
    print_json(rows)
    return 0


def run_impact(args, client) -> int:
    result = strip_noisy_fields(agents_mod.check_impact(client, args.agent))
    write_json(args.out, result)
    print_json(result)
    return 0


def _resolve_history_for_publish(
    client: CodeerClient,
    agent_id: str,
    history_id: Optional[str],
    version: Optional[int],
) -> dict:
    if history_id:
        return agents_mod.get_version(client, agent_id, history_id)
    if version is not None:
        for candidate in agents_mod.list_versions(client, agent_id):
            if candidate.get("version_number") == version:
                return agents_mod.get_version(client, agent_id, candidate["id"])
        raise SystemExit(f"no version {version} on agent {agent_id}")
    raise SystemExit("must pass --history or --version")


def run_publish(args, client) -> int:
    history = _resolve_history_for_publish(client, args.agent, args.history, args.version)
    history_id = history["id"]
    summary = {
        "agent_id": args.agent,
        "history_id": history_id,
        "version_number": history.get("version_number"),
        "status": history.get("status"),
        "was_published": history.get("was_published"),
        "version_note": history.get("version_note") or "",
    }

    if args.dry_run:
        result = {
            "dry_run": True,
            "operation": "agent_publish",
            "method": "POST",
            "path": f"/external/agents/{args.agent}/versions/{history_id}:publish",
            "target": summary,
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        print_json(result)
        write_json(args.out, result)
        return 0

    result = strip_noisy_fields(agents_mod.publish_version(client, args.agent, history_id))
    output = {"target": summary, "response": result}
    print_json(output)
    write_json(args.out, output)
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
