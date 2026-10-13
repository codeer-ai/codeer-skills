"""ID-bound KB additions. Existing file content cannot be replaced by this API."""
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from . import kb
from .project import ProjectError, fingerprint, now, read_json, save_json, scope_matches


def local_sources(project, entry):
    source = entry.get("source")
    if not source:
        return None  # Legacy bindings cannot assert source freshness.
    directory = (project.root / source["directory"]).resolve()
    selected = sorted(p for p in directory.glob(source["glob"]) if p.is_file())
    if any(not p.resolve().is_relative_to(directory) for p in selected):
        return None
    return {str(p.relative_to(directory)): fingerprint(p.read_bytes().hex()) for p in selected}


def verify_originals(client, entry, statuses):
    from .resource_exports import original
    if set(entry.get("local", {})) != set(entry.get("file_ids", {})):
        raise ProjectError("Original verification requires every uploaded file identity; inspect receipt or bind explicit file IDs")
    proofs = {}
    snapshots = {row.get("node_id") or row.get("id"): row.get("snapshot_object_id") for row in statuses}
    for name, sid in entry["file_ids"].items():
        metadata = client.get(f"/external/knowledge-bases/files/{sid}")
        snapshot = metadata.get("snapshot_object_id")
        # files:status promises readiness, not a snapshot identity. Metadata owns
        # that identity; the download condition/header then pins the actual bytes.
        if (metadata.get("node_id") != sid or not snapshot
                or snapshots.get(sid) is not None and snapshot != snapshots[sid]):
            raise ProjectError("KB original metadata identity differs")
        content, receipt = original(client, metadata, node_id=sid)
        if fingerprint(content.hex()) != entry["local"][name]:
            raise ProjectError("Uploaded KB original bytes differ from the staged proposal")
        proofs[name] = receipt
    entry["original_verification"] = proofs


def reconcile(project, client, key, entry, scope, args):
    receipt = read_json(project.root / entry.get("receipt", ""), {}) if entry.get("receipt") else {}
    plan = receipt.get("plan", {})
    saved_scope = entry.get("scope") or plan.get("scope")
    if not saved_scope or not scope_matches(saved_scope, scope, allow_unbound_agent=True):
        raise ProjectError("KB recovery requires the saved API/workspace/Agent scope")
    # Recover older receipts and a crash between response and state persistence.
    returned_ids = [n["node_id"] for n in receipt.get("response", {}).get("nodes", []) if n.get("node_id")]
    if returned_ids and len(returned_ids) == len(plan.get("upload_files", [])) and len(set(returned_ids)) == len(returned_ids):
        entry.update(upload_complete=True, node_ids=sorted(set(entry.get("node_ids", [])) | set(returned_ids)),
                     server_id=entry.get("server_id") or receipt.get("kb_id") or plan.get("kb_id"),
                     local=plan.get("local", entry.get("local", {})))
    if not entry.get("upload_complete") or not entry.get("server_id") or not entry.get("node_ids"):
        raise ProjectError("Upload identity is incomplete; inspect receipt and verify missing file IDs before retry. Root identity alone cannot prove file creation.")
    entry["scope"] = saved_scope
    if not entry.get("source"):
        directory = Path(args.dir).resolve()
        source = {"directory": str(directory.relative_to(project.root)) if directory.is_relative_to(project.root) else str(directory), "glob": args.glob}
        if local_sources(project, {"source": source}) == entry.get("local"):
            entry["source"] = source
    ws, org = client.resolve_scope()
    statuses = kb.file_status(client, organization_id=org, workspace_id=ws, node_ids=entry["node_ids"])
    ready = {s.get("node_id") or s.get("id") for s in statuses} == set(entry["node_ids"]) and all(str(s.get("status")).upper() == "READY" for s in statuses)
    if ready and project.portable:
        if not entry.get("file_ids"):
            by_name = {Path(name).name: name for name in plan.get("upload_files", [])}
            entry["file_ids"] = {by_name[n["original_name"]]: n["node_id"] for n in receipt.get("response", {}).get("nodes", []) if n.get("original_name") in by_name and n.get("node_id")}
        verify_originals(client, entry, statuses)
    entry.update(status="ready" if ready else "not_ready", base=statuses)
    receipt.update(reconciled_at=now(), status=entry["status"], statuses=statuses)
    save_json(project.root / entry["receipt"], receipt)
    state = project.state()
    state["resources"][key] = entry
    state["queried_at"] = now()
    project.save_state(state)
    return {"resource": key, "kb_id": entry["server_id"], "status": entry["status"], "statuses": statuses, "read_only": True}


