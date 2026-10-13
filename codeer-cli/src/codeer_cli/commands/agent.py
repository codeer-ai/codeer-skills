from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Optional

from .. import agents as agents_mod
from .._http_contracts import validate_http_input_contracts
from .._validate import validate_human_handoff, validate_suggested_questions, validate_unified_tools
from ..client import CodeerClient
from ._util import log, print_json, strip_noisy_fields, truncate, write_json


def register(subparsers):
    agent = subparsers.add_parser("agent", help="Agent CRUD and versioning")
    sub = agent.add_subparsers(dest="action", required=True)

    p = sub.add_parser("bind", help="Configure an isolated local deployment; creates no remote resources")
    p.add_argument("--alias", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--new", action="store_true")
    group.add_argument("--agent")
    p.set_defaults(func=run_bind)
    p = sub.add_parser("use", help="Select an existing local deployment (offline)")
    p.add_argument("alias")
    p.set_defaults(func=run_use_deployment, no_client=True)
    p = sub.add_parser("migrate", help="Explicitly migrate a legacy project, retaining originals (offline)")
    p.add_argument("--alias", required=True)
    p.set_defaults(func=run_migrate, no_client=True)
    p = sub.add_parser("adopt", help="Compare and explicitly adopt remote content or retain local proposals; no remote writes")
    p.add_argument("--resource", required=True, help="agent, case:<local-id>, tester:<local-id>, pairs:<local-id>")
    p.add_argument("--remote-id", help="Explicit ID for a previously unmapped resource")
    p.add_argument("--fields", help="Comma-separated fields; default all")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--remote", action="store_true")
    group.add_argument("--keep-local", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--expect")
    p.set_defaults(func=run_adopt)
    p = sub.add_parser("recover-rejected-create", help="Recover an evidenced legacy validation-rejected Agent create; no remote writes")
    p.add_argument("--evidence", required=True, help="Project-relative operator evidence bound to the original receipt SHA-256")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--expect")
    p.add_argument("--out")
    p.set_defaults(func=run_recover_rejected_create)
    p = sub.add_parser("attachment", help="Upload an original declared in resources.json")
    p.add_argument("--local-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--expect")
    p.add_argument("--reconcile", action="store_true")
    mapping = p.add_mutually_exclusive_group()
    mapping.add_argument("--remote-id", help="Take over this existing original after byte verification; no upload")
    mapping.add_argument("--new", action="store_true", help="Explicitly create a new attachment on an existing deployment")
    p.set_defaults(func=run_attachment)

    p = sub.add_parser("pull", help="Import Agent editable/Published snapshots without remote writes")
    p.add_argument("--agent", default=None)
    p.add_argument("--reconcile", action="store_true", help="After inspecting a receipt, accept observed remote as sync base; preserve local files")
    p.set_defaults(func=run_pull, requires_agent=True)

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
    p.add_argument("--history", default=None, help="Read this exact AgentHistory UUID instead of the editable agent.")
    p.add_argument("--full", action="store_true",
                   help="Print stripped full agent config, including system_prompt and tools.")
    p.add_argument("--out", default=None,
                   help="Write stripped full agent config to this file.")
    p.set_defaults(func=run_get)

    # codeer agent apply --payload agent.json
    p = sub.add_parser("apply", help="Create or update agent from JSON payload; run --dry-run first")
    p.add_argument("--payload", default=None, help="Path to agent payload JSON (project defaults to configured settings)")
    p.add_argument("--agent-id", default=None, help="If set, PATCH (update). Else POST (create).")
    p.add_argument("--note", default="", help="version_note for PATCH")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate payload and print intended mutation without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.add_argument("--expect", help="Project dry-run token for exactly the reviewed change")
    p.add_argument("--remove-tools", help="Comma-separated IDs explicitly removed from the complete tool list")
    p.set_defaults(func=run_apply)

    # codeer agent diff --from-version 41 --to-version 42
    p = sub.add_parser("diff", help="Diff system_prompt + tools between two versions")
    p.add_argument("--agent", default=None)
    p.add_argument("--local", action="store_true", help="Compare base/local/current remote for all managed settings")
    p.add_argument("--remove-tools", help="Explicit tool removal IDs included in local preview")
    p.add_argument("--from", dest="frm", default=None, help="From history_id")
    p.add_argument("--to", default=None, help="To history_id")
    p.add_argument("--from-version", type=int, default=None)
    p.add_argument("--to-version", type=int, default=None)
    p.add_argument("--field", choices=("system_prompt", "tools", "all"), default="all")
    p.set_defaults(func=run_diff, requires_agent=True)

    # codeer agent versions --agent <id>
    p = sub.add_parser(
        "versions",
        help="List version metadata; use agent get --history <id> for a stored snapshot.",
    )
    p.add_argument("--agent", default=None)
    p.add_argument("--full", action="store_true",
                   help="Add prompt/tool size metadata when included by the server.")
    p.add_argument("--out", default=None,
                   help="Write the full version listing (metadata, not snapshots); stdout stays compact.")
    p.set_defaults(func=run_versions, requires_agent=True)

    p = sub.add_parser("impact", help="Check downstream agents affected by this agent")
    p.add_argument("--agent", default=None)
    p.add_argument("--out", default=None, help="Write full impact detail to this file too")
    p.set_defaults(func=run_impact, requires_agent=True)

    p = sub.add_parser("publish", help="Publish an agent version; run --dry-run first")
    p.add_argument("--agent", default=None)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--history", default=None, help="AgentHistory UUID to publish")
    g.add_argument("--version", type=int, default=None, help="AgentHistory version_number to publish")
    p.add_argument("--dry-run", action="store_true",
                   help="Resolve target version and print intended mutation without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_publish, requires_agent=True)
    p.add_argument("--expect", help="Reviewed project publication evidence token")
    p.add_argument("--reconcile", action="store_true", help="Read back an interrupted publication without publishing again")


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
            "knowledge_node_count": len(agents_mod.referenced_knowledge_nodes([t])),
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
    if "version_number" in agent:
        row.update({key: agent.get(key) for key in ("agent_id", "version_number", "status")})
    if full:
        row["description"] = agent.get("description") or ""
        row["use_search"] = agent.get("use_search")
        row["suggested_questions"] = agent.get("suggested_questions") or []
        row["tools"] = _tool_summary(tools)
        row["human_handoff"] = human_handoff
        row["system_prompt_preview"] = truncate(agent.get("system_prompt") or "", 1200)
    return row



def run_bind(args, client):
    from ..deployment import configure
    if not args.project:
        raise ValueError("agent bind requires codeer init")
    print_json(configure(args.project, client, alias=args.alias, agent_id=args.agent, new=args.new))
    return 0


def run_recover_rejected_create(args, client):
    from ..deployment import rejected_create_plan, recover_rejected_create
    if not args.project or not args.project.portable:
        raise ValueError("Recovery requires a portable project/deployment")
    plan = rejected_create_plan(args.project, client, args.evidence)
    result = plan if args.dry_run else recover_rejected_create(args.project, client, plan, args.expect)
    print_json(result)
    write_json(args.out, result)
    return 0


def run_use_deployment(args, client):
    from ..deployment import use
    if not args.project:
        raise ValueError("agent use requires a project")
    print_json(use(args.project, args.alias))
    return 0


def run_migrate(args, client):
    from ..deployment import migrate
    if not args.project:
        raise ValueError("agent migrate requires a project")
    print_json(migrate(args.project, args.alias))
    return 0


def run_adopt(args, client):
    from ..deployment import adoption_plan, adopt
    if not args.project or not args.project.portable:
        raise ValueError("agent adopt requires a portable project/deployment")
    choice = "remote" if args.remote else "local" if args.keep_local else None
    plan = adoption_plan(args.project, client, args.resource, remote_id=args.remote_id,
                         fields=args.fields.split(",") if args.fields else None, choice=choice)
    print_json(plan if args.dry_run else adopt(args.project, client, plan, args.expect))
    return 0


def run_attachment(args, client):
    from ..project_attachments import upload
    if not args.project:
        raise ValueError("agent attachment requires a project")
    print_json(upload(args.project, client, args.local_id, dry_run=args.dry_run, expected=args.expect, reconcile=args.reconcile, remote_id=args.remote_id, new=args.new))
    return 0


def run_pull(args, client) -> int:
    from ..project_agent import pull
    if not getattr(args, "project", None):
        raise ValueError("agent pull requires codeer init")
    print_json(pull(args.project, client, args.agent, reconcile=args.reconcile))
    return 0


def run_list(args, client) -> int:
    ws, org = client.resolve_scope()
    result = agents_mod.list_all(client, workspace_id=ws, organization_id=org)
    write_json(args.out, strip_noisy_fields(result))
    print_json([_agent_summary(a, full=args.full) for a in result])
    return 0


def run_get(args, client) -> int:
    history_id = getattr(args, "history", None)
    result = (
        agents_mod.get_version(client, args.agent_id, history_id)
        if history_id else agents_mod.get(client, args.agent_id)
    )
    full_result = strip_noisy_fields(result)
    write_json(args.out, full_result)
    print_json(full_result if args.full else _agent_summary(result))
    return 0


def run_apply(args, client) -> int:
    project = getattr(args, "project", None)
    if project:
        from .. import project_agent
        if args.payload and Path(args.payload).resolve() != project.path("agent"):
            raise ValueError("Project apply uses the configured agent path; change [paths].agent to adopt another file")
        plan = project_agent.preview(project, client, remove_tools=(args.remove_tools or "").split(",") if args.remove_tools else [], note=args.note)
        result = plan if args.dry_run else project_agent.apply(project, client, plan, args.expect, args.note)
        print_json(result)
        write_json(args.out, result)
        return 1 if result.get("conflicts") or result.get("status") in ("readback_mismatch", "outcome_unknown") else 0
    if not args.payload:
        raise ValueError("--payload is required outside a project")
    body = json.loads(Path(args.payload).read_text())
    missing = [field for field in ("name", "system_prompt") if not body.get(field)]
    if missing:
        log(f"error: payload missing required field(s): {', '.join(missing)}")
        return 2

    try:
        validated_tools = validate_unified_tools(body.get("unified_tools") or [])
        validated_handoff = validate_human_handoff(body.get("human_handoff"))
        validate_suggested_questions(body.get("suggested_questions"))
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
            "http_inputs": [
                {
                    "tool_index": index,
                    "body_inputs_used": tool["http_request"]["method"] not in ("GET", "HEAD"),
                    "inputs": validate_http_input_contracts(tool["http_request"].get("body", {})),
                }
                for index, tool in enumerate(validated_tools)
                if tool.get("type") == "http_request"
            ],
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
        log(f"PATCH /agents/{agent_id} ok")
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
            if "system_prompt" in v:
                row["system_prompt_chars"] = len(v.get("system_prompt") or "")
            if "unified_tools" in v or "tools" in v:
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
    if getattr(args, "project", None):
        from ..evidence import publish
        result = publish(args.project, client, history_id, dry_run=args.dry_run, expected=args.expect, reconcile=args.reconcile)
        print_json(result)
        write_json(args.out, result)
        return 1 if result.get("status") in ("outcome_unknown", "readback_mismatch") else 0
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
                 "knowledge_node_ids", "knowledge_node_id", "domain", "agent_id",
                 "custom_form_schema", "http_request")
    safe = {k: t.get(k) for k in keep_keys if t.get(k) is not None}
    # HTTP placeholder keys depend on template insertion order. Sorting would
    # hide a reordering that changes which input receives a collision suffix.
    return json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=t.get("type") != "http_request")


def run_diff(args, client) -> int:
    if getattr(args, "local", False):
        from ..project_agent import preview
        if not getattr(args, "project", None):
            raise ValueError("--local requires a project")
        plan = preview(args.project, client, remove_tools=(args.remove_tools or "").split(",") if args.remove_tools else [])
        print_json(plan)
        return 1 if plan["conflicts"] else 0
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
