"""Version-bound remote snapshots, run identities and publication evidence."""
from collections import Counter
from pathlib import Path
import time
import uuid

from . import agents, eval_ as api, kb
from .project import ProjectError, fingerprint, now, read_json, save_json
from .project_agent import local_settings, writable
from .project_eval import CASE_FIELDS, TESTER_FIELDS, select, validate_design


def pair_key(pair):
    return pair["case_id"], pair["evaluator_id"]


def snapshot(project, client, history_id):
    scope = project.check_scope(client)
    aid = scope["agent_id"]
    history = agents.get_version(client, aid, history_id)
    if history.get("agent_id") not in (None, aid):
        raise ProjectError("History belongs to another Agent")
    version_settings = writable(history)
    runtime = {}
    if "use_search" not in version_settings:
        runtime["use_search"] = agents.get(client, aid).get("use_search")
        version_settings["use_search"] = runtime["use_search"]
    cases = api.list_cases(client, aid)
    infos = api.get_case_evaluator_infos(client, case_ids=[c["id"] for c in cases]) if cases else []
    tester_ids = sorted({e["evaluator_id"] for row in infos for e in row.get("evaluators", [])})
    testers = {tid: select(api.get_evaluator(client, tid), TESTER_FIELDS) for tid in tester_ids}
    pairs = [{"case_id": row["case_id"], "evaluator_id": e["evaluator_id"], "rubric": e.get("rubric", "")} for row in infos for e in row.get("evaluators", [])]
    nodes = agents.referenced_knowledge_nodes(history.get("unified_tools"))
    kb_state = {}
    ws, org = client.resolve_scope()
    for node_id in sorted(nodes):
        children = kb.list_nodes(client, workspace_id=ws, organization_id=org, parent_id=node_id)
        file_ids = [n.get("id") or n.get("node_id") for n in children if str(n.get("node_type") or n.get("type")).upper() == "FILE"]
        # Folder traversal is explicit, preserving IDs and every snapshot/status.
        pending = [n.get("id") or n.get("node_id") for n in children if str(n.get("node_type") or n.get("type")).upper() == "FOLDER"]
        seen = {node_id}
        while pending:
            folder = pending.pop()
            if folder in seen:
                raise ProjectError("Cycle in KB references")
            seen.add(folder)
            children = kb.list_nodes(client, workspace_id=ws, organization_id=org, parent_id=folder)
            file_ids.extend(n.get("id") or n.get("node_id") for n in children if str(n.get("node_type") or n.get("type")).upper() == "FILE")
            pending.extend(n.get("id") or n.get("node_id") for n in children if str(n.get("node_type") or n.get("type")).upper() == "FOLDER")
        # A direct file reference also works with files:status.
        statuses = kb.file_status(client, workspace_id=ws, organization_id=org, node_ids=file_ids or [node_id])
        faqs = {}
        for status in statuses:
            snapshot_id = status.get("snapshot_object_id")
            if snapshot_id is not None:
                offset = 0
                entries = []
                while True:
                    page = kb.list_context_obj_faqs(client, context_object_id=snapshot_id, limit=200, offset=offset)
                    rows = page if isinstance(page, list) else page.get("items", page.get("data", []))
                    entries.extend(rows)
                    if len(rows) < 200:
                        break
                    offset += 200
                faqs[str(snapshot_id)] = entries
        kb_state[node_id] = {"expected_file_ids": file_ids or [node_id], "statuses": statuses, "faqs": faqs}
    data = {"scope": scope, "history_id": history_id, "agent": version_settings, "current_runtime": runtime,
            "cases": {c["id"]: select(c, CASE_FIELDS) for c in cases}, "testers": testers,
            "pairs": sorted(pairs, key=pair_key), "kb": kb_state,
            "limits": ["Current KB/Rubric/Tester state; no server transaction or fixed external tool state", "History API omits use_search; current runtime value is explicitly observed when needed", "Fingerprint is configuration identity, not proof of reproducibility"]}
    result = {"revision": project.revision(), "remote_fingerprint": fingerprint(data), "snapshot": data}
    state = project.state()
    state.update(last_anchor=result, queried_at=now())
    project.save_state(state)
    return result


