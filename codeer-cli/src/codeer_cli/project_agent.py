"""Agent-specific project import and sync over existing external APIs."""
from . import agents
from ._validate import validate_human_handoff, validate_suggested_questions, validate_unified_tools
from .project import ProjectError, fingerprint, now, read_json, save_json, scope_matches
from copy import deepcopy

from .sync import apply_change, plan_change, reconcile_entry


FIELDS = ("name", "system_prompt", "unified_tools", "primary_object_ids", "attachment_ids",
          "use_search", "suggested_questions", "description", "llm_model", "llm_model_settings", "human_handoff",
          "response_mode", "output_presentation_policy")


def writable(snapshot):
    result = {k: snapshot[k] for k in FIELDS if k in snapshot}
    meta = snapshot.get("meta") or {}
    for key in ("human_handoff", "response_mode", "output_presentation_policy"):
        if key not in result and key in meta:
            result[key] = meta[key]
    if "attachment_ids" not in result and isinstance(snapshot.get("attachments"), list):
        result["attachment_ids"] = [a["id"] for a in snapshot["attachments"]]
    if "primary_object_ids" not in result and "version_number" in snapshot:
        result["primary_object_ids"] = [p["id"] for p in meta.get("primary_objects_info", [])]
    return canonical(result)


def canonical(settings):
    """Expand only documented schema defaults; arbitrary tool templates retain order/nulls."""
    result = deepcopy(settings)
    if isinstance(result.get("human_handoff"), dict):
        result["human_handoff"] = validate_human_handoff(result["human_handoff"])
    if isinstance(result.get("output_presentation_policy"), dict):
        result["output_presentation_policy"] = {"enable_output_presentations": False, "allowed_presentation_kinds": [], "max_items_by_kind": {}, "when_to_use_by_kind": {}, **result["output_presentation_policy"]}
    if isinstance(result.get("llm_model_settings"), dict):
        result["llm_model_settings"] = {model: {k: v for k, v in values.items() if v is not None} for model, values in result["llm_model_settings"].items()}
    if "unified_tools" in result:
        tools = []
        for original in result["unified_tools"] or []:
            tool = {k: None for k in ("name", "description", "version", "domain", "invocation_instruction", "draft_policy", "agent_id", "knowledge_node_ids", "knowledge_node_id", "image_model", "custom_form_schema", "http_request", "text2speech")}
            tool.update(original)
            if isinstance(tool["http_request"], dict):
                config = {"headers": None, "query_params": None, **tool["http_request"]}
                config["auth"] = {"type": "none", **{k: None for k in ("token", "api_key", "api_key_location", "api_key_param_name", "username", "password", "header_name", "header_value")}, **config.get("auth", {})}
                body = {"template": None, "input_contracts": {}, **config.get("body", {})}
                body["input_contracts"] = {k: {"type": "string", "format": "text", "json_type": "any", **v} for k, v in body["input_contracts"].items()}
                config["body"] = body
                tool["http_request"] = config
            if isinstance(tool["text2speech"], dict):
                tool["text2speech"] = {"provider": "elevenlabs", "model_id": "eleven_multilingual_v2", "language_code": None, "output_format": "mp3_44100_128", **tool["text2speech"]}
            tools.append(tool)
        result["unified_tools"] = tools
    return result


def observe(client, agent_id):
    """Editable API omits attachment IDs; recover from its exact latest history."""
    editable = agents.get(client, agent_id)
    result = writable(editable)
    if "attachment_ids" not in result or "primary_object_ids" not in result:
        versions = agents.list_versions(client, agent_id)
        if not versions:
            raise ProjectError("No history available to preserve existing attachments")
        latest = max(versions, key=lambda h: h.get("version_number", 0))
        history = agents.get_version(client, agent_id, latest["id"])
        historical = writable(history)
        for key in set(result) & set(historical):
            if result[key] != historical[key]:
                raise ProjectError("Editable Agent differs from latest history; cannot safely infer attachment/settings base")
        for key in ("attachment_ids", "primary_object_ids"):
            if key not in historical:
                raise ProjectError(f"Cannot preserve missing {key}; inspect exact version evidence")
            result.setdefault(key, historical[key])
    return editable, result


