"""Offline, selected delivery evidence bundles; never deployment-state exports."""
import hashlib
import json
from pathlib import Path

from .project import ProjectError, fingerprint, now, read_json, save_json


def digest(content):
    return hashlib.sha256(content).hexdigest()


def verify(directory):
    root = Path(directory).resolve()
    manifest = read_json(root / "manifest.json")
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 1
            or not isinstance(manifest.get("files"), dict) or not isinstance(manifest.get("run_path"), str)
            or manifest.get("release_path") is not None and not isinstance(manifest["release_path"], str)):
        raise ProjectError("Invalid delivery manifest")
    gaps = list(manifest.get("gaps", []))
    def local_path(relative):
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ProjectError("Delivery reference escapes bundle")
        return path
    for relative, expected in manifest.get("files", {}).items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != expected:
            gaps.append(f"Missing or changed evidence: {relative}")
    run = read_json(local_path(manifest["run_path"]), {})
    release = read_json(local_path(manifest["release_path"]), {}) if manifest.get("release_path") else {}
    if not isinstance(run, dict) or not isinstance(release, dict):
        raise ProjectError("Invalid run/release evidence object")
    for relative, expected in run.get("input_files", {}).items():
        path = local_path(relative)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            gaps.append(f"Run input evidence missing or changed: {relative}")
        if run.get("evidence_contract_version") == 2 and relative.endswith("/inputs/resources.json") and path.is_file():
            resources = read_json(path, {})
            prefix = relative.removesuffix("resources.json")
            for kind in ("knowledge", "attachments"):
                for entry in resources.get(kind, {}).values():
                    for field in ("manifest", "faq_file"):
                        if entry.get(field):
                            required_path = local_path(str(Path(prefix) / entry[field]))
                            required = str(required_path.relative_to(root))
                            if required not in run.get("input_files", {}) or not required_path.is_file():
                                gaps.append(f"Required declared {field} input missing: {entry[field]}")
    if run and run.get("evidence_contract_version") != 2:
        return {"complete": False, "integrity": not gaps, "historical": True,
                "gaps": [*gaps, "Historical evidence grants no current clearance"],
                "run_id": run.get("id"), "release_id": release.get("id"),
                "verification": "Stored metadata and file integrity only; use the pinned old CLI for old evidence interpretation"}
    if run:
        from .evidence import pair_key, classify
        if fingerprint(run.get("snapshot", {})) != run.get("remote_fingerprint"):
            gaps.append("Remote snapshot fingerprint mismatch")
        allowed = [sid for trigger in run.get("triggers", []) for sid in trigger.get("response", {}).get("created_results", [])]
        rows = [r["result"] for r in run.get("results", []) if r.get("result")]
        requirements = {pair_key(p): p["variables"] for p in run.get("evidence_requirements", [])}
        thresholds = {pair_key(p): p["value"] for p in run.get("minimum_scores", [])}
        wanted = {pair_key(p) for p in run.get("planned_pairs", [])}
        actual = {(r.get("case_id") or r.get("evaluation_case_id"), r.get("evaluator_id")) for r in rows}
        if (not wanted or run.get("status") != "passed" or len(allowed) != len(set(allowed))
                or {r.get("id") for r in rows} != set(allowed) or len(rows) != len(allowed) or actual != wanted
                or any(r.get("agent_history_id") != run.get("history_id") for r in rows)
                or any(pair_key(o) != (o["result"].get("case_id") or o["result"].get("evaluation_case_id"), o["result"].get("evaluator_id"))
                       for o in run.get("results", []) if o.get("result"))
                or any(classify(r, requirements.get((r.get("case_id") or r.get("evaluation_case_id"), r.get("evaluator_id")), []), thresholds.get((r.get("case_id") or r.get("evaluation_case_id"), r.get("evaluator_id")), 1), run=run) != "passed" for r in rows)):
            gaps.append("Run lacks complete exact-ID passing results/evidence")
    else:
        gaps.append("Run is missing")
    if release:
        plan = release.get("plan", {})
        if plan.get("run", {}).get("fingerprint") != fingerprint(run):
            gaps.append("Release references another run revision")
        if any(plan.get(k) != run.get(k) for k in ("history_id", "revision", "remote_fingerprint")):
            gaps.append("Release/run identity mismatch")
        if release.get("status") not in ("published", "published_reconciled"):
            gaps.append("Publication has not been proven by readback")
        actual_history = release.get("actual_history_id") if release.get("status") == "published" else release.get("reconciliation", {}).get("actual_history_id")
        if actual_history != plan.get("history_id"):
            gaps.append("Publication readback does not prove the exact history")
        if plan.get("run", {}).get("id") != run.get("id") or not {pair_key(p) for p in plan.get("pairs", [])} <= {pair_key(p) for p in run.get("planned_pairs", [])}:
            gaps.append("Publication run or acceptance pair identity mismatch")
        if plan.get("scope") and plan["scope"] != run.get("snapshot", {}).get("scope"):
            gaps.append("Publication/run scope mismatch")
        audit_path = local_path(plan.get("audit", {}).get("path", ""))
        audit = read_json(audit_path, {}) if audit_path.is_file() else {}
        if not audit or fingerprint(audit) != plan.get("audit", {}).get("fingerprint"):
            gaps.append("Audit is missing or changed")
        else:
            if (audit.get("conclusion") != "pass" or any(audit.get(k) != run.get(k) for k in ("history_id", "revision", "remote_fingerprint"))
                    or not {pair_key(p) for p in plan.get("pairs", [])} <= {pair_key(p) for p in audit.get("pairs", [])}):
                gaps.append("Audit does not cover the exact version/content/pairs")
            report = (root / audit.get("report", "")).resolve()
            if not report.is_relative_to(root) or not report.is_file() or fingerprint(report.read_text()) != audit.get("report_fingerprint"):
                gaps.append("Audit report is missing or changed")
        acceptance = plan.get("acceptance", {})
        confirmation = acceptance.get("confirmation", {})
        if confirmation.get("scope_fingerprint") != fingerprint({k: v for k, v in acceptance.items() if k != "confirmation"}):
            gaps.append("Acceptance scope confirmation mismatch")
        source = (root / confirmation.get("source", "")).resolve()
        if not source.is_relative_to(root) or not source.is_file() or fingerprint(source.read_text()) != confirmation.get("source_fingerprint"):
            gaps.append("Acceptance confirmation source is missing or changed")
    else:
        gaps.append("No selected publication receipt")
    return {"complete": not gaps, "gaps": sorted(set(gaps)), "run_id": run.get("id"),
            "release_id": release.get("id"), "scope": run.get("snapshot", {}).get("scope"),
            "verification": "Offline file integrity and evidence identity; not live platform verification or authenticity"}


