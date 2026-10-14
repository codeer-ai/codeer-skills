"""Stable Case/Tester design, ID-bound import, and per-resource reconciliation."""
from copy import deepcopy
import uuid

from . import agents, eval_ as api
from .client import CodeerError
from .project import ProjectError, fingerprint, now, read_json, save_json, scope_matches
from .sync import apply_change, plan_change, reconcile_entry

CASE_FIELDS = ("input", "expected_output", "attachment_ids", "label_ids", "meta", "note")
TESTER_FIELDS = ("name", "system_prompt_template", "description", "judge_llm_model_id")


def select(row, fields):
    result = {k: deepcopy(row[k]) for k in fields if k in row}
    if fields == CASE_FIELDS:
        for key, source in (("attachment_ids", "attachments"), ("label_ids", "labels")):
            if source in row and key not in result:
                result[key] = [item["id"] for item in row[source] or []]
            if key in result:
                result[key] = sorted(result[key] or [])
    return result


def references(design):
    """Local source and delivery reports; URLs remain external observations."""
    testers = design.get("testers", [])
    for tester in testers if isinstance(testers, list) else []:
        if isinstance(tester, dict):
            items = tester.get("evidence", [])
            for item in items if isinstance(items, list) else []:
                if isinstance(item, dict) and isinstance(item.get("verification"), str):
                    yield item["verification"]
    cases = design.get("cases", [])
    for case in cases if isinstance(cases, list) else []:
        if isinstance(case, dict) and isinstance(case.get("source"), dict):
            document = case["source"].get("document")
            if isinstance(document, str):
                yield document