def audit_matches(project, audit, anchor, pairs, *, remote=True):
    """Pure validity predicate shared by offline status and online clearance."""
    if not isinstance(audit, dict) or not anchor.get("snapshot"):
        return False
    try:
        covered = {pair_key(p) for p in audit.get("pairs", [])}
        report = (project.root / audit.get("report", "")).resolve()
        return (audit.get("schema_version") == 1 and audit.get("conclusion") == "pass"
                and audit.get("revision") == anchor["revision"]
                and (not remote or audit.get("remote_fingerprint") == anchor["remote_fingerprint"])
                and audit.get("history_id") == anchor["snapshot"]["history_id"]
                and {pair_key(p) for p in pairs} <= covered
                and report.is_relative_to(project.root) and report.is_file()
                and audit.get("report_fingerprint") == fingerprint(report.read_text(encoding="utf-8")))
    except (KeyError, TypeError, OSError, ValueError):
        return False


def valid_audit(project, anchor, pairs):
    for path in sorted((project.root / "reviews").glob("*.audit.json"), reverse=True):
        audit = read_json(path)
        if audit_matches(project, audit, anchor, pairs):
            return {"path": str(path.relative_to(project.root)), "fingerprint": fingerprint(audit)}
    raise ProjectError("Missing or stale semantic audit for this revision, exact history and pair scope")


def ensure_ready(project, anchor):
    issues = project.validate()
    design = read_json(project.path("evals"))
    validation = validate_design(design, project.state(), project.root)
    if issues or not validation["apply_ready"]:
        raise ProjectError(f"Unresolved local design/resources: {issues or validation['unresolved']}")
    from .sync import effective_change
    from .project_kb import local_sources
    resources = project.state().get("resources", {})
    if effective_change(resources.get("agent", {}), "agent", local_settings(project), anchor["snapshot"]["agent"]):
        raise ProjectError("Local Agent changes are not applied to this exact history")
    referenced = set(anchor["snapshot"]["kb"])
    referenced.update(sid for resource in anchor["snapshot"]["kb"].values() for sid in resource["expected_file_ids"])
    for key, entry in resources.items():
        if key.startswith("kb:") and referenced.intersection({entry.get("server_id"), *entry.get("node_ids", [])}) and local_sources(project, entry) != entry.get("local", {}):
            raise ProjectError(f"Managed KB has local unapplied changes or missing source binding: {key}")
    for resource in anchor["snapshot"]["kb"].values():
        statuses = resource["statuses"]
        actual = {s.get("node_id") or s.get("id") for s in statuses}
        if actual != set(resource["expected_file_ids"]) or any(str(s.get("status")).upper() != "READY" for s in statuses):
            raise ProjectError("KB readiness is missing or not READY")
    remote_pairs = {pair_key(p): p.get("rubric", "") for p in anchor["snapshot"]["pairs"]}
    for tester in design["testers"]:
        sid = resources.get(f"tester:{tester['local_id']}", {}).get("server_id")
        key = f"tester:{tester['local_id']}"
        if not sid or sid not in anchor["snapshot"]["testers"] or effective_change(resources.get(key, {}), key, select(tester, TESTER_FIELDS), anchor["snapshot"]["testers"][sid]):
            raise ProjectError(f"Tester changes not applied: {tester['local_id']}")
    for case in design["cases"]:
        sid = resources.get(f"case:{case['local_id']}", {}).get("server_id")
        key = f"case:{case['local_id']}"
        if not sid or sid not in anchor["snapshot"]["cases"] or effective_change(resources.get(key, {}), key, select(case, CASE_FIELDS), anchor["snapshot"]["cases"][sid]):
            raise ProjectError(f"Case changes not applied: {case['local_id']}")
        for pair in case["pairs"]:
            tid = resources.get(f"tester:{pair['tester']}", {}).get("server_id")
            key = f"pairs:{case['local_id']}"
            if not tid or effective_change(resources.get(key, {}), key, {tid: pair["rubric"]}, {t: rubric for (c, t), rubric in remote_pairs.items() if c == sid}):
                raise ProjectError(f"Pair changes not applied: {case['local_id']}/{pair['tester']}")
        for tid in case.get("remove_tester_ids", []):
            if (sid, tid) in remote_pairs or tid not in resources.get(f"pairs:{case['local_id']}", {}).get("removed_ids", []):
                raise ProjectError(f"Pair removal not applied: {case['local_id']}/{tid}")


