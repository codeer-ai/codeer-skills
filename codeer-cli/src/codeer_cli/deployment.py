"""Explicit local deployment setup and resource adoption over existing APIs."""
from copy import deepcopy
import hashlib

from . import eval_ as api
from .project import ProjectError, fingerprint, now, read_json, save_json
from .portable import connection_fingerprint, logical_remote


def rejected_create_plan(project, client, evidence_path):
    """Explicit operator recovery for old receipts that lost a known 422.

    Limited to the reproduced question-limit and recorded KB-file rejections.
    An absence in Agent list alone never proves that a write was rejected.
    """
    scope = project.check_scope(client)
    entry = project.state().get("resources", {}).get("agent", {})
    if project.target.get("intent") != "create" or scope.get("agent_id") or entry.get("server_id"):
        raise ProjectError("Recovery requires an unbound Agent create with no known server identity")
    if entry.get("status") != "outcome_unknown" or not entry.get("receipt"):
        raise ProjectError("No legacy unknown Agent create to recover")
    receipt_path = project.resolve_path("receipt", entry["receipt"])
    if not receipt_path.is_relative_to((project.local_dir / "receipts").resolve()):
        raise ProjectError("Receipt must belong to the selected deployment")
    receipt = read_json(receipt_path)
    plan = receipt.get("plan", {})
    if (receipt.get("status") != "outcome_unknown" or receipt.get("error") != "CodeerError"
            or "response" in receipt or plan.get("resource") != "agent" or plan.get("server_id")):
        raise ProjectError("Receipt is not an unacknowledged legacy Agent create")
    if receipt.get("scope") != scope or plan.get("scope") != scope or entry.get("scope") != scope:
        raise ProjectError("Recovery scope differs from the saved receipt")
    path = project.resolve_path("evidence", evidence_path)
    if path.is_relative_to((project.root / ".codeer").resolve()):
        raise ProjectError("Operator evidence must be project content, outside machine state")
    evidence = read_json(path)
    receipt_hash = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    if (not isinstance(evidence, dict) or evidence.get("schema_version") != 1
            or evidence.get("receipt_sha256") != receipt_hash or evidence.get("scope") != scope
            or evidence.get("request_token") != plan.get("token")
            or evidence.get("operator_attested_validation_rejection") is not True):
        raise ProjectError("Require receipt-bound operator evidence, never a timeout or inferred failure")
    verification = evidence.get("verification")
    if not isinstance(verification, str) or not project.resolve_path("verification", verification).is_file():
        raise ProjectError("Recovery requires a local investigation report")
    questions = plan.get("payload", {}).get("suggested_questions")
    legacy_questions = (evidence.get("http_status") == 422 and evidence.get("message") == "Invalid request payload"
                        and isinstance(questions, list) and len(questions) > 3)
    kb_error = "Tool validation failed: One or more knowledge node files are not in the workspace"
    recorded = receipt.get("http_error", {})
    recorded_kb_rejection = (evidence.get("http_status") == recorded.get("status") == 400
                             and evidence.get("message") == recorded.get("message") == kb_error)
    if not (legacy_questions or recorded_kb_rejection):
        raise ProjectError("Recovery only supports the evidenced question-limit or recorded KB-file validation rejection")
    from ._validate import validate_suggested_questions
    validate_suggested_questions(read_json(project.path("agent"), {}).get("suggested_questions"))
    from . import agents
    ws, org = client.resolve_scope()
    rows = agents.list_all(client, workspace_id=ws, organization_id=org)
    if any(row.get("name") == plan.get("payload", {}).get("name") for row in rows):
        raise ProjectError("A same-name Agent exists; investigate its identity instead of clearing the create")
    result = {"resource": "agent", "scope": scope, "receipt": entry["receipt"],
              "receipt_sha256": receipt_hash, "evidence": str(path.relative_to(project.root)),
              "evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "entry_fingerprint": fingerprint(entry), "operator": project.preview_identity(client),
              "observed_agent_ids": sorted(str(row["id"]) for row in rows),
              "operation": "record_operator_verified_validation_rejection", "remote_mutations": 0}
    result["token"] = fingerprint(result)
    return result