def validate_design(design, state=None, root=None):
    issues = []
    design_issues = []
    evidence_issues = []
    gaps = {}

    def result(pair_count=0):
        operations = [f"unreconciled: {k}" for k, v in (state or {}).get("resources", {}).items()
                      if v.get("status") in ("pending", "outcome_unknown", "readback_mismatch")]
        return {"design_complete": not issues and not design_issues and not evidence_issues,
                "apply_ready": not issues and not design_issues and not evidence_issues and not operations,
                "pair_count": pair_count, "structural_issues": issues, "evidence_issues": evidence_issues,
                "design_issues": design_issues,
                "operation_issues": operations, "evidence_gaps": list(gaps.values()),
                "unresolved": issues + design_issues + evidence_issues + operations}

    if not isinstance(design, dict) or design.get("schema_version") != 1:
        issues.append("Eval design requires schema_version 1")
        return result()
    testers = design.get("testers", [])
    cases = design.get("cases", [])
    if not isinstance(testers, list) or not isinstance(cases, list):
        issues.append("testers and cases must be arrays")
        return result()
    indexes = {}
    for kind, rows in (("tester", testers), ("case", cases)):
        index = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("local_id"), str) or not row["local_id"].strip():
                issues.append(f"{kind}: missing local_id")
                continue
            local_id = row["local_id"]
            if local_id in index:
                issues.append(f"duplicate {kind} local_id: {local_id}")
            index[local_id] = row
        indexes[kind] = index
    for tid, tester in indexes["tester"].items():
        if not tester.get("rationale"):
            issues.append(f"tester {tid}: document reuse/change/new rationale")
        if not tester.get("name") or not isinstance(tester.get("system_prompt_template"), str) or not tester["system_prompt_template"].strip():
            issues.append(f"tester {tid}: name/template required")
        items = tester.get("evidence", [])
        if not isinstance(items, list):
            issues.append(f"tester {tid}: evidence must be an array")
            items = []
        for evidence in items:
            if not isinstance(evidence, dict) or not evidence.get("variable") or not evidence.get("producer"):
                issues.append(f"tester {tid}: evidence requires variable and producer")
    pair_count = 0
    for cid, case in indexes["case"].items():
        if "rubric" in case:
            issues.append(f"case {cid}: rubric belongs to a Tester pair, not the Case")
        if not isinstance(case.get("input"), str) or not case["input"].strip() or not isinstance(case.get("source"), dict) or not case["source"]:
            issues.append(f"case {cid}: input/source required")
        pairs = case.get("pairs", [])
        if not isinstance(pairs, list):
            issues.append(f"case {cid}: pairs must be an array")
            pairs = []
        if not pairs:
            issues.append(f"case {cid}: no Tester/Rubric pairs")
        seen = set()
        for pair in pairs:
            pair_count += 1
            if not isinstance(pair, dict) or not isinstance(pair.get("tester"), str):
                issues.append(f"case {cid}: pair requires Tester ID")
                continue
            tid = pair.get("tester")
            if tid in seen:
                issues.append(f"case {cid}: duplicate Tester pair {tid}")
            seen.add(tid)
            tester = indexes["tester"].get(tid)
            if not tester or not pair.get("rubric"):
                issues.append(f"case {cid}: missing Tester or Rubric for {tid}")
                continue
            items = tester.get("evidence", [])
            evidence = {e.get("variable"): e for e in items if isinstance(e, dict) and isinstance(e.get("variable"), str)} if isinstance(items, list) else {}
            required = pair.get("required_evidence", [])
            if not isinstance(required, list) or any(not isinstance(v, str) for v in required):
                issues.append(f"{cid}/{tid}: required_evidence must be string array")
                continue
            for variable in required:
                item = evidence.get(variable, {})
                template = tester.get("system_prompt_template")
                reasons = []
                if not isinstance(template, str) or ("{" + variable + "}") not in template:
                    reasons.append("template cannot see variable")
                    evidence_issues.append(f"{cid}/{tid}: template cannot see {variable}")
                if item.get("availability") != "verified" or not item.get("verification") or not item.get("producer"):
                    reasons.append("unverified producer/delivery")
                    evidence_issues.append(f"{cid}/{tid}: unverified producer/delivery of {variable}")
                if reasons:
                    gap = gaps.setdefault((tid, variable), {"tester": tid, "variable": variable,
                                                           "reasons": [], "affected_pairs": []})
                    gap["reasons"] = sorted(set(gap["reasons"] + reasons))
                    pair_ref = {"case": cid, "tester": tid}
                    if pair_ref not in gap["affected_pairs"]:
                        gap["affected_pairs"].append(pair_ref)
    if not cases:
        design_issues.append("No cases designed")
    if root is not None:
        for reference in references(design):
            if reference.startswith(("https://", "http://")):
                continue
            path = (root / reference).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                issues.append(f"Missing or outside-project evidence/source file: {reference}")
    resources = (state or {}).get("resources", {})
    for cid in indexes["case"]:
        if resources.get(f"case:{cid}", {}).get("status") == "retired":
            issues.append(f"case {cid}: retired; remove this Case from the design (use a new local_id for an intentional new Case)")
    return result(pair_count)