def required_evidence(project):
    design = read_json(project.path("evals"), {})
    resources = project.state().get("resources", {})
    requirements = {}
    for case in design.get("cases", []):
        sid = resources.get(f"case:{case['local_id']}", {}).get("server_id")
        for pair in case.get("pairs", []):
            tid = resources.get(f"tester:{pair['tester']}", {}).get("server_id")
            requirements[(sid, tid)] = pair.get("required_evidence", [])
    return requirements


def thresholds(project):
    acceptance = read_json(project.path("acceptance"), {})
    resources = project.state().get("resources", {})
    result = {}
    for pair in acceptance.get("pairs", []):
        threshold = pair.get("minimum_score", 1.0)
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
            raise ProjectError("Acceptance minimum_score must be between 0 and 1")
        key = (resources.get(f"case:{pair['case']}", {}).get("server_id"), resources.get(f"tester:{pair['tester']}", {}).get("server_id"))
        result[key] = threshold
    return result


def classify(row, required, minimum_score=1.0):
    if not row:
        return "missing"
    status = str(row.get("status", "")).lower()
    if status in ("failed", "error", "cancelled", "canceled"):
        return "error"
    if status not in ("finished", "completed", "success"):
        return "missing"
    for variable in required:
        # Empty reasoning_steps is observable absence of calls, unlike missing data.
        field = {"tool_steps": "reasoning_steps", "output": "output"}.get(variable)
        if not field or row.get(field) is None:
            return "unjudgeable"
    score = row.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1:
        return "unjudgeable"
    return "passed" if score >= minimum_score else "failed"