def upload(project, client, args):
    # Private staging is removed on success, errors and interruption. Hash and
    # multipart content use the same read, even if source files change in flight.
    with TemporaryDirectory(prefix="codeer-kb-") as directory:
        return _upload(project, client, args, Path(directory))


def _upload(project, client, args, staged_directory):
    ws, org = client.resolve_scope()
    scope = project.check_scope(client)
    local_id = args.local_id
    if not local_id:
        raise ProjectError("Project KB upload requires --local-id (stable local identity)")
    key = f"kb:{local_id}"
    state = project.state()
    entry = state.setdefault("resources", {}).get(key, {})
    if entry.get("scope") and not scope_matches(entry["scope"], scope, allow_unbound_agent=True):
        raise ProjectError("KB mapping scope differs from saved receipt")
    sid = entry.get("server_id") or args.kb_id
    if args.kb_id and sid != args.kb_id:
        raise ProjectError("KB ID differs from saved binding")
    if getattr(args, "reconcile", False):
        return reconcile(project, client, key, entry, scope, args)
    if entry.get("status") in ("pending", "outcome_unknown"):
        raise ProjectError("Inspect the previous upload receipt and reconcile returned node IDs before retrying")
    directory = Path(args.dir).resolve()
    source = {"directory": str(directory.relative_to(project.root)) if directory.is_relative_to(project.root) else str(directory), "glob": args.glob}
    if project.portable:
        from .portable import definitions
        if (project.target.get("intent") != "create" or project.target.get("agent_id")) and not entry and not getattr(args, "new", False):
            raise ProjectError("Map an existing KB with kb bind, or explicitly review a --new upload; missing state cannot create a replacement")
        definition = definitions(project).get("knowledge", {}).get(local_id)
        if not definition or source != {k: definition[k] for k in ("directory", "glob")}:
            raise ProjectError("Portable KB upload must match resources.json directory/glob for this local ID")
    if entry.get("source") and entry["source"] != source:
        raise ProjectError("KB source directory/glob differs from binding; use a separate stable local ID for a different selection")
    files = sorted(p for p in directory.glob(args.glob) if p.is_file())
    if not files:
        raise ProjectError("No upload files")
    if any(not p.resolve().is_relative_to(directory) for p in files):
        raise ProjectError("KB source symlink escapes selected directory")
    if len({p.name for p in files}) != len(files):
        raise ProjectError("Upload flattens selected files into one parent; use unique basenames")
    remote = kb.list_nodes(client, organization_id=org, workspace_id=ws, parent_id=sid) if sid else []
    local = {}
    staged = {}
    for path in files:
        name = str(path.relative_to(directory))
        content = path.read_bytes()
        local[name] = fingerprint(content.hex())
        if not args.dry_run:
            staged[name] = staged_directory / path.name
            staged[name].write_bytes(content)
    prior = entry.get("local", {})
    missing = sorted(set(prior) - set(local))
    changed = {name: digest for name, digest in local.items() if prior.get(name) != digest}
    if not changed and not missing and sid:
        entry.update(source=source, scope=scope)
        state["resources"][key] = entry
        ids = entry.get("node_ids", [])
        statuses = kb.file_status(client, organization_id=org, workspace_id=ws, node_ids=ids) if ids else []
        ready = bool(ids) and {s.get("node_id") or s.get("id") for s in statuses} == set(ids) and all(str(s.get("status")).upper() == "READY" for s in statuses)
        if ready and project.portable:
            verify_originals(client, entry, statuses)
        entry.update(status="ready" if ready else "not_ready", base=statuses)
        if entry.get("receipt"):
            path = project.root / entry["receipt"]
            receipt = read_json(path, {})
            receipt.update(status=entry["status"], statuses=statuses, readiness_checked_at=now())
            save_json(path, receipt)
        project.save_state(state)
        return {"status": entry["status"], "content_unchanged": True, "kb_id": sid, "statuses": statuses}
    # Upload always creates new file nodes; existing names cannot mean replace.
    existing_names = {n.get("name") or n.get("original_name") for n in remote}
    overlap = {name for name in changed if name in prior or Path(name).name in existing_names}
    plan = {"resource": key, "kb_id": sid, "scope": scope, "source": source, "local": local, "remote": remote,
            "operation": "add_file_nodes" if sid else "create_kb_and_add_files", "upload_files": sorted(changed),
            "unsupported_replacements": sorted(overlap),
            "missing_sources": missing,
            "limitation": "No supported in-place content replacement; replacement requires explicit new nodes and reviewed Agent/FAQ reference changes."}
    if project.portable:
        plan["operator"] = project.preview_identity(client)
        plan["new"] = getattr(args, "new", False)
    plan["token"] = fingerprint(plan)
    if args.dry_run:
        return plan
    if overlap:
        raise ProjectError("In-place replacement unsupported; use separate new files/nodes and review references")
    if missing:
        raise ProjectError("Managed local KB sources are missing; restore them or review a separate binding/reference change. No remote deletion is implied.")
    if args.expect != plan["token"]:
        raise ProjectError("Missing or stale --expect; review KB dry-run")
    receipt_path = project.local_dir / "receipts" / f"kb-{now().replace(':', '-')}.json"
    receipt = {"plan": plan, "status": "pending"}
    entry.update(status="pending", receipt=str(receipt_path.relative_to(project.root)), source=source, scope=scope, upload_complete=False)
    state["resources"][key] = entry
    project.save_state(state)
    save_json(receipt_path, receipt)
    try:
        if not sid:
            result = kb.create_kb(client, organization_id=org, workspace_id=ws, name=args.name, description=args.description)
            sid = result.get("id") or result.get("node_id")
            entry["server_id"] = sid
            project.save_state(state)
        response = kb.upload_files(client, organization_id=org, workspace_id=ws, kb_id=sid,
                                   parent_id=sid, file_paths=[str(staged[name]) for name in sorted(changed)])
        receipt["response"] = response
        save_json(receipt_path, receipt)
        ids = [n["node_id"] for n in response.get("nodes", []) if n.get("node_id")]
        entry.update(server_id=sid, node_ids=sorted(set(entry.get("node_ids", [])) | set(ids)), local={**prior, **local})
        by_name = {Path(name).name: name for name in changed}
        file_ids = {by_name[n["original_name"]]: n["node_id"] for n in response.get("nodes", []) if n.get("original_name") in by_name and n.get("node_id")}
        entry.setdefault("file_ids", {}).update(file_ids)
        entry["upload_complete"] = len(ids) == len(changed) and len(set(ids)) == len(ids)
        project.save_state(state)
        if not entry["upload_complete"]:
            raise ProjectError("Upload returned incomplete/duplicate identities; reconcile missing file IDs before retry")
        deadline = time.monotonic() + args.poll_timeout
        statuses = []
        while ids:
            statuses = kb.file_status(client, organization_id=org, workspace_id=ws, node_ids=ids)
            if len(statuses) == len(ids) and all(str(s.get("status")).upper() in ("READY", "FAILED", "ERROR") for s in statuses):
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(3)
        ready = bool(ids) and {s.get("node_id") or s.get("id") for s in statuses} == set(ids) and all(str(s.get("status")).upper() == "READY" for s in statuses)
        if ready and project.portable:
            verify_originals(client, entry, statuses)
        receipt.update(status="ready" if ready else "not_ready", statuses=statuses, kb_id=sid,
                       original_verification=entry.get("original_verification", {}))
        entry.update(status=receipt["status"], base=statuses)
    except BaseException as exc:
        receipt.update(status="outcome_unknown", error=str(exc), kb_id=sid)
        entry["status"] = "outcome_unknown"
        raise
    finally:
        save_json(receipt_path, receipt)
        project.save_state(state)
    return receipt