def export(project, run_id, release_id, out_dir):
    output = Path(out_dir).resolve()
    if output.exists():
        raise ProjectError("Use a fresh delivery directory; existing evidence is never overwritten")
    run_path = f"runs/{run_id}/run.json"
    run_source = project.resolve_path("run", run_path)
    if run_source.parent.parent != project.root / "runs":
        raise ProjectError("Invalid run ID")
    run = read_json(run_source)
    if not run:
        raise ProjectError("Unknown run")
    if run.get("evidence_contract_version") != 2:
        raise ProjectError("Historical run is read-only; retain its existing delivery bytes and use metadata/integrity inspection")
    if not project.owns_scope(run.get('snapshot', {}).get('scope')):
        raise ProjectError("Run is outside the selected deployment")
    selected = [p for p in project.release_paths() if read_json(p).get("id") == release_id] if release_id else []
    if release_id and len(selected) != 1:
        raise ProjectError("Unknown or ambiguous release ID")
    release = read_json(selected[0]) if selected else {}
    release_path = str(selected[0].relative_to(project.root)) if selected else None
    manifest = {"schema_version": 1, "exported_at": now(), "run_path": run_path, "release_path": release_path,
                "files": {}, "gaps": [], "state_exported": False}
    references = {run_path}
    references.update(run.get("input_files", {}))
    if release:
        references.add(release_path)
        plan = release.get("plan", {})
        references.add(plan.get("audit", {}).get("path", ""))
        audit = read_json(project.resolve_path("audit", plan.get("audit", {}).get("path", "")), {}) if plan.get("audit", {}).get("path") else {}
        references.add(audit.get("report", ""))
        references.add(plan.get("acceptance", {}).get("confirmation", {}).get("source", ""))
    # Include the captured run's local input snapshot and selected required reports.
    for reference in run.get("evidence_requirements", []):
        if reference.get("verification"):
            references.add(reference["verification"])
    from .portable import environment
    secret_values = [v.encode() for v in environment(project).values() if v and len(v) >= 8]
    contents = {}
    for relative in sorted(references):
        if not relative or Path(relative).parts[0] == ".codeer":
            manifest["gaps"].append(f"Missing or unsupported evidence reference: {relative}")
            continue
        source = project.resolve_path("delivery evidence", relative)
        if not source.is_file():
            manifest["gaps"].append(f"Missing evidence: {relative}")
            continue
        content = source.read_bytes()
        if any(value in content for value in secret_values):
            raise ProjectError("Selected evidence contains a resolved environment value; remove credentials from the source evidence before controlled export")
        contents[relative] = content
        manifest["files"][relative] = digest(content)
    output.mkdir(parents=True)
    for relative, content in contents.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    save_json(output / "manifest.json", manifest)
    result = verify(output)
    (output / "README.md").write_text("# Selected delivery evidence\n\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n\nOriginal results/traces require controlled sharing. This bundle does not contain .codeer deployment state or all trial runs.\n")
    return {**result, "path": str(output)}