def run(project, client, args):
    history_id = args.history or agents.get_latest_history_id(client, args.agent)
    if not history_id:
        raise ProjectError("Agent has no version to evaluate")
    for path in (project.root / "runs").glob("*/run.json"):
        previous = read_json(path)
        if previous.get("history_id") == history_id and previous.get("status") in ("triggering", "polling", "outcome_unknown"):
            raise ProjectError(f"Previous run {previous['id']} is unresolved; eval export --run-id before another trigger")
    anchor = snapshot(project, client, history_id)
    ensure_ready(project, anchor)
    selected_cases = set(args.cases.split(",")) if args.cases else None
    selected_testers = set((args.evaluator or args.evaluators).split(",")) if (args.evaluator or args.evaluators) else None
    pairs = [p for p in anchor["snapshot"]["pairs"] if (selected_cases is None or p["case_id"] in selected_cases) and (selected_testers is None or p["evaluator_id"] in selected_testers)]
    if not pairs:
        raise ProjectError("No assigned pairs selected")
    audit = valid_audit(project, anchor, pairs)
    run_id = f"{now().replace(':', '-')}-{uuid.uuid4().hex[:8]}"
    path = project.root / "runs" / run_id / "run.json"
    record = {"schema_version": 1, "id": run_id, "started_at": now(), "history_id": history_id,
              **anchor, "audit": audit, "planned_pairs": pairs, "triggers": [], "results": [], "status": "triggering"}
    save_json(path, record)
    if getattr(args, "out", None):
        save_json(args.out, record)
    allowed = set()
    skipped = set()
    requirements = required_evidence(project)
    minimum_scores = thresholds(project)
    record["evidence_requirements"] = [{"case_id": k[0], "evaluator_id": k[1], "variables": v} for k, v in requirements.items()]
    record["minimum_scores"] = [{"case_id": k[0], "evaluator_id": k[1], "value": v} for k, v in minimum_scores.items()]
    save_json(path, record)
    ws, _ = client.resolve_scope()
    grouped = {}
    for p in pairs:
        grouped.setdefault(p["evaluator_id"], []).append(p["case_id"])
    try:
        for tid, cids in grouped.items():
            response = api.trigger(client, case_ids=cids, evaluator_ids=[tid], agent_history_id=history_id)
            record["triggers"].append({"evaluator_id": tid, "case_ids": cids, "response": response})
            allowed.update(response.get("created_results", []))
            skipped.update((p["case_id"], p["evaluator_id"]) for p in response.get("skipped_pairs", []))
            save_json(path, record)
        record["status"] = "polling"
        deadline = time.monotonic() + args.poll_timeout
        rows = {}
        anomalies = []
        while True:
            for tid, cids in grouped.items():
                fetched = api.get_results(client, case_ids=cids, evaluator_id=tid, agent_history_id=history_id, workspace_id=ws)
                for row in fetched:
                    key = (row.get("case_id") or row.get("evaluation_case_id"), row.get("evaluator_id"))
                    if row.get("id") not in allowed:
                        continue
                    if row.get("agent_history_id") != history_id or key not in {pair_key(p) for p in pairs} or key in skipped:
                        anomalies.append("result_identity_mismatch")
                        continue
                    if key in rows and rows[key].get("id") != row.get("id"):
                        anomalies.append("duplicate_pair_results")
                    rows[key] = row
            outcomes = [{"case_id": p["case_id"], "evaluator_id": p["evaluator_id"], "minimum_score": minimum_scores.get(pair_key(p), 1.0), "state": "skipped" if pair_key(p) in skipped else classify(rows.get(pair_key(p)), requirements.get(pair_key(p), []), minimum_scores.get(pair_key(p), 1.0)), "result": rows.get(pair_key(p))} for p in pairs]
            record.update(results=outcomes, counts=dict(Counter(r["state"] for r in outcomes)), result_ids=sorted(allowed), anomalies=sorted(set(anomalies)))
            save_json(path, record)
            if all(r["state"] != "missing" for r in outcomes) or time.monotonic() >= deadline:
                break
            time.sleep(3)
        exact = len(allowed) == len(pairs) - len(skipped) and {r["result"]["id"] for r in outcomes if r["result"]} == allowed
        record["status"] = "passed" if exact and not anomalies and all(r["state"] == "passed" for r in outcomes) else "incomplete" if any(r["state"] in ("missing", "unjudgeable", "skipped") for r in outcomes) or not exact else "failed"
        # Detect edits during execution; fingerprints do not freeze server state.
        end_anchor = snapshot(project, client, history_id)
        if end_anchor["remote_fingerprint"] != anchor["remote_fingerprint"] or project.revision() != anchor["revision"]:
            record["status"] = "stale"
        record["finished_at"] = now()
    except BaseException as exc:
        record.update(status="outcome_unknown", error=str(exc))
        raise
    finally:
        save_json(path, record)
        if getattr(args, "out", None):
            save_json(args.out, record)
    return {"id": run_id, "history_id": history_id, "status": record["status"], "counts": record.get("counts"), "path": str(path)}