def record_export(project, result):
    state = project.state()
    state.setdefault("kb_exports", {})[result["node_id"]] = {"time": now(), "manifest": result}
    state["queried_at"] = now()
    project.save_state(state)


def bind(project, client, local_id, kb_id, files, *, choice, dry_run, expected):
    """Explicit file-ID takeover. A Markdown snapshot never proves PDF identity."""
    from .portable import definitions
    if not project.portable:
        raise ProjectError("KB takeover mapping requires a portable project")
    definition = definitions(project).get("knowledge", {}).get(local_id)
    if not definition or not isinstance(files, dict) or not files:
        raise ProjectError("Declare the KB in resources.json and supply relative-file → node-ID JSON")
    scope = project.check_scope(client)
    source = {k: definition[k] for k in ("directory", "glob")}
    directory = project.resolve_path("knowledge", source["directory"])
    local = local_sources(project, {"source": source})
    if set(files) != set(local or {}) or len(set(files.values())) != len(files):
        raise ProjectError("Map each selected source exactly once; duplicate or missing node IDs are ambiguous")
    state = project.state()
    key = f"kb:{local_id}"
    entry = state.get("resources", {}).get(key, {})
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
        raise ProjectError("Reconcile the previous KB operation before takeover")
    if entry.get("server_id") and (entry["server_id"] != kb_id or entry.get("file_ids") != files):
        raise ProjectError("Mapping differs from the tracked KB; inspect the original mapping")
    ws, org = client.resolve_scope()
    pending, seen, descendants = [kb_id], set(), set()
    while pending:
        parent = pending.pop()
        if parent in seen:
            raise ProjectError("Cycle in KB tree")
        seen.add(parent)
        for row in kb.list_nodes(client, organization_id=org, workspace_id=ws, parent_id=parent):
            sid = row.get("id") or row.get("node_id")
            descendants.add(sid)
            if str(row.get("node_type") or row.get("type")).upper() == "FOLDER":
                pending.append(sid)
    if not set(files.values()) <= descendants:
        raise ProjectError("Mapped file is absent from the explicitly selected KB")
    from .resource_exports import knowledge, original as read_original
    exported = {path: knowledge(client, sid) for path, sid in files.items()}
    remote = {path: row["snapshot"] for path, row in exported.items()}
    downloads = {path: read_original(client, exported[path]["metadata"], node_id=sid) for path, sid in files.items()}
    originals = {path: value[0] for path, value in downloads.items()}
    proofs = {path: value[1] for path, value in downloads.items()}
    comparison = {}
    for path, observation in remote.items():
        text = observation.get("content")
        original = (directory / path).read_bytes()
        equal = original == originals[path]
        comparison[path] = {"state": "aligned" if equal else "pending_apply" if choice == "local" else "undecided",
                            "snapshot_available": text is not None, "original_bytes_verified": equal}
    plan = {"resource": key, "scope": scope, "kb_id": kb_id, "files": files, "source": source,
            "local": local, "remote": remote, "original_verification": proofs, "comparison": comparison, "choice": choice}
    plan["operator"] = project.preview_identity(client)
    plan["token"] = fingerprint({**plan, "original_verification": {name: {k: v for k, v in proof.items() if k != "downloaded_at"}
                                                               for name, proof in proofs.items()}})
    if dry_run:
        return plan
    if expected != plan["token"] or choice not in ("local", "remote"):
        raise ProjectError("Review the current KB mapping with a choice and --expect")
    statuses = kb.file_status(client, organization_id=org, workspace_id=ws, node_ids=list(files.values()))
    snapshots = {sid: exported[path]["snapshot"]["snapshot_object_id"] for path, sid in files.items()}
    if any(row.get("snapshot_object_id") is not None and row["snapshot_object_id"] != snapshots.get(row.get("node_id") or row.get("id")) for row in statuses):
        raise ProjectError("KB snapshot changed after original export; review a fresh mapping")
    for path, sid in files.items():
        knowledge(client, sid, expected=exported[path]["export_revision"])
    if choice == "remote":
        if any(Path(p).suffix.lower() not in (".md", ".txt") or not isinstance(remote[p].get("content"), str) for p in files):
            raise ProjectError("Remote API supplies text only; retain binary originals and import a separate Markdown snapshot explicitly")
        if any(originals[p] != remote[p]["content"].encode("utf-8") for p in files):
            raise ProjectError("Saved text differs from original bytes; use kb import to preserve both separately")
        # The write boundary precedes baseline changes; byte writes preserve CRLF.
        previous = {path: (directory / path).read_bytes() for path in files}
        try:
            for path in files:
                (directory / path).write_bytes(originals[path])
        except BaseException:
            for path, content in previous.items():
                (directory / path).write_bytes(content)
            raise
        local = local_sources(project, {"source": source})
        if any((directory / path).read_bytes() != remote[path]["content"].encode() for path in files):
            raise ProjectError("Local KB write verification failed; bases unchanged")
        for path in files:
            comparison[path].update(state="aligned", original_bytes_verified=True)
    aligned = {path: local[path] for path in files if choice == "remote" or comparison[path]["state"] == "aligned"}
    ready = {r.get("node_id") or r.get("id") for r in statuses} == set(files.values()) and all(str(r.get("status")).upper() == "READY" for r in statuses)
    entry.update(server_id=kb_id, file_ids=files, node_ids=list(files.values()), source=source, local=aligned,
                 base=statuses, status="ready" if ready else "not_ready", scope=scope, tracked_at=now(),
                 snapshot_fingerprints={p: fingerprint(v) for p, v in remote.items()}, alignment=comparison,
                 original_verification=proofs, limitation="No in-place content replacement; originals and text stay separate")
    state.setdefault("resources", {})[key] = entry
    save_json(project.local_dir / "imports" / f"kb-{now().replace(':', '-')}.json", plan)
    project.save_state(state)
    return {"resource": key, "comparison": comparison, "remote_mutations": 0,
            "original_backup_complete": all(row["original_bytes_verified"] for row in comparison.values())}
