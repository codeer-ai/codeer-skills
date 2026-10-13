"""Portable KB originals, saved text and FAQ definitions with explicit recovery."""
from copy import deepcopy
from pathlib import Path
import uuid

from . import agents, kb, resource_exports as exports
from .client import CodeerError
from .deployment import compare
from .portable import definitions
from .project import ProjectError, fingerprint, now, read_json, save_json, scope_matches

CRAWL_GAP = "website_crawl_settings_excluded"


def faq_value(row, content=None):
    ranges = []
    starts = [0] + [i + 1 for i, c in enumerate(content or "") if c == "\n"]
    for span in row.get("ranges") or []:
        normalized = {k: span.get(k, 0) for k in ("start_line", "start_column", "end_line", "end_column")}
        for edge in ("start", "end"):
            offset = span.get(edge + "_offset")
            if offset is None and isinstance(content, str):
                offset = starts[normalized[edge + "_line"] - 1] + normalized[edge + "_column"]
            normalized[edge + "_offset"] = offset
        normalized["text"] = span.get("text") or None
        ranges.append(normalized)
    return {"question": row["question"], "ranges": ranges}


def faq_id(row):
    return "faq-" + fingerprint(row["id"])[:12]


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema_version") != 1 or not isinstance(bundle.get("files"), dict):
        raise ProjectError("FAQ file requires schema_version 1 and files")
    for name, row in bundle["files"].items():
        if not isinstance(name, str) or not isinstance(row, dict) or set(row) != {"content", "faqs"}:
            raise ProjectError("FAQ file entries require exact saved content and faqs")
        text, faqs = row["content"], row["faqs"]
        if text is not None and not isinstance(text, str) or not isinstance(faqs, dict):
            raise ProjectError("Invalid saved text/FAQ collection")
        for lid, faq in faqs.items():
            if not isinstance(lid, str) or not lid or lid.startswith("unmapped-") or not isinstance(faq, dict) or set(faq) != {"question", "ranges"}:
                raise ProjectError("FAQ definitions require stable local IDs, question and ranges")
            question, ranges = faq["question"], faq["ranges"]
            if not isinstance(question, str) or not question.strip() or question != question.strip() or len(question) > 100 or not isinstance(ranges, list):
                raise ProjectError("FAQ question/ranges invalid; normalize questions before review")
            starts = [0] + [i + 1 for i, c in enumerate(text or "") if c == "\n"]
            for span in ranges:
                if not isinstance(span, dict) or any(type(span.get(k)) is not int for k in ("start_line", "end_line", "start_column", "end_column")):
                    raise ProjectError("FAQ ranges require integer line/column coordinates")
                offsets = []
                for edge in ("start", "end"):
                    line, col = span[edge + "_line"], span[edge + "_column"]
                    if not 1 <= line <= len(starts) or col < 0:
                        raise ProjectError("FAQ range outside saved text")
                    if line < len(starts) and col > starts[line] - starts[line - 1] - 1:
                        raise ProjectError("FAQ column exceeds its saved line")
                    offset = span.get(edge + "_offset")
                    if offset is None:
                        offset = starts[line - 1] + col
                    if type(offset) is not int or offset != starts[line - 1] + col:
                        raise ProjectError("FAQ range offsets differ from line/column basis")
                    offsets.append(offset)
                if text is None or not 0 <= offsets[0] < offsets[1] <= len(text):
                    raise ProjectError("FAQ range outside saved text")
                if span.get("text") is not None and (not isinstance(span["text"], str) or len(span["text"]) > 500):
                    raise ProjectError("FAQ range text must be at most 500 characters")