def pull(project, client, *, reconcile=False):
    scope = project.check_scope(client)
    agent_id = scope["agent_id"]
    if not agent_id:
        raise ProjectError("Bind an Agent before Eval import")
    cases = api.list_cases(client, agent_id)
    infos = api.get_case_evaluator_infos(client, case_ids=[c["id"] for c in cases]) if cases else []
    by_case = {r["case_id"]: r.get("evaluators", []) for r in infos}
    ids = {e["evaluator_id"] for row in infos for e in row.get("evaluators", [])}
    testers = {tid: api.get_evaluator(client, tid) for tid in sorted(ids)}
    originals = {"obtained": [], "gaps": []}
    if project.portable and not project.path("evals").exists():
        from .project_attachments import import_originals
        for case in cases:
            if case.get("attachments") or case.get("attachment_ids"):
                observed = import_originals(project, client, case)
                originals["obtained"].extend(observed["obtained"])
                originals["gaps"].extend(observed["gaps"])
    state = project.state()
    resources = state.setdefault("resources", {})
    if reconcile:
        case_ids = {c["id"] for c in cases}
        for key, entry in list(resources.items()):
            if key.startswith("case:") and entry.get("delete_receipt") and entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
                reconcile_delete(project, client, state, key, scope, case_ids)
        # A created Tester may not have been assigned when readback failed.
        for key, entry in resources.items():
            if key.startswith(("tester:", "case:", "pairs:")) and entry.get("server_id"):
                if entry.get("scope") and not scope_matches(entry["scope"], scope):
                    raise ProjectError(f"Mapping scope mismatch: {key}")
                sid = entry["server_id"]
                if entry.get("status") == "retired":
                    if sid in case_ids:
                        raise ProjectError(f"Retired Case {sid} is unexpectedly present; inspect its deletion receipt")
                    continue
                if key.startswith("tester:"):
                    if sid not in testers:
                        testers[sid] = api.get_evaluator(client, sid)
                elif sid not in {c["id"] for c in cases}:
                    raise ProjectError(f"Mapped Case {sid} is absent from this Agent; verify deletion/ownership before recovery")
    def local_id(kind, sid):
        matches = [key.split(":", 1)[1] for key, v in resources.items() if key.startswith(kind+":") and v.get("server_id") == sid]
        if len(matches) > 1:
            raise ProjectError(f"Ambiguous mapping for {kind} {sid}")
        return matches[0] if matches else f"{kind}-{sid}"
    def record(key, sid, base):
        if project.portable:
            if key in resources:
                if reconcile:
                    reconcile_entry(project, resources[key], base)
                resources[key]["observed"] = base
            return
        if resources.get(key, {}).get("status") == "retired":
            raise ProjectError(f"Retired resource {key} is unexpectedly present; inspect its deletion receipt")
        if key in resources and reconcile:
            if resources[key].get("scope") and not scope_matches(resources[key]["scope"], scope):
                raise ProjectError(f"Mapping scope mismatch: {key}")
            reconcile_entry(project, resources[key], base)
            resources[key]["scope"] = scope
        elif key not in resources:
            resources[key] = {"server_id": sid, "base": base, "status": "imported_unvalidated", "scope": scope}
    design = {"schema_version": 1, "testers": [], "cases": []}
    for sid, tester in testers.items():
        tid = local_id("tester", sid)
        record(f"tester:{tid}", sid, select(tester, TESTER_FIELDS))
        design["testers"].append({"local_id": tid, **select(tester, TESTER_FIELDS),
                                   "rationale": "Imported existing shared Tester; review suitability", "evidence": []})
    for case in cases:
        if project.portable:
            from .portable import logical_remote
            case = {**case, **logical_remote(project, select(case, CASE_FIELDS))}
        sid = case["id"]
        cid = local_id("case", sid)
        record(f"case:{cid}", sid, select(case, CASE_FIELDS))
        pairs = by_case.get(sid, [])
        record(f"pairs:{cid}", sid, {p["evaluator_id"]: p.get("rubric", "") for p in pairs})
        design["cases"].append({"local_id": cid, **select(case, CASE_FIELDS),
                                "source": {"remote_case_id": sid, "retrieved_at": now()},
                                "pairs": [{"tester": local_id("tester", p["evaluator_id"]), "rubric": p.get("rubric", ""), "required_evidence": []} for p in pairs]})
    stamp = now().replace(":", "-")
    from .portable import logical_remote, redact
    safe_cases = [{**redact(project, row), **logical_remote(project, select(row, CASE_FIELDS))} for row in cases]
    save_json(project.local_dir / "imports" / stamp / "eval.json", {"scope": scope, "cases": safe_cases, "infos": infos, "testers": redact(project, testers), "originals": originals})
    if not project.path("evals").exists():
        save_json(project.path("evals"), design)
    else:
        save_json(project.root / "reviews" / f"{stamp}.import-design.json", design)
    state["queried_at"] = now()
    project.save_state(state)
    return {"case_count": len(cases), "tester_count": len(testers), "accepted": False, "originals": originals,
            "gaps": ["Imported evidence requirements need semantic review; current resources are not historical snapshots"]}