def publication_plan(project, client, history_id):
    anchor = snapshot(project, client, history_id)
    ensure_ready(project, anchor)
    acceptance = read_json(project.path("acceptance"))
    if not isinstance(acceptance, dict) or not acceptance.get("pairs") or not acceptance.get("confirmation"):
        raise ProjectError("Define confirmed acceptance.json with stable case/tester pairs before publication")
    confirmation = acceptance["confirmation"]
    source = (project.root / confirmation.get("source", "")).resolve()
    content = {k: v for k, v in acceptance.items() if k != "confirmation"}
    if (not source.is_relative_to(project.root) or not source.is_file()
            or confirmation.get("source_fingerprint") != fingerprint(source.read_text(encoding="utf-8"))
            or confirmation.get("scope_fingerprint") != fingerprint(content)):
        raise ProjectError("Acceptance confirmation must reference the reviewed content and source fingerprints")
    resources = project.state().get("resources", {})
    pairs = [{"case_id": resources.get(f"case:{p['case']}", {}).get("server_id"), "evaluator_id": resources.get(f"tester:{p['tester']}", {}).get("server_id")} for p in acceptance["pairs"]]
    if any(None in pair_key(p) for p in pairs) or len({pair_key(p) for p in pairs}) != len(pairs):
        raise ProjectError("Unknown or duplicate acceptance pair IDs")
    audit = valid_audit(project, anchor, pairs)
    wanted = {pair_key(p) for p in pairs}
    selected = None
    for path in sorted((project.root / "runs").glob("*/run.json"), reverse=True):
        record = read_json(path)
        if (record.get("status") == "passed" and record.get("history_id") == history_id and record.get("revision") == anchor["revision"] and record.get("remote_fingerprint") == anchor["remote_fingerprint"] and wanted <= {pair_key(p) for p in record.get("planned_pairs", [])}):
            selected = {"path": str(path.relative_to(project.root)), "fingerprint": fingerprint(record), "id": record["id"]}
            break
    if not selected:
        raise ProjectError("No current passing run covers the confirmed acceptance set for this exact history")
    plan = {"history_id": history_id, "revision": anchor["revision"], "remote_fingerprint": anchor["remote_fingerprint"], "audit": audit, "run": selected, "acceptance": acceptance, "pairs": pairs}
    plan["token"] = fingerprint(plan)
    return plan


def publish(project, client, history_id, *, dry_run, expected, reconcile=False):
    unresolved = []
    for path in (project.root / "releases").glob("*/release.json"):
        record = read_json(path)
        if record.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
            unresolved.append((path, record))
    if reconcile:
        actual = agents.get(client, project.target["agent_id"])
        for path, record in unresolved:
            record.update(status="published_reconciled" if actual.get("publish_history_id") == record["plan"]["history_id"] else "reconciled_observation",
                          reconciliation={"time": now(), "actual_history_id": actual.get("publish_history_id"), "limitation": "Current observation cannot prove prior publication sequence"})
            save_json(path, record)
        return {"status": "reconciled", "observed_history_id": actual.get("publish_history_id"), "remote_mutations": 0}
    if unresolved:
        raise ProjectError("Previous publication unresolved; publish --reconcile to read back before retry")
    plan = publication_plan(project, client, history_id)
    if dry_run:
        return plan
    if expected != plan["token"]:
        raise ProjectError("Missing or stale publication --expect token")
    if publication_plan(project, client, history_id)["token"] != expected:
        raise ProjectError("Publication evidence changed during preflight")
    rid = f"{now().replace(':', '-')}-{uuid.uuid4().hex[:8]}"
    path = project.root / "releases" / rid / "release.json"
    record = {"id": rid, "time": now(), "plan": plan, "status": "pending"}
    save_json(path, record)
    try:
        record["response"] = agents.publish_version(client, project.target["agent_id"], history_id)
        save_json(path, record)
        actual = agents.get(client, project.target["agent_id"])
        record["actual_history_id"] = actual.get("publish_history_id")
        record["status"] = "published" if record["actual_history_id"] == history_id else "readback_mismatch"
    except BaseException as exc:
        record.update(status="outcome_unknown", error=str(exc))
        raise
    finally:
        save_json(path, record)
    return record