def collect(project, client, kb_id):
    """Walk public nodes; each file export is consistent, the whole walk is not atomic."""
    ws, org = client.resolve_scope()
    pending, seen, files, gaps = [kb_id], set(), {}, []
    while pending:
        parent = pending.pop()
        if parent in seen:
            raise ProjectError("Cycle or duplicate in KB traversal")
        seen.add(parent)
        try:
            children = kb.list_nodes(client, organization_id=org, workspace_id=ws, parent_id=parent)
        except CodeerError as exc:
            gaps.append({"node_id": parent, **exports.gap(exc)})
            continue
        if not children and parent == kb_id:
            try:
                files[parent] = exports.knowledge(client, parent)
            except (CodeerError, ProjectError) as exc:
                gaps.append({"node_id": parent, **exports.gap(exc)})
        for row in children:
            sid = row.get("id") or row.get("node_id")
            if str(row.get("source_type", "")).upper() in ("WEBSITE", "WEBSITE_CRAWL", "WEBSITE_CRAWLER"):
                gaps.append({"node_id": sid, "reason": CRAWL_GAP})
            if str(row.get("node_type") or row.get("type")).upper() == "FOLDER":
                pending.append(sid)
            else:
                try:
                    files[sid] = exports.knowledge(client, sid)
                except (CodeerError, ProjectError) as exc:
                    gaps.append({"node_id": sid, **exports.gap(exc)})
    return files, gaps