def shared_impact(client, tester_id):
    ws, org = client.resolve_scope()
    impacted = []
    for agent in agents.list_all(client, workspace_id=ws, organization_id=org):
        cases = api.list_cases(client, agent["id"])
        infos = api.get_case_evaluator_infos(client, case_ids=[c["id"] for c in cases]) if cases else []
        impacted.extend({"agent_id": agent["id"], "case_id": row["case_id"]} for row in infos
                        if any(e["evaluator_id"] == tester_id for e in row.get("evaluators", [])))
    return impacted


def preview(project, client, design, only=None):
    scope = project.check_scope(client)
    validation = validate_design(design, project.state(), project.root)
    if not validation["design_complete"] and not only:
        raise ProjectError(f"Eval design unresolved: {validation['unresolved']}")
    if not scope["agent_id"]:
        raise ProjectError("Bind Agent before applying Eval")
    resources = project.state().get("resources", {})
    plans = []
    known_case_ids = {c["id"] for c in api.list_cases(client, scope["agent_id"])}
    tester_ids = {}
    for tester in design["testers"]:
        key = f"tester:{tester['local_id']}"
        entry = resources.get(key, {})
        sid = entry.get("server_id")
        if project.portable and not sid and (project.target.get("intent") != "create" or known_case_ids) and entry.get("status") != "new":
            raise ProjectError(f"Map existing {key} with agent adopt --remote-id <id>, or explicitly declare --remote-id new")
        if entry.get("scope") and not scope_matches(entry["scope"], scope):
            raise ProjectError(f"Mapping scope mismatch: {key}")
        from .portable import logical_remote
        if project.portable:
            from .portable import check_models
            check_models(project, client, tester)
        remote = logical_remote(project, select(api.get_evaluator(client, sid), TESTER_FIELDS)) if sid else {}
        plan = plan_change(project, key, sid, entry.get("base", {}), select(tester, TESTER_FIELDS), remote)
        if sid and plan["changed"]:
            plan["shared_impact"] = shared_impact(client, sid)
        plans.append(plan)
        tester_ids[tester["local_id"]] = sid or f"new:{tester['local_id']}"
    for case in design["cases"]:
        cid = case["local_id"]
        key = f"case:{cid}"
        entry = resources.get(key, {})
        sid = entry.get("server_id")
        if project.portable and not sid and (project.target.get("intent") != "create" or known_case_ids) and entry.get("status") != "new":
            raise ProjectError(f"Map existing {key} before applying; missing state is not permission to create")
        if entry.get("scope") and not scope_matches(entry["scope"], scope):
            raise ProjectError(f"Mapping scope mismatch: {key}")
        if entry.get("status") == "retired":
            raise ProjectError(f"Retired Case {cid} is still in the design; remove it before apply")
        if sid and sid not in known_case_ids:
            raise ProjectError(f"Unknown or cross-Agent mapped case {sid}")
        remote = logical_remote(project, select(api.get_case(client, sid), CASE_FIELDS)) if sid else {}
        if project.portable:
            from .portable import translate
            selected = select(case, CASE_FIELDS)
            if any(not str(v).startswith("attachment:") for v in selected.get("attachment_ids", [])):
                raise ProjectError("Portable Case attachments require attachment:<local-id> references")
            if any(not str(v).startswith("env:") for v in selected.get("label_ids", [])):
                raise ProjectError("Portable labels require env:<VARIABLE> references")
            translate(project, selected)
        plans.append(plan_change(project, key, sid, entry.get("base", {}), select(case, CASE_FIELDS), remote))
        assigned = api.get_case_evaluator_infos(client, case_ids=[sid]) if sid else []
        current = {e["evaluator_id"]: e.get("rubric", "") for r in assigned for e in r.get("evaluators", [])}
        base = resources.get(f"pairs:{cid}", {}).get("base", {})
        desired = {tester_ids[p["tester"]]: p["rubric"] for p in case["pairs"]}
        # Omission retains assignments. Explicit removal is a separate reviewed list.
        removed = case.get("remove_tester_ids", [])
        if not isinstance(removed, list) or any(not isinstance(tid, str) or not tid for tid in removed):
            raise ProjectError(f"case {cid}: remove_tester_ids must be an array of server Tester IDs")
        if project.portable:
            if any(not tid.startswith("tester:") for tid in removed):
                raise ProjectError("Portable removals require tester:<local-id> references")
            resolved = [resources.get(tid, {}).get("server_id") for tid in removed]
            if any(tid is None for tid in resolved):
                raise ProjectError("Unmapped Tester removal reference")
            removed = resolved
        pair_plan = plan_change(project, f"pairs:{cid}", sid, base, desired, current)
        for tid in removed:
            if tid in desired:
                pair_plan["conflicts"].append(f"pair_both_assigned_and_removed:{tid}")
            already_removed = tid in resources.get(f"pairs:{cid}", {}).get("removed_ids", [])
            if (already_removed and tid in current) or (not already_removed and (tid not in current or tid not in base or current[tid] != base[tid])):
                pair_plan["conflicts"].append(f"cannot_remove_changed_or_unknown_pair:{tid}")
            pair_plan["payload"].pop(tid, None)
        pair_plan["removed_ids"] = removed
        pair_plan["changed"] = pair_plan["payload"] != current
        plans.append(pair_plan)
    if only:
        plans = [p for p in plans if p["resource"] in only]
    for p in plans:
        p["scope"] = scope
        if project.portable:
            from .portable import connection_fingerprint
            p["environment"] = connection_fingerprint(project)
            p["operator"] = project.preview_identity(client)
        p["token"] = fingerprint({k: v for k, v in p.items() if k != "token"})
    result = {"scope": scope, "design": design, "plans": plans, "validation": validation, "only": only,
              "conflicts": [p["resource"] for p in plans if p["conflicts"]]}
    result["token"] = fingerprint(result)
    return result