def local_settings(project):
    settings = read_json(project.path("agent"))
    if not isinstance(settings, dict):
        raise ProjectError("Agent settings file must contain an object")
    if any(k not in FIELDS for k in settings):
        raise ProjectError(f"Read-only or unknown Agent fields: {sorted(set(settings) - set(FIELDS))}")
    if "suggested_questions" in settings:
        validate_suggested_questions(settings["suggested_questions"])
    prompt = project.path("instructions")
    if prompt.exists():
        if "system_prompt" in settings:
            raise ProjectError("Remove system_prompt from settings; instructions.md is its authority")
        settings["system_prompt"] = prompt.read_text(encoding="utf-8")
    return canonical(settings)


def pull(project, client, agent_id, *, reconcile=False):
    scope = project.check_scope(client)
    if project.target.get("agent_id") not in (None, agent_id):
        raise ProjectError("Agent differs from project binding")
    state = project.state()
    entry = state.get("resources", {}).get("agent", {})
    if entry.get("scope") and not scope_matches(entry["scope"], scope, allow_unbound_agent=True):
        raise ProjectError("Agent mapping scope differs from saved receipt")
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch") and not reconcile:
        raise ProjectError("Unfinished operation; inspect receipt then pull --reconcile")
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch") and entry.get("server_id") and entry["server_id"] != agent_id:
        raise ProjectError("Reconcile the saved Agent identity before importing another Agent")
    if project.portable:
        recovering_create = reconcile and project.target.get("agent_id") is None and entry.get("server_id") == agent_id
        if not project.target or project.target.get("agent_id") != agent_id and not recovering_create:
            raise ProjectError("Configure takeover with agent bind --alias <name> --agent <id> before pull")
    editable, editable_settings = observe(client, agent_id)
    versions = agents.list_versions(client, agent_id)
    published_id = editable.get("publish_history_id")
    published = agents.get_version(client, agent_id, published_id) if published_id else None
    if project.portable:
        from .portable import logical_remote
        from .project_attachments import import_originals
        latest = max(versions, key=lambda h: h.get("version_number", 0)) if versions else None
        history = agents.get_version(client, agent_id, latest["id"]) if latest else {}
        originals = import_originals(project, client, history) if not project.path("agent").exists() else {"obtained": [], "gaps": []}
        from .project_knowledge import import_references
        knowledge = import_references(project, client, history) if not project.path("agent").exists() else {"obtained": [], "gaps": []}
        # Reload after original import so its mappings cannot be overwritten.
        state = project.state()
        editable_settings = logical_remote(project, editable_settings)
        editable = logical_remote(project, writable(editable))
        published = logical_remote(project, writable(published)) if published else None
    imported_at = now()
    directory = project.local_dir / "imports" / imported_at.replace(":", "-")
    save_json(directory / "agent.json", {"editable": editable, "published": published, "versions": versions,
                                         "retrieved_at": imported_at, "scope": scope})
    settings = dict(editable_settings)
    paths = (project.path("agent"), project.path("instructions"))
    if not any(p.exists() for p in paths):
        prompt = settings.pop("system_prompt", "")
        save_json(paths[0], settings)
        paths[1].write_text(prompt, encoding="utf-8")
    if project.portable:
        entry = state.setdefault("resources", {}).setdefault("agent", {})
        if reconcile:
            reconcile_entry(project, entry, editable_settings)
            if recovering_create and entry.get("status") == "imported_unvalidated":
                project.bind(agent_id=agent_id)
        entry.update(server_id=agent_id, observed=editable_settings, tracking_version=1)
        state.update(queried_at=imported_at, versions=versions, published_history_id=published_id)
        project.save_state(state)
        from .deployment import compare
        return {"agent_id": agent_id, "snapshot": str(directory), "accepted": False,
                "comparison": compare(entry, local_settings(project), editable_settings), "originals": originals, "knowledge": knowledge,
                "gaps": ["Website crawl settings are excluded; source snapshots do not recreate crawling; import Eval separately",
                         "Design intent, confirmations and previous local history cannot be reconstructed"]}
    elif "agent" in state.get("resources", {}) and not reconcile:
        # A repeated pull records observation, never advances a live sync base.
        state["observed_agent"] = editable_settings
        state["queried_at"] = imported_at
        project.save_state(state)
        return {"agent_id": agent_id, "snapshot": str(directory), "local_preserved": True, "base_preserved": True, "accepted": False}
    project.bind(agent_id=agent_id, api_base=scope["api_base"], workspace_id=scope["workspace_id"])
    entry = state.setdefault("resources", {}).setdefault("agent", {})
    if reconcile and entry:
        reconcile_entry(project, entry, editable_settings)
    else:
        entry.update(base=editable_settings, status="imported_unvalidated")
    entry["server_id"] = agent_id
    state.update(queried_at=imported_at, versions=versions, published_history_id=published_id)
    project.save_state(state)
    return {"agent_id": agent_id, "snapshot": str(directory), "local_preserved": True,
            "accepted": False, "published_history_id": published_id,
            "gaps": ["KB/Eval/Tester import is separate", "Import does not establish intended behavior or validate quality"]}