def import_kb(project, client, local_id, kb_id, *, dry_run=False, expected=None, initial=False, collected=None):
    if not project.portable:
        raise ProjectError("KB portable import requires schema_version 2")
    scope = project.check_scope(client)
    resources = definitions(project)
    if local_id in resources.get("knowledge", {}):
        raise ProjectError("KB definition already exists; bind explicit file IDs and use faq-sync to compare/adopt")
    if not local_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in local_id):
        raise ProjectError("Invalid KB local identity")
    files, gaps = collected if collected is not None else collect(project, client, kb_id)
    gaps = deepcopy(gaps)
    direct_file = kb_id in files
    root_id = files[kb_id]["metadata"]["knowledge_base_id"] if direct_file else kb_id
    plan = {"scope": scope, "resource": f"kb:{local_id}", "kb_id": kb_id,
            "exports": files, "gaps": gaps + [{"reason": CRAWL_GAP}], "operator": project.preview_identity(client)}
    plan["token"] = fingerprint(plan)
    if dry_run:
        return plan
    if not initial and expected != plan["token"]:
        raise ProjectError("Missing/stale KB import --expect; nothing was saved")
    if not files:
        save_json(project.local_dir / "imports" / ("kb-gap-" + uuid.uuid4().hex + ".json"), plan)
        return {"resource": f"kb:{local_id}", "obtained": [], "faq_file": None,
                "gaps": gaps + [{"reason": CRAWL_GAP}], "remote_mutations": 0, "original_backup_complete": False}
    directory = f"sources/knowledge/{local_id}/originals"
    faq_file = f"kb/{local_id}-faqs.json"
    manifest_file = f"sources/knowledge/{local_id}/manifest.json"
    targets = [project.resolve_path("knowledge", p) for p in (directory, faq_file, manifest_file)]
    if any(p.exists() for p in targets):
        raise ProjectError("Import destination exists; originals and definitions are never overwritten")
    bundle, manifests, originals, mapping, faq_mapping = {"schema_version": 1, "files": {}}, {}, {}, {}, {}
    for index, (sid, value) in enumerate(sorted(files.items())):
        meta, snapshot = value["metadata"], value["snapshot"]
        name = str(meta.get("stored_file", {}).get("filename") or meta.get("name") or "original.bin")
        # Prefix avoids same-name collisions; remote names cannot choose directories.
        name = f"{index + 1:03d}-" + Path(name.replace("\\", "/")).name
        item = {"snapshot": snapshot, "export_revision": value["export_revision"], "metadata": meta,
                "scope": scope, "agent_version_id": None, "faqs": value["faqs"], "gaps": []}
        try:
            content, receipt = exports.original(client, meta, node_id=sid)
            if receipt["provenance"] != "uploaded_original":
                raise ProjectError("Saved representation is not a portable uploaded original")
            originals[name] = content
            receipt["path"] = f"{directory}/{name}"
            item["original"] = receipt
        except (ProjectError, CodeerError, OSError) as exc:
            item["gaps"].append(exports.gap(exc))
            gaps.append({"node_id": sid, **exports.gap(exc)})
        # Detect text/FAQ changes during the separate binary download.
        try:
            exports.knowledge(client, sid, expected=value["export_revision"])
        except (CodeerError, ProjectError) as exc:
            originals.pop(name, None)
            item.pop("original", None)
            item["gaps"].append(exports.gap(exc))
            gaps.append({"node_id": sid, **exports.gap(exc)})
        mapping[name] = sid
        bundle["files"][name] = {"content": snapshot.get("content"),
                                 "faqs": {faq_id(f): faq_value(f, snapshot.get("content")) for f in value["faqs"]}}
        faq_mapping[name] = {faq_id(f): f["id"] for f in value["faqs"]}
        manifests[name] = item
    resource_gaps = [gap for gap in gaps if gap.get("reason") != CRAWL_GAP]
    previous_state = project.state()
    previous_resources = deepcopy(resources)
    try:
        for name, content in originals.items():
            path = project.resolve_path("knowledge", f"{directory}/{name}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        save_json(targets[1], bundle)
        save_json(targets[2], {"files": manifests, "gaps": gaps + [{"reason": CRAWL_GAP}],
                               "consistency": "per_file_only", "retrieved_at": now()})
        resources.setdefault("knowledge", {})[local_id] = {"directory": directory, "glob": "*", "faq_file": faq_file,
                                                         "manifest": manifest_file}
        save_json(project.root / "resources.json", resources)
        state = project.state()
        from .project_kb import local_sources
        definition = resources["knowledge"][local_id]
        state.setdefault("resources", {})[f"kb:{local_id}"] = {
            "server_id": root_id, "root_reference": not direct_file, "file_ids": mapping, "node_ids": list(mapping.values()),
            "source": {k: definition[k] for k in ("directory", "glob")},
            "local": local_sources(project, {"source": definition}), "scope": scope,
            "status": "ready" if files and not resource_gaps and len(originals) == len(files) and not any(v["snapshot"].get("content") is None for v in files.values()) else "incomplete",
            "gaps": gaps + [{"reason": CRAWL_GAP}]}
        state["resources"][f"faq:{local_id}"] = {"server_id": kb_id, "scope": scope, "ids": faq_mapping,
                                                    "base": bundle["files"], "local_base": bundle["files"], "observed": bundle["files"], "status": "aligned"}
        project.save_state(state)
    except BaseException:
        import shutil
        shutil.rmtree(targets[0], ignore_errors=True)
        for path in targets[1:]:
            path.unlink(missing_ok=True)
        save_json(project.root / "resources.json", previous_resources)
        project.save_state(previous_state)
        raise
    return {"resource": f"kb:{local_id}", "obtained": [f"{directory}/{p}" for p in originals],
            "faq_file": faq_file, "gaps": gaps + [{"reason": CRAWL_GAP}], "remote_mutations": 0,
            "original_backup_complete": bool(files) and not resource_gaps and len(originals) == len(files)}


def import_references(project, client, history):
    result = {"obtained": [], "gaps": [{"reason": CRAWL_GAP}]}
    observed = []
    for sid in sorted(agents.referenced_knowledge_nodes(history.get("unified_tools"))):
        try:
            collected = collect(project, client, sid)
            observed.append((sid in collected[0], -len(collected[0]), sid, collected))
        except (CodeerError, ProjectError, OSError) as exc:
            result["gaps"].append({"node_id": sid, **exports.gap(exc)})
    # Import covering folders first; direct file references reuse their exact IDs.
    for direct, _, sid, collected in sorted(observed, key=lambda row: row[:3]):
        from .portable import bindings
        existing = bindings(project, canonical=True)
        if direct and sid in existing.values():
            continue
        try:
            value = import_kb(project, client, "imported-" + fingerprint(sid)[:12], sid, initial=True, collected=collected)
            if value.get("faq_file"):
                result["obtained"].append(value)
                # Overlapping folders retain their originals and root identities,
                # while exact shared file IDs reuse the first imported reference.
                state = project.state()
                entry = state["resources"][value["resource"]]
                existing_files = {ref: remote for ref, remote in existing.items() if ref.startswith("kb:") and "/" in ref}
                entry["file_aliases"] = {path: next(ref for ref, remote in existing_files.items() if remote == node_id)
                                         for path, node_id in entry["file_ids"].items() if node_id in existing_files.values()}
                project.save_state(state)
            result["gaps"].extend(value["gaps"])
        except (CodeerError, ProjectError, OSError) as exc:
            result["gaps"].append({"node_id": sid, **exports.gap(exc)})
    return result


def observed_faqs(value, mappings):
    inverse = {v: k for k, v in mappings.items()}
    content = value["snapshot"]["content"]
    return {"content": content, "faqs": {inverse.get(f["id"], "unmapped-" + str(f["id"])): faq_value(f, content)
                                        for f in value["faqs"]}}


def replay_faq_changes(before, completed):
    result = deepcopy(before)
    for operation in completed:
        faqs = result[operation["file"]]["faqs"]
        if operation["value"] is None:
            faqs.pop(operation["local_id"], None)
        else:
            faqs[operation["local_id"]] = deepcopy(operation["value"])
    return result


def faq_plan(project, client, local_id, *, choice=None, ids=None, apply=False, recovery=None):
    definition = definitions(project).get("knowledge", {}).get(local_id, {})
    if not definition.get("faq_file"):
        raise ProjectError("Declare knowledge.<id>.faq_file containing saved text and stable FAQ definitions")
    path = project.resolve_path("knowledge", definition["faq_file"])
    local = read_json(path)
    if local is None and recovery is not None:
        local = {"schema_version": 1, "files": {}}
    validate_bundle(local)
    for row in local["files"].values():
        row["faqs"] = {lid: faq_value(faq, row["content"]) for lid, faq in row["faqs"].items()}
    scope = project.check_scope(client)
    resources = project.state().get("resources", {})
    binding = resources.get(f"kb:{local_id}", {})
    entry = resources.get(f"faq:{local_id}", {})
    if entry.get("scope") and not scope_matches(entry["scope"], scope, allow_unbound_agent=True):
        raise ProjectError("FAQ scope differs from selected deployment")
    if binding.get("scope") and not scope_matches(binding["scope"], scope, allow_unbound_agent=True):
        raise ProjectError("KB scope differs from selected deployment")
    file_ids = binding.get("file_ids", {})
    if recovery is not None:
        file_ids = recovery.get("file_ids") or {name: value["metadata"]["node_id"] for name, value in recovery["observations"].items()}
        if any(binding.get("file_ids", {}).get(name) != sid for name, sid in file_ids.items()):
            raise ProjectError("FAQ recovery file mapping differs from recorded operation")
    elif set(local["files"]) != set(file_ids):
        raise ProjectError("Map every declared KB file explicitly with kb bind before FAQ synchronization")
    mappings = deepcopy(entry.get("ids", {})) if ids is None else deepcopy(ids)
    if not isinstance(mappings, dict) or set(mappings) - set(file_ids):
        raise ProjectError("FAQ IDs must map declared file paths to local FAQ ID → remote FAQ ID")
    remote, observations, all_ids = {}, {}, set()
    for name, sid in file_ids.items():
        value = exports.knowledge(client, sid)
        if recovery is not None and value["snapshot"]["snapshot_object_id"] != recovery["observations"][name]["snapshot"]["snapshot_object_id"]:
            raise ProjectError("FAQ recovery snapshot differs from recorded operation")
        observations[name] = value
        by_id = {f["id"]: f for f in value["faqs"]}
        mapped = mappings.get(name, {})
        allowed = set(local["files"].get(name, {}).get("faqs", {})) | set(entry.get("ids", {}).get(name, {}))
        if recovery is not None:
            allowed.update(recovery["local"].get(name, {}).get("faqs", {}))
        if not isinstance(mapped, dict) or set(mapped) - allowed:
            raise ProjectError("FAQ mapping contains undeclared identities")
        historical = {**(recovery or {}).get("ids", {}).get(name, {}), **entry.get("ids", {}).get(name, {})}
        if any((remote_id not in by_id and historical.get(lid) != remote_id) or remote_id in all_ids for lid, remote_id in mapped.items()) or len(set(mapped.values())) != len(mapped):
            raise ProjectError("FAQ mapping absent from this exact snapshot or ambiguous; no name matching")
        all_ids.update(mapped.values())
        remote[name] = observed_faqs(value, mapped)
    comparison = compare(entry, local["files"], remote)
    plan = {"resource": f"faq:{local_id}", "scope": scope, "local": local["files"], "remote": remote,
            "ids": mappings, "file_ids": file_ids, "observations": observations, "comparison": comparison,
            "choice": choice, "apply": apply, "operator": project.preview_identity(client)}
    plan["token"] = fingerprint({**plan, "observations": {name: {"node_id": value["metadata"]["node_id"],
                                           "export_revision": value["export_revision"]} for name, value in observations.items()}})
    return plan


def faq_sync(project, client, local_id, *, dry_run, expected=None, choice=None, ids=None, apply=False, reconcile=False):
    key = f"faq:{local_id}"
    state = project.state()
    entry = state.setdefault("resources", {}).setdefault(key, {})
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
        if not reconcile:
            raise ProjectError("FAQ write unresolved; reconcile recorded identities before any new write")
        return reconcile_faq(project, client, key, entry, ids=ids, dry_run=dry_run)
    if reconcile:
        raise ProjectError("No unresolved FAQ operation")
    plan = faq_plan(project, client, local_id, choice=choice, ids=ids, apply=apply)
    if dry_run:
        # Cache observation only. Proposed mappings, decisions and bases are untouched.
        entry.update(observed=plan["remote"], observed_at=now())
        state["resources"][key] = entry
        project.save_state(state)
        return plan
    if expected != plan["token"] or choice not in ("local", "remote"):
        raise ProjectError("Review FAQ choice and current --expect before adopting or applying")
    definition = definitions(project)["knowledge"][local_id]
    entry.update(scope=plan["scope"], ids=plan["ids"], observed=plan["remote"])
    if choice == "remote":
        if apply:
            raise ProjectError("Remote adoption writes local definitions only; omit --apply")
        adopted, new_ids = {}, {}
        for name, observed in plan["observations"].items():
            inverse = {v: k for k, v in plan["ids"].get(name, {}).items()}
            adopted[name] = {"content": observed["snapshot"]["content"], "faqs": {inverse.get(f["id"], faq_id(f)): faq_value(f, observed["snapshot"]["content"]) for f in observed["faqs"]}}
            new_ids[name] = {inverse.get(f["id"], faq_id(f)): f["id"] for f in observed["faqs"]}
        save_json(project.resolve_path("knowledge", definition["faq_file"]), {"schema_version": 1, "files": adopted})
        if read_json(project.resolve_path("knowledge", definition["faq_file"]))["files"] != adopted:
            raise ProjectError("Local FAQ adoption verification failed; bases unchanged")
        entry.update(ids=new_ids, base=adopted, local_base=adopted, observed=adopted, status="aligned", decisions={})
    elif not apply:
        entry.update(decisions={name: {"local": fingerprint(row), "remote": fingerprint(plan["remote"][name])}
                                for name, row in plan["local"].items()}, status="pending_apply")
    else:
        # Complete collection is atomic for review; never delete or overwrite unowned FAQ.
        operations = []
        for name, local in plan["local"].items():
            observed = plan["observations"][name]
            if local.get("content") is None or local["content"] != observed["snapshot"]["content"]:
                raise ProjectError("Target saved text differs; review FAQ ranges before rebuilding")
            if any(k.startswith("unmapped-") for k in plan["remote"][name]["faqs"]):
                raise ProjectError("Unmapped target FAQ; explicitly map IDs or adopt remote before writing")
            if plan["comparison"][name]["state"] == "undecided":
                raise ProjectError("Keep-local decision required before applying FAQ differences")
            for lid, faq in local["faqs"].items():
                remote_id = plan["ids"].get(name, {}).get(lid)
                if remote_id is not None and lid not in plan["remote"][name]["faqs"]:
                    raise ProjectError("Mapped FAQ was removed or moved; adopt deletion or explicitly review a new identity mapping")
                if plan["remote"][name]["faqs"].get(lid) != faq:
                    operations.append({"file": name, "local_id": lid, "remote_id": remote_id,
                                       "snapshot_object_id": observed["snapshot"]["snapshot_object_id"], "value": faq})
            for lid in plan["remote"][name]["faqs"].keys() - local["faqs"].keys():
                operations.append({"file": name, "local_id": lid, "remote_id": plan["ids"][name][lid],
                                   "snapshot_object_id": observed["snapshot"]["snapshot_object_id"], "value": None})
        receipt_path = project.local_dir / "receipts" / ("faq-" + uuid.uuid4().hex + ".json")
        receipt = {"plan": plan, "operations": operations, "completed": [], "status": "pending"}
        current_exports = deepcopy(plan["observations"])
        entry.update(status="pending", receipt=str(receipt_path.relative_to(project.root)))
        save_json(receipt_path, receipt)
        project.save_state(state)
        try:
            for operation in operations:
                name = operation["file"]
                exports.knowledge(client, current_exports[name]["metadata"]["node_id"],
                                  expected=current_exports[name]["export_revision"])
                receipt["inflight"] = operation
                save_json(receipt_path, receipt)
                if operation["value"] is None:
                    kb.delete_context_obj_faq(client, faq_id=operation["remote_id"])
                    returned_id = None
                else:
                    params = {"context_object_id": operation["snapshot_object_id"], **operation["value"]}
                    result = (kb.update_context_obj_faq(client, faq_id=operation["remote_id"], **params)
                              if operation["remote_id"] is not None else kb.create_context_obj_faq(client, **params))
                    if result.get("context_object_id") != operation["snapshot_object_id"] or faq_value(result, plan["local"][name]["content"]) != operation["value"]:
                        raise ProjectError("FAQ write response identity/content mismatch; inspect recorded operation")
                    returned_id = result["id"]
                receipt["completed"].append({**operation, "returned_id": returned_id})
                receipt.pop("inflight", None)
                save_json(receipt_path, receipt)
                mapped = entry.setdefault("ids", {}).setdefault(name, {})
                if returned_id is None:
                    mapped.pop(operation["local_id"], None)
                else:
                    mapped[operation["local_id"]] = returned_id
                project.save_state(state)
                # Each confirmed mutation changes export_revision; refresh its readback.
                refreshed = exports.knowledge(client, current_exports[name]["metadata"]["node_id"])
                expected_remote = replay_faq_changes(plan["remote"], receipt["completed"])
                if refreshed["snapshot"]["snapshot_object_id"] != operation["snapshot_object_id"] or observed_faqs(refreshed, entry["ids"].get(name, {})) != expected_remote[name]:
                    raise ProjectError("FAQ readback contains unreviewed changes; reconcile before deciding again")
                current_exports[name] = refreshed
            return reconcile_faq(project, client, key, entry)
        except BaseException:
            entry["status"] = receipt["status"] = "outcome_unknown"
            save_json(receipt_path, receipt)
            project.save_state(state)
            raise
    state["resources"][key] = entry
    project.save_state(state)
    return {"resource": key, "status": entry["status"], "remote_mutations": 0}


def reconcile_faq(project, client, key, entry, *, ids=None, dry_run=False):
    receipt = read_json(project.root / entry["receipt"])
    if not scope_matches(receipt["plan"]["scope"], project.check_scope(client), allow_unbound_agent=True):
        raise ProjectError("FAQ recovery scope differs")
    if receipt.get("inflight") and receipt["inflight"].get("remote_id") is None:
        op = receipt["inflight"]
        recovered_id = (ids or {}).get(op["file"], {}).get(op["local_id"])
        if recovered_id is None:
            raise ProjectError("Unknown created FAQ identity; inspect receipt and coordinate recovery, never recreate by question")
        receipt["completed"].append({**op, "returned_id": recovered_id})
        receipt.pop("inflight")
    ids = deepcopy(ids if ids is not None else entry.get("ids", receipt["plan"]["ids"]))
    for operation in receipt["completed"]:
        mapped = ids.setdefault(operation["file"], {})
        if operation["returned_id"] is None:
            mapped.pop(operation["local_id"], None)
        else:
            mapped[operation["local_id"]] = operation["returned_id"]
    if receipt.get("inflight") and receipt["inflight"]["value"] is None:
        operation = receipt["inflight"]
        sid = project.state()["resources"]["kb:" + key.split(":", 1)[1]]["file_ids"][operation["file"]]
        if any(f["id"] == operation["remote_id"] for f in exports.knowledge(client, sid)["faqs"]):
            raise ProjectError("FAQ deletion unconfirmed; inspect operation before any retry")
        ids.setdefault(operation["file"], {}).pop(operation["local_id"], None)
        receipt["completed"].append({**operation, "returned_id": None})
        receipt.pop("inflight")
    plan = faq_plan(project, client, key.split(":", 1)[1], ids=ids, recovery=receipt["plan"])
    # Preserve a proposal edited while the operation was interrupted.
    expected_local = receipt["plan"]["local"]
    if receipt.get("inflight") and receipt["inflight"]["value"] is not None:
        op = receipt["inflight"]
        if plan["remote"][op["file"]]["faqs"].get(op["local_id"]) != op["value"]:
            raise ProjectError("FAQ write readback unconfirmed; bases unchanged")
        receipt["completed"].append({**op, "returned_id": op["remote_id"]})
        receipt.pop("inflight")
    for op in receipt["completed"]:
        if plan["remote"][op["file"]]["faqs"].get(op["local_id"]) != op["value"]:
            raise ProjectError("Completed FAQ readback changed; bases unchanged")
    expected_remote = replay_faq_changes(receipt["plan"]["remote"], receipt["completed"])
    conflicts = [name for name, value in plan["remote"].items() if value != expected_remote[name]]
    aligned = not conflicts and plan["remote"] == expected_local
    status = "conflict" if conflicts else "aligned" if aligned else "pending_apply"
    if dry_run:
        return {"resource": key, "status": status, "remote_mutations": 0,
                "comparison": compare(entry, plan["local"], plan["remote"]), "read_only": True}
    entry.update(ids=ids, observed=plan["remote"], status=status)
    for name, remote in plan["remote"].items():
        if name in conflicts:
            entry.setdefault("decisions", {}).pop(name, None)
            continue
        entry.setdefault("base", {})[name] = deepcopy(remote)
        entry.setdefault("local_base", {})[name] = deepcopy(expected_local[name])
        if remote == expected_local[name]:
            entry.setdefault("decisions", {}).pop(name, None)
        else:
            entry.setdefault("decisions", {})[name] = {"local": fingerprint(expected_local[name]), "remote": fingerprint(remote)}
    receipt["conflicts"] = conflicts
    receipt.update(status=entry["status"], reconciled_at=now())
    save_json(project.root / entry["receipt"], receipt)
    state = project.state()
    state.setdefault("resources", {})[key] = entry
    project.save_state(state)
    return {"resource": key, "status": entry["status"], "comparison": compare(entry, plan["local"], plan["remote"]),
            "remote_mutations": 0, "receipt": entry["receipt"]}