def recover_rejected_create(project, client, plan, expected):
    current = rejected_create_plan(project, client, plan["evidence"])
    if expected != plan["token"] or current["token"] != expected:
        raise ProjectError("Recovery preview changed or missing --expect; investigate again")
    # Preserve the original receipt byte-for-byte; recovery is separate evidence.
    path = project.local_dir / "receipts" / f"recovery-{now().replace(':', '-')}.json"
    save_json(path, {"time": now(), "plan": plan, "status": "rejected", "remote_mutations": 0})
    state = project.state()
    state["resources"]["agent"].update(status="rejected", rejection_recovery=str(path.relative_to(project.root)))
    project.save_state(state)
    return {"status": "rejected", "resource": "agent", "recovery_receipt": str(path.relative_to(project.root)),
            "original_receipt_preserved": True, "remote_mutations": 0,
            "next_step": "Review a fresh Agent create preview; recovery does not retry the write"}


def configure(project, client, *, alias, agent_id=None, new=False):
    project.select(alias)
    if project.target or project.state_path.exists():
        raise ProjectError("Binding already exists; select it with --binding or agent use")
    ws, _ = client.resolve_scope()
    if getattr(client, "agent_id", None) and (new or client.agent_id != agent_id):
        raise ProjectError("CODEER_AGENT_ID conflicts with the explicit deployment; correct the override")
    agent_name = None
    if agent_id:
        from .project_agent import observe
        agent_name = observe(client, agent_id)[0].get("name")
    elif not new:
        raise ProjectError("Explicitly choose --new or --agent <id>")
    from .commands.check import _workspace_name
    workspace_name = _workspace_name(client.get_me().get("profile", {}), ws)
    project.bind(api_base=client.base_url.rstrip("/"), workspace_id=str(ws), workspace_name=workspace_name, agent_id=agent_id,
                 intent="create" if new else "takeover", created_at=now(), agent_name=agent_name)
    return {"binding": alias, "deployment": alias, "target": project.target, "remote_mutations": 0,
            "next_step": "Local binding prepared; no remote Agent exists yet. Upload dependencies then preview agent apply" if new else "Pull observations; explicitly map and adopt or keep each resource"}


def use(project, alias):
    project.select(alias)
    if not project.target:
        raise ProjectError("Unknown binding; configure it with agent bind <name>")
    path = project.root / ".codeer/deployment"
    path.write_text(alias + "\n", encoding="utf-8")
    return {"binding": alias, "deployment": alias, "remote_mutations": 0}


def list_bindings(project):
    from copy import copy
    rows = []
    for path in sorted((project.root / ".codeer/deployments").glob("*/target.json")):
        bound = copy(project).select(path.parent.name)
        target, state = bound.target, bound.state()
        agent = state.get("resources", {}).get("agent", {})
        pending = [key for key, value in state.get("resources", {}).items()
                   if value.get("status") in ("pending", "outcome_unknown", "readback_mismatch")]
        rows.append({"name": bound.deployment, "selected": bound.deployment == project.deployment,
                     "api_base": target["api_base"], "workspace_id": target["workspace_id"],
                     "workspace_name": target.get("workspace_name"), "agent_id": target.get("agent_id"),
                     "known_agent_id": agent.get("server_id"),
                     "agent_name": agent.get("observed", {}).get("name") or target.get("agent_name"),
                     "status": "bound" if target.get("agent_id") else "creation_unresolved" if agent.get("server_id") or "agent" in pending else "awaiting_create",
                     "unresolved_resources": pending,
                     "observed_at": state.get("queried_at")})
    return {"bindings": rows, "offline": True, "remote_mutations": 0}