def apply(project, client, plan, expected):
    if plan["token"] != expected or plan["conflicts"]:
        raise ProjectError("Missing/stale --expect or unresolved resource conflicts")
    if preview(project, client, plan["design"], only=plan.get("only"))["token"] != expected:
        raise ProjectError("Resources changed before apply; review again")
    receipts = []
    for original in plan["plans"]:
        p = deepcopy(original)
        kind, local_id = p["resource"].split(":", 1)
        resources = project.state().get("resources", {})
        if kind == "pairs":
            p["server_id"] = resources[f"case:{local_id}"]["server_id"]
            p["payload"] = {(resources[f"tester:{k[4:]}"]["server_id"] if k.startswith("new:") else k): v for k, v in p["payload"].items()}
            p["local"] = {(resources[f"tester:{k[4:]}"]["server_id"] if k.startswith("new:") else k): v for k, v in p["local"].items()}
            def readback(sid):
                return {e["evaluator_id"]: e.get("rubric", "") for r in api.get_case_evaluator_infos(client, case_ids=[sid]) for e in r.get("evaluators", [])}
            def mutate(body):
                return api.replace_case_evaluator_infos(client, case_id=p["server_id"], evaluators=[{"evaluator_id": k, "rubric": v} for k, v in body.items()])
        elif kind == "tester":
            def readback(sid):
                from .portable import logical_remote
                return logical_remote(project, select(api.get_evaluator(client, sid), TESTER_FIELDS))
            def mutate(body):
                from .portable import translate
                body = translate(project, body)
                return client.put(f"/external/eval/evaluators/{p['server_id']}", json=body) if p["server_id"] else client.post("/external/eval/evaluators", json=body)
        else:
            def readback(sid):
                from .portable import logical_remote
                return logical_remote(project, select(api.get_case(client, sid), CASE_FIELDS))
            def mutate(body):
                from .portable import translate
                body = translate(project, body)
                return client.put(f"/external/eval/cases/{p['server_id']}", json=body) if p["server_id"] else client.post("/external/eval/cases", json={**body, "agent_id": project.target["agent_id"]})
        # Recheck each resource immediately before its own write, after earlier successes.
        if p["server_id"] and readback(p["server_id"]) != p["remote"]:
            raise ProjectError(f"Remote changed during partial apply: {p['resource']}; successful receipts retained")
        receipt = apply_change(project, p, p["token"], mutate, readback)
        receipts.append(receipt)
        if receipt["status"] == "readback_mismatch":
            break
        state = project.state()
        state["resources"][p["resource"]]["scope"] = plan["scope"]
        project.save_state(state)
    return {"receipts": receipts, "complete": all(r["status"] in ("unchanged", "applied") for r in receipts)}