def export_run(project, client, run_id, out_dir):
    root = (project.root / "runs" / run_id).resolve()
    if root.parent != (project.root / "runs").resolve():
        raise ProjectError("Invalid run ID")
    path = root / "run.json"
    record = read_json(path)
    if not record:
        raise ProjectError("Unknown run ID")
    update_record = record.get("status") not in ("passed", "failed", "stale")
    project.check_scope(client)
    anchor = snapshot(project, client, record["history_id"])
    if anchor["snapshot"]["scope"] != record["snapshot"]["scope"]:
        raise ProjectError("Run scope differs from project")
    allowed = {rid for t in record["triggers"] for rid in t["response"].get("created_results", [])}
    skipped = {(p["case_id"], p["evaluator_id"]) for t in record["triggers"] for p in t["response"].get("skipped_pairs", [])}
    # The API exposes only the latest result per pair. Retain exact historical
    # evidence already captured; never substitute a newer run's row.
    rows = {}
    for outcome in record.get("results", []):
        row = outcome.get("result")
        if (row and row.get("id") in allowed and row.get("agent_history_id") == record["history_id"]
                and (row.get("case_id") or row.get("evaluation_case_id"), row.get("evaluator_id")) == pair_key(outcome)):
            rows[pair_key(outcome)] = row
    ws, _ = client.resolve_scope()
    anomalies = list(record.get("anomalies", []))
    planned = {pair_key(p) for p in record["planned_pairs"]}
    returned = set()
    for trigger in record["triggers"]:
        for row in api.get_results(client, case_ids=trigger["case_ids"], evaluator_id=trigger["evaluator_id"], agent_history_id=record["history_id"], workspace_id=ws):
            key = (row.get("case_id") or row.get("evaluation_case_id"), row.get("evaluator_id"))
            if row.get("id") not in allowed:
                continue
            returned.add(row["id"])
            if row.get("agent_history_id") != record["history_id"] or key not in planned or key in skipped:
                anomalies.append("result_identity_mismatch")
                continue
            if key in rows and rows[key]["id"] != row["id"]:
                anomalies.append("duplicate_pair_results")
            rows[key] = row
    requirements = {pair_key(p): p["variables"] for p in record.get("evidence_requirements", [])}
    minimum_scores = {pair_key(p): p["value"] for p in record.get("minimum_scores", [])}
    outcomes = [{"case_id": p["case_id"], "evaluator_id": p["evaluator_id"], "minimum_score": minimum_scores.get(pair_key(p), 1.0), "state": "skipped" if pair_key(p) in skipped else classify(rows.get(pair_key(p)), requirements.get(pair_key(p), []), minimum_scores.get(pair_key(p), 1.0)), "result": rows.get(pair_key(p))} for p in record["planned_pairs"]]
    exact = bool(allowed) and len(allowed) == len(outcomes) - len(skipped) and {r["result"]["id"] for r in outcomes if r["result"]} == allowed
    status = "passed" if exact and not anomalies and all(r["state"] == "passed" for r in outcomes) else "incomplete" if not exact or any(r["state"] in ("missing", "unjudgeable", "skipped") for r in outcomes) else "failed"
    if anchor["remote_fingerprint"] != record["remote_fingerprint"] or anchor["revision"] != record["revision"]:
        status = "stale"
    if record["status"] == "outcome_unknown" and not exact:
        status = "outcome_unknown"
    record.update(status=status, results=outcomes, counts=dict(Counter(r["state"] for r in outcomes)), anomalies=anomalies, refreshed_at=now())
    record["refresh_observation"] = {"returned_exact_result_ids": sorted(returned), "exact_result_ids_not_returned": sorted(allowed - returned), "latest_only_api": True}
    # Completed evidence may already be fingerprinted by a release. Export's
    # refresh observation is a separate artifact; interrupted runs can resume.
    if update_record:
        save_json(path, record)
    output = Path(out_dir)
    export_path = output / f"{run_id}.json"
    save_json(export_path, record)
    return {"id": run_id, "status": status, "counts": record["counts"], "path": str(path),
            "export_path": str(export_path), "record_updated": update_record}