def read_resource(project, client, key, remote_id=None):
    from .project_agent import local_settings, observe
    from .project_eval import CASE_FIELDS, TESTER_FIELDS, select
    state = project.state()
    entry = state.get("resources", {}).get(key, {})
    sid = entry.get("server_id")
    if sid and remote_id and sid != remote_id:
        raise ProjectError("Remote ID differs from the saved mapping")
    sid = sid or remote_id
    if key == "agent":
        sid = project.target.get("agent_id")
        if not sid or remote_id and remote_id != sid:
            raise ProjectError("Agent ID must match the explicitly configured deployment")
        return sid, local_settings(project), logical_remote(project, observe(client, sid)[1])
    kind, local_id = key.split(":", 1)
    if kind not in ("case", "tester", "pairs") or not sid:
        raise ProjectError("Specify --remote-id for a stable case/tester/pairs mapping; names are not matched")
    design = read_json(project.path("evals"), {})
    rows = design.get("testers" if kind == "tester" else "cases", [])
    matches = [r for r in rows if r.get("local_id") == local_id]
    if len(matches) != 1:
        raise ProjectError(f"Unknown or ambiguous local resource: {key}")
    row = matches[0]
    if sid == "new" and kind in ("case", "tester"):
        if entry.get("server_id"):
            raise ProjectError("Existing mapping cannot be redeclared new")
        return None, select(row, CASE_FIELDS if kind == "case" else TESTER_FIELDS), {}
    if any(other != key and other.startswith(kind + ":") and mapped.get("server_id") == sid for other, mapped in state.get("resources", {}).items()):
        raise ProjectError("Remote identity is already mapped to another local resource; resolve the ambiguity")
    if kind == "pairs" and state.get("resources", {}).get(f"case:{local_id}", {}).get("server_id") != sid:
        raise ProjectError("Map this exact Case before adopting its pairs; pair IDs cannot target a different Case")
    if kind in ("case", "pairs"):
        if sid not in {c["id"] for c in api.list_cases(client, project.target["agent_id"])}:
            if kind == "case" and entry.get("server_id") == sid:
                from .client import CodeerError
                try:
                    api.get_case(client, sid)
                except CodeerError as exc:
                    if exc.status == 404:
                        return sid, select(row, CASE_FIELDS), None
                    raise
            raise ProjectError("Case is absent from the selected Agent")
    if kind == "pairs":
        mapping = state.get("resources", {})
        local = {}
        for pair in row.get("pairs", []):
            tid = mapping.get(f"tester:{pair['tester']}", {}).get("server_id")
            if not tid:
                raise ProjectError("Map Testers before adopting pair assignments")
            local[tid] = pair["rubric"]
        remote = {e["evaluator_id"]: e.get("rubric", "") for item in api.get_case_evaluator_infos(client, case_ids=[sid]) for e in item.get("evaluators", [])}
    else:
        fields = CASE_FIELDS if kind == "case" else TESTER_FIELDS
        local = select(row, fields)
        remote = logical_remote(project, select(api.get_case(client, sid) if kind == "case" else api.get_evaluator(client, sid), fields))
    return sid, local, remote


def compare(entry, local, remote):
    result = {}
    for key in sorted(set(local) | set(remote)):
        # Omitted settings preserve remote; omission is not a deletion request.
        desired = local.get(key, remote.get(key))
        current = remote.get(key)
        lb, rb = entry.get("local_base", entry.get("base", {})), entry.get("base", {})
        decision = entry.get("decisions", {}).get(key, {})
        decided = decision.get("local") == fingerprint(desired) and decision.get("remote") == fingerprint(current)
        aligned = desired == current
        tracked = "base" in entry and "local_base" in entry
        local_only = tracked and current == rb.get(key) and desired != lb.get(key)
        result[key] = {"state": "aligned" if aligned else "pending_apply" if decided or local_only else "undecided",
                       "local": desired, "remote": current,
                       "local_changed": key not in lb or desired != lb.get(key),
                       "remote_changed": key not in rb or current != rb.get(key)}
    return result


def adoption_plan(project, client, key, *, remote_id=None, fields=None, choice=None):
    scope = project.check_scope(client)
    sid, local, remote = read_resource(project, client, key, remote_id)
    entry = project.state().get("resources", {}).get(key, {})
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch", "retired"):
        raise ProjectError("Resolve the recorded operation before adoption; adoption is not reconciliation")
    if entry.get("scope"):
        from .project import scope_matches
        # Create receipts retain an unbound scope after the deployment is bound.
        created_agent_bound = key == "agent" and entry.get("server_id") == sid == scope.get("agent_id") and bool(sid)
        if not scope_matches({k: v for k, v in entry["scope"].items() if k != "profile"}, scope, allow_unbound_agent=created_agent_bound):
            raise ProjectError("Resource mapping scope mismatch")
    comparison = compare(entry, local, remote) if remote is not None else {"$resource": {"state": "undecided", "local": local, "remote": None}}
    selected = fields or list(comparison)
    if any(f not in comparison for f in selected):
        raise ProjectError("Unknown adoption field")
    if choice not in (None, "remote", "local"):
        raise ProjectError("Choose remote or local")
    result = {"resource": key, "server_id": sid, "scope": scope, "local": local, "remote": remote,
              "requested_remote_id": remote_id,
              "fields": selected, "choice": choice, "comparison": comparison,
              "environment": connection_fingerprint(project)}
    result["operator"] = project.preview_identity(client)
    result["token"] = fingerprint(result)
    return result