def command_apply(project, client, changes, *, dry_run, expected):
    """Adapt existing resource commands to the same scoped design/sync contract."""
    design = read_json(project.path("evals"))
    if not isinstance(design, dict) or design.get("schema_version") != 1:
        raise ProjectError("eval pull or create a stable evals/design.json before project mutations")
    for key, fields in changes.items():
        kind, local_id = key.split(":", 1)
        if kind == "case" and "rubric" in fields:
            raise ProjectError("Project Rubric belongs to a Tester pair; use rubrics-apply or edit case.pairs instead of case-update --rubric")
        rows = design["testers" if kind == "tester" else "cases"]
        matches = [r for r in rows if r["local_id"] == local_id]
        if len(matches) != 1:
            raise ProjectError(f"Unknown/ambiguous stable resource: {key}")
        matches[0].update(fields)
    plan = preview(project, client, design, only=list(changes))
    if dry_run:
        return plan
    if expected != plan["token"] or plan["conflicts"]:
        raise ProjectError("Missing/stale --expect or unresolved resource conflicts")
    # Keep an authorized proposal durable even if a later resource fails.
    save_json(project.path("evals"), design)
    result = apply(project, client, plan, expected)
    return result


def mapped_key(project, kind, server_id):
    matches = [k for k, v in project.state().get("resources", {}).items()
               if k.startswith(kind+":") and v.get("server_id") == server_id]
    if len(matches) != 1:
        raise ProjectError(f"Unknown/ambiguous {kind} mapping for {server_id}; eval pull first")
    return matches[0]


def checked_case(project, client, server_id):
    """Resolve a mapped Case without trusting a saved mapping for ownership."""
    scope = project.check_scope(client)
    key = mapped_key(project, "case", server_id)
    entry = project.state()["resources"][key]
    if entry.get("scope") and not scope_matches(entry["scope"], scope):
        raise ProjectError(f"Mapping scope mismatch: {key}")
    if entry.get("status") in ("retired", "pending", "outcome_unknown", "readback_mismatch"):
        raise ProjectError(f"Case {key} is retired or unresolved; inspect its receipt and eval pull --reconcile before retrying")
    current = api.get_case(client, server_id)
    if not scope["agent_id"] or current.get("agent_id") != scope["agent_id"]:
        raise ProjectError("Case does not belong to the bound Agent; use --outside-project for an intentional standalone operation")
    return current


def delete_readback(client, server_id, scope):
    """Only a scoped 404 proves absence; transport/auth errors remain unresolved."""
    try:
        current = api.get_case(client, server_id)
    except CodeerError as exc:
        if exc.status == 404:
            return {"absent": True, "server_id": server_id}
        raise
    if current.get("agent_id") != scope["agent_id"]:
        raise ProjectError("Case ownership changed during deletion; inspect before recovery")
    return {"absent": False, "current": current}


def retire_deleted(resources, keys):
    for key in keys:
        resources[key].update(status="retired", retired_at=now())


