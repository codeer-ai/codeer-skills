"""Explicit Tester separation using ID-bound creation and pair receipts."""
from copy import deepcopy

from . import eval_ as api
from .project import ProjectError, fingerprint, read_json, scope_matches
from .project_eval import TESTER_FIELDS, select, shared_impact
from .sync import apply_change, plan_change, reconcile_entry


def pair_values(client, case_id):
    return {row["evaluator_id"]: row.get("rubric", "")
            for info in api.get_case_evaluator_infos(client, case_ids=[case_id])
            for row in info.get("evaluators", [])}


def tester_plan(project, client, local_id):
    scope = project.check_scope(client)
    if not scope.get("agent_id"):
        raise ProjectError("Tester separation requires a bound Agent")
    resources = project.state().get("resources", {})
    source = resources.get(f"tester:{local_id}", {})
    if not source.get("server_id"):
        raise ProjectError("Map the source Tester explicitly before separation")
    if source.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
        raise ProjectError("Reconcile the source Tester before separation")
    if source.get("scope") and not scope_matches(source["scope"], scope):
        raise ProjectError("Source Tester mapping belongs to another scope")
    key = f"fork-tester:{local_id}"
    operation = resources.get(key, {})
    active = bool(operation and operation.get("status") != "forked")
    if active and operation.get("scope") and not scope_matches(operation["scope"], scope):
        raise ProjectError("Fork receipt belongs to another scope")
    if active and operation.get("source_id") != source["server_id"]:
        raise ProjectError("Source mapping changed during separation; inspect its receipt")
    sid = operation.get("server_id") if active else None
    rows = [row for row in read_json(project.path("evals"), {}).get("testers", []) if row.get("local_id") == local_id]
    if len(rows) != 1:
        raise ProjectError("Require one declared local Tester and its reviewed settings")
    desired = select(rows[0], TESTER_FIELDS)
    if not desired.get("name") or not desired.get("system_prompt_template"):
        raise ProjectError("Tester name/template are required")
    from .portable import check_models, logical_remote, connection_fingerprint
    check_models(project, client, rows[0])
    remote = logical_remote(project, select(api.get_evaluator(client, sid), TESTER_FIELDS)) if sid else {}
    create = plan_change(project, key, sid, operation.get("base", {}) if active else {}, desired, remote)
    if sid and remote != desired:
        raise ProjectError("Created Tester differs; reconcile instead of modifying it")
    create.update(scope=scope, operator=project.preview_identity(client), source_id=source["server_id"],
                  environment=connection_fingerprint(project))
    create["token"] = fingerprint({k: v for k, v in create.items() if k != "token"})
    allowed = {row["id"] for row in api.list_cases(client, scope["agent_id"])}
    pairs = []
    for name, mapped in resources.items():
        if not name.startswith("case:") or mapped.get("status") == "retired":
            continue
        case_id = mapped.get("server_id")
        if mapped.get("scope") and not scope_matches(mapped["scope"], scope):
            raise ProjectError("Mapped Case belongs to another scope")
        if case_id not in allowed:
            raise ProjectError("Mapped Case is outside this Agent")
        current = pair_values(client, case_id)
        if source["server_id"] not in current and not (sid and sid in current):
            continue
        pair_key = f"pairs:{name.split(':', 1)[1]}"
        if resources.get(pair_key, {}).get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
            raise ProjectError("Unresolved pairs; run tester-fork --reconcile first")
        desired_pairs = {(sid or "new:tester") if tid == source["server_id"] else tid: rubric for tid, rubric in current.items()}
        pairs.append({"resource": pair_key, "case_id": case_id, "before": current, "after": desired_pairs})
    result = {"scope": scope, "local_id": local_id, "source_id": source["server_id"], "create": create, "pairs": pairs,
              "source": select(api.get_evaluator(client, source["server_id"]), TESTER_FIELDS),
              "source_users": shared_impact(client, source["server_id"]),
              "limitation": "Only mapped Cases in this Agent are reconnected; shared source remains unchanged"}
    result["token"] = fingerprint(result)
    return result