def write_local(project, key, local):
    if key == "agent":
        settings = deepcopy(local)
        prompt = settings.pop("system_prompt", None)
        paths = [project.path("agent"), project.path("instructions")]
        previous = {p: p.read_bytes() if p.exists() else None for p in paths}
        try:
            save_json(paths[0], settings)
            if prompt is not None:
                paths[1].parent.mkdir(parents=True, exist_ok=True)
                paths[1].write_text(prompt, encoding="utf-8")
        except BaseException:
            for path, content in previous.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)
            raise
        return
    kind, local_id = key.split(":", 1)
    design = read_json(project.path("evals"))
    rows = design["testers" if kind == "tester" else "cases"]
    row = next(r for r in rows if r["local_id"] == local_id)
    if kind == "pairs":
        mapping = {v.get("server_id"): k.split(":", 1)[1] for k, v in project.state().get("resources", {}).items() if k.startswith("tester:")}
        if any(tid not in mapping for tid in local):
            raise ProjectError("Map newly observed Testers before adopting assignments")
        previous = {p["tester"]: p for p in row.get("pairs", [])}
        row["pairs"] = [{**previous.get(mapping[tid], {"required_evidence": []}), "tester": mapping[tid], "rubric": rubric} for tid, rubric in local.items()]
    else:
        from .project_eval import CASE_FIELDS, TESTER_FIELDS
        for field in TESTER_FIELDS if kind == "tester" else CASE_FIELDS:
            if field not in local:
                row.pop(field, None)
        row.update(local)
    save_json(project.path("evals"), design)


def adopt(project, client, plan, expected):
    current = adoption_plan(project, client, plan["resource"], remote_id=plan["requested_remote_id"], fields=plan["fields"], choice=plan["choice"])
    if expected != plan["token"] or current["token"] != expected or not plan["choice"]:
        raise ProjectError("Missing/stale --expect or adoption choice; compare again")
    local = deepcopy(plan["local"])
    if plan["remote"] is None:
        if plan["choice"] != "remote" or not plan["resource"].startswith("case:"):
            raise ProjectError("Deleted remote Case: explicitly adopt retirement, or retain the proposal and create a reviewed new local ID")
        local_id = plan["resource"].split(":", 1)[1]
        design = read_json(project.path("evals"))
        design["cases"] = [row for row in design["cases"] if row["local_id"] != local_id]
        save_json(project.path("evals"), design)
        state = project.state()
        from .project_eval import retire_deleted
        keys = [key for key in (plan["resource"], f"pairs:{local_id}") if key in state.get("resources", {})]
        retire_deleted(state["resources"], keys)
        save_json(project.local_dir / "imports" / f"retire-{now().replace(':', '-')}.json", plan)
        project.save_state(state)
        return {"resource": plan["resource"], "status": "retired", "remote_mutations": 0, "accepted_design": False}
    if plan["choice"] == "remote":
        if plan["server_id"] is None:
            raise ProjectError("A new resource has no remote content to adopt")
        for field in plan["fields"]:
            if field in plan["remote"]:
                local[field] = deepcopy(plan["remote"][field])
            else:
                local.pop(field, None)
        write_local(project, plan["resource"], local)
        # Read actual files; no baseline advances on a failed local update.
        _, actual, remote = read_resource(project, client, plan["resource"], plan["server_id"])
        if actual != local or remote != plan["remote"]:
            raise ProjectError("Content changed during adoption; files retained for comparison, bases unchanged")
    state = project.state()
    entry = state.setdefault("resources", {}).setdefault(plan["resource"], {})
    entry.update(server_id=plan["server_id"], scope=plan["scope"], status="tracked" if plan["server_id"] else "new", tracked_at=now(), tracking_version=1)
    for field in plan["fields"]:
        desired = local.get(field, plan["remote"].get(field))
        value = plan["remote"].get(field)
        if desired == value:
            entry.setdefault("base", {})[field] = deepcopy(value)
            entry.setdefault("local_base", {})[field] = deepcopy(desired)
            entry.setdefault("decisions", {}).pop(field, None)
        else:
            entry.setdefault("decisions", {})[field] = {"local": fingerprint(desired), "remote": fingerprint(value), "time": now()}
    entry["observed"] = plan["remote"]
    entry["alignment"] = compare(entry, local, plan["remote"])
    save_json(project.local_dir / "imports" / f"adopt-{now().replace(':', '-')}.json", plan)
    project.save_state(state)
    return {"resource": plan["resource"], "comparison": entry["alignment"], "remote_mutations": 0,
            "accepted_design": False}