def preview(project, client, remove_tools=None, note=""):
    scope = project.check_scope(client)
    agent_id = project.target.get("agent_id")
    entry = project.state().get("resources", {}).get("agent", {})
    if entry.get("scope") and not scope_matches(entry["scope"], scope, allow_unbound_agent=True):
        raise ProjectError("Agent mapping scope differs from saved receipt")
    if not agent_id and entry.get("server_id"):
        raise ProjectError(f"Previous create identity {entry['server_id']} is known; agent pull --agent <id> --reconcile to bind it before retry")
    if agent_id and entry.get("server_id") != agent_id:
        raise ProjectError("Pull the bound Agent before applying")
    if project.portable and not project.target:
        raise ProjectError("Configure a deployment with agent bind --new or --agent <id> before apply")
    if project.portable and not agent_id and project.target.get("intent") != "create":
        raise ProjectError("Missing Agent identity is not create intent; configure a separate explicitly new deployment or reconcile its known identity")
    remote = observe(client, agent_id)[1] if agent_id else {}
    local = local_settings(project)
    if project.portable:
        from .portable import check_agent, check_models, logical_remote
        check_agent(project, local)
        check_models(project, client, local)
        remote = logical_remote(project, remote)
    plan = plan_change(project, "agent", agent_id, entry.get("base", {}), local, remote)
    plan["scope"] = scope
    if project.portable:
        from .portable import connection_fingerprint
        plan["environment"] = connection_fingerprint(project)
        plan["operator"] = project.preview_identity(client)
    plan["version_note"] = note if agent_id else ""
    payload = plan["payload"]
    if not agent_id and any(k in payload for k in ("response_mode", "output_presentation_policy")):
        if not project.portable:
            raise ProjectError("External create does not accept response_mode/output_presentation_policy; create Draft first then explicitly update these settings")
        plan["deferred_fields"] = [k for k in ("response_mode", "output_presentation_policy") if k in payload]
        for key in plan["deferred_fields"]:
            payload.pop(key)
        plan["next_step"] = "After successful create readback, review a second Agent apply for deferred update-only settings"
    if not payload.get("name") or not payload.get("system_prompt"):
        raise ProjectError("Agent requires name and instructions")
    validate_unified_tools(payload.get("unified_tools"))
    validate_human_handoff(payload.get("human_handoff"))
    validate_suggested_questions(payload.get("suggested_questions"))
    # Removing a tool from a full list needs explicit, reviewable removal intent.
    before = {t.get("id") for t in remote.get("unified_tools", []) if t.get("id")}
    after = {t.get("id") for t in payload.get("unified_tools", []) if t.get("id")}
    if before - after != set(remove_tools or []):
        plan["conflicts"].append(f"explicit_tool_removal_required:{sorted(before-after)}")
    plan["remove_tools"] = remove_tools or []
    plan.pop("token")
    plan["token"] = fingerprint(plan)
    return plan


def apply(project, client, plan, expected, note=""):
    # Second fetch narrows the race window; no server atomicity is claimed.
    current = preview(project, client, remove_tools=plan.get("remove_tools"), note=note)
    if current["token"] != plan["token"]:
        raise ProjectError("Remote or local changed during preflight; preview again")
    agent_id = plan["server_id"]
    def mutate(payload):
        from .portable import translate
        payload = translate(project, payload)
        if agent_id:
            return client.patch(f"/external/agents/{agent_id}", json={**payload, "version_note": plan["version_note"]})
        return client.post("/external/agents", json=payload)
    from .portable import logical_remote
    result = apply_change(project, plan, expected, mutate, lambda sid: logical_remote(project, observe(client, sid)[1]))
    if result["status"] == "applied":
        sid = result["plan"]["server_id"] or result["response"]["id"]
        scope = project.check_scope(client)
        project.bind(agent_id=sid, api_base=scope["api_base"], workspace_id=scope["workspace_id"])
    return result