def tester_fork(project, client, local_id, *, dry_run=False, expected=None, reconcile=False):
    key = f"fork-tester:{local_id}"
    if reconcile:
        scope = project.check_scope(client)
        state = project.state()
        entry = state.get("resources", {}).get(key, {})
        if entry.get("status") == "forked":
            raise ProjectError("Tester separation is already complete; no unfinished fork to reconcile")
        sid = entry.get("server_id")
        if not sid:
            raise ProjectError("Created Tester identity unknown; never repeat creation")
        if entry.get("scope") != scope:
            raise ProjectError("Fork receipt belongs to another scope")
        from .portable import logical_remote
        reconcile_entry(project, entry, logical_remote(project, select(api.get_evaluator(client, sid), TESTER_FIELDS)))
        for name, pair in state["resources"].items():
            if not name.startswith("pairs:") or pair.get("status") not in ("pending", "outcome_unknown", "readback_mismatch"):
                continue
            receipt = read_json(project.root / pair.get("receipt", ""), {}) if pair.get("receipt") else {}
            if receipt.get("plan", {}).get("fork_operation") != key or receipt["plan"].get("fork_id") != sid:
                continue
            if pair.get("scope") != scope:
                raise ProjectError("Pair receipt belongs to another scope")
            reconcile_entry(project, pair, pair_values(client, pair["server_id"]))
        project.save_state(state)
        return {"status": "observed", "new_id": sid, "remote_mutations": 0,
                "next_step": "Review a fresh tester-fork preview to finish reconnection"}
    plan = tester_plan(project, client, local_id)
    if dry_run:
        return plan
    if expected != plan["token"]:
        raise ProjectError("Missing/stale tester-fork --expect")
    state = project.state()
    if state.get("resources", {}).get(key, {}).get("status") == "forked":
        del state["resources"][key]
    state.setdefault("resources", {}).setdefault(key, {}).update(source_id=plan["source_id"])
    project.save_state(state)
    from .portable import translate, logical_remote
    create = plan["create"]
    result = apply_change(project, create, create["token"],
                          lambda body: client.post("/external/eval/evaluators", json=translate(project, body)),
                          lambda sid: logical_remote(project, select(api.get_evaluator(client, sid), TESTER_FIELDS)))
    if result["status"] not in ("applied", "unchanged"):
        return result
    sid = project.state()["resources"][key]["server_id"]
    for pair in plan["pairs"]:
        before = pair_values(client, pair["case_id"])
        if before != pair["before"]:
            raise ProjectError("Pairs changed during separation; preview again")
        desired = {(sid if tid == "new:tester" else tid): rubric for tid, rubric in pair["after"].items()}
        update = {"resource": pair["resource"], "server_id": pair["case_id"], "scope": plan["scope"],
                  "local": desired, "remote": before, "payload": desired, "conflicts": [], "changed": desired != before,
                  "fork_operation": key, "fork_id": sid}
        update["token"] = fingerprint(update)
        result = apply_change(project, update, update["token"],
                              lambda body, cid=pair["case_id"]: api.replace_case_evaluator_infos(
                                  client, case_id=cid, evaluators=[{"evaluator_id": tid, "rubric": rubric} for tid, rubric in body.items()]),
                              lambda cid: pair_values(client, cid))
        if result["status"] not in ("applied", "unchanged"):
            return result
    state = project.state()
    state["resources"][f"tester:{local_id}"] = {**deepcopy(state["resources"][key]), "status": "applied",
                                                "previous_server_id": plan["source_id"]}
    state["resources"][key]["status"] = "forked"
    project.save_state(state)
    return {"status": "forked", "source_id": plan["source_id"], "new_id": sid,
            "reconnected_cases": [p["case_id"] for p in plan["pairs"]], "source_modified": False}