def delete_case(project, client, server_id, *, dry_run=False, expected=None):
    """Explicit deletion retires identity without editing the authored design."""
    current = checked_case(project, client, server_id)
    scope = project.check_scope(client)
    key = mapped_key(project, "case", server_id)
    state = project.state()
    resources = state["resources"]
    pair_key = "pairs:" + key.split(":", 1)[1]
    keys = [key] + ([pair_key] if pair_key in resources else [])
    for related in keys:
        entry = resources[related]
        if entry.get("server_id") != server_id or (entry.get("scope") and not scope_matches(entry["scope"], scope)):
            raise ProjectError(f"Mapping scope/identity mismatch: {related}")
        if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch", "retired"):
            raise ProjectError(f"Reconcile {related} before deletion")
    plan = {"operation": "case_delete", "resource": key, "server_id": server_id,
            "scope": scope, "current": current}
    if project.portable:
        from .portable import logical_remote
        plan["current"] = logical_remote(project, current)
        plan["operator"] = project.preview_identity(client)
        plan["token"] = fingerprint(plan)
    if dry_run:
        return {**plan, "dry_run": True, "method": "DELETE", "path": f"/external/eval/cases/{server_id}",
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval."}
    if project.portable and expected != plan["token"]:
        raise ProjectError("Missing/stale Case deletion --expect; review current deletion preview")
    receipt_id = f"{now().replace(':', '-')}-{uuid.uuid4().hex[:8]}"
    path = project.local_dir / "receipts" / f"{receipt_id}.json"
    relative = str(path.relative_to(project.root))
    receipt = {"id": receipt_id, "time": now(), "scope": scope, "plan": plan,
               "previous": {k: deepcopy(resources[k]) for k in keys}, "status": "pending"}
    save_json(path, receipt)
    for related in keys:
        resources[related].update(status="pending", delete_receipt=relative, scope=scope)
    project.save_state(state)
    try:
        receipt["response"] = api.delete_case(client, server_id)
        save_json(path, receipt)
        receipt["readback"] = delete_readback(client, server_id, scope)
        receipt["status"] = "retired" if receipt["readback"]["absent"] else "readback_mismatch"
        if receipt["status"] == "retired":
            retire_deleted(resources, keys)
        else:
            for related in keys:
                resources[related]["status"] = "readback_mismatch"
    except BaseException as exc:
        receipt.update(status="outcome_unknown", error=str(exc))
        for related in keys:
            resources[related]["status"] = "outcome_unknown"
        raise
    finally:
        save_json(path, receipt)
        project.save_state(state)
    return receipt


def reconcile_delete(project, client, state, key, scope, case_ids):
    """Resolve only a recorded deletion intent; never repeat DELETE during pull."""
    resources = state["resources"]
    entry = resources[key]
    relative = entry["delete_receipt"]
    path = (project.root / relative).resolve()
    if not path.is_relative_to(project.root):
        raise ProjectError("Deletion receipt must be within the project")
    receipt = read_json(path, {})
    plan = receipt.get("plan", {})
    sid = entry["server_id"]
    previous = receipt.get("previous", {})
    allowed = {key, "pairs:" + key.split(":", 1)[1]}
    if (not scope_matches(receipt.get("scope", {}), scope) or not scope_matches(plan.get("scope", {}), scope)
            or plan.get("operation") != "case_delete" or plan.get("resource") != key or plan.get("server_id") != sid
            or key not in previous or not set(previous).issubset(allowed)):
        raise ProjectError(f"Deletion receipt identity/scope mismatch: {key}")
    for related in previous:
        saved = resources.get(related, {})
        if saved.get("server_id") != sid or saved.get("delete_receipt") != relative or not scope_matches(saved.get("scope", {}), scope):
            raise ProjectError(f"Deletion mapping identity/scope mismatch: {related}")
    observation = delete_readback(client, sid, scope)
    if observation["absent"] != (sid not in case_ids):
        raise ProjectError("Case list and deletion readback disagree; query again before recovery")
    if observation["absent"]:
        retire_deleted(resources, previous)
    else:
        # The deletion did not take effect at this observation. Restore only the
        # saved checkpoints; the ordinary pull below reconciles current content.
        for related, saved in previous.items():
            resources[related] = {**saved, "last_delete_receipt": relative}
    receipt["reconciliation"] = {"at": now(), "status": "retired" if observation["absent"] else "reconciled_observation",
                                 "readback": observation}
    save_json(path, receipt)
    project.save_state(state)
