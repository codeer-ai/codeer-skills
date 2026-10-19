"""Offline, reference-aware cleanup of selected binding operation history.

Only recognized, completed machine history is eligible. All other project files
are roots. Direct file editors must stop while this advisory protocol is in use.
"""
from copy import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from .evidence_references import TEXT, relative_references
from .project import ProjectError, fingerprint, read_json, save_json
from .project_lock import project_lock

COMPLETED = {"applied", "ready", "rejected", "aligned", "retired"}


def known_receipt(record):
    """Admit only the existing request/recovery contracts, never status alone."""
    plan = record.get("plan")
    if not isinstance(plan, dict) or record.get("schema_version", 1) != 1:
        return False
    key = plan.get("resource", "")
    if not isinstance(key, str):
        return False
    if plan.get("operation") == "case_delete":
        return key.startswith("case:") and bool(plan.get("server_id")) and isinstance(record.get("previous"), dict)
    if plan.get("operation") == "record_operator_verified_validation_rejection":
        return key == "agent" and bool(plan.get("receipt_sha256")) and bool(plan.get("evidence_sha256"))
    if key.startswith("attachment:"):
        return bool(plan.get("sha256")) and isinstance(plan.get("size"), int) and bool(plan.get("path"))
    if key.startswith(("kb:", "fork-kb:")):
        return isinstance(plan.get("local"), dict) and isinstance(plan.get("upload_files"), list) and isinstance(plan.get("source"), dict)
    if key.startswith("faq:"):
        return (isinstance(plan.get("local"), dict) and isinstance(plan.get("remote"), dict)
                and isinstance(record.get("operations"), list) and isinstance(record.get("completed"), list))
    return (bool(re.fullmatch(r"agent|(?:case|tester|pairs|fork-tester):.+", key))
            and isinstance(plan.get("payload"), dict) and isinstance(plan.get("local"), dict)
            and isinstance(plan.get("token"), str))


def files_in(root):
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in folders:
            if (Path(directory) / name).is_symlink() and name != "_plans":
                raise ProjectError(f"Cleanup cannot establish references through symlink: {Path(directory, name).relative_to(root)}")
        folders[:] = sorted(name for name in folders if name not in (".git", ".venv", "__pycache__", "node_modules")
                            and not (Path(directory) / name).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if path == root / ".codeer/project.lock" or name.endswith(".tmp"):
                continue
            if path.is_symlink():
                raise ProjectError(f"Cleanup cannot establish references through symlink: {path.relative_to(root)}")
            yield path


def age_days(value):
    if value is None:
        return 0
    if not re.fullmatch(r"[0-9]+d", value):
        raise ProjectError("--older-than requires a whole number of days, e.g. 30d")
    return int(value[:-1])


def keep_index(project):
    record = read_json(project.root / ".codeer/keep.json", {"schema_version": 1, "entries": []})
    if (not isinstance(record, dict) or record.get("schema_version") != 1 or not isinstance(record.get("entries"), list)
            or any(not isinstance(row, dict) or not isinstance(row.get("path"), str) or not row["path"]
                   or not isinstance(row.get("reason"), str) or not row["reason"].strip() for row in record["entries"])):
        raise ProjectError("Invalid manual keep index; cleanup roots cannot be established")
    for row in record["entries"]:
        project.resolve_path("keep", row["path"])
    return record


def preview(project, older_than=None):
    if not project.deployment or not project.target:
        raise ProjectError("Select a configured binding before cleanup")
    keep_index(project)
    days = age_days(older_than)
    current_time = datetime.now(timezone.utc).timestamp()
    all_files = sorted(files_in(project.root))
    contents = {}
    inventory = []
    for path in all_files:
        name = str(path.relative_to(project.root))
        if path.suffix in TEXT:
            content = path.read_bytes()
            contents[name] = content
            digest = hashlib.sha256(content).hexdigest()
        else:
            # Originals/PDFs may dwarf operation history. Fingerprint them without
            # keeping every binary in memory; they are never deletion candidates.
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
        inventory.append((name, digest, path.stat().st_mtime_ns))
    # All bindings are roots and must be understood, even when cleaning one.
    for path in (project.root / ".codeer/deployments").glob("*/target.json"):
        bound = copy(project).select(path.parent.name)
        if not bound.target:
            raise ProjectError("Cleanup cannot establish a binding scope")
        bound.state()
    candidates, protected, unknown = {}, {}, []
    machine = project.local_dir
    for path in all_files:
        if not path.is_relative_to(machine):
            continue
        name = str(path.relative_to(project.root))
        relative = path.relative_to(machine)
        if relative.parts[0] not in ("receipts", "imports"):
            continue
        try:
            record = json.loads(contents[name])
            if not isinstance(record, dict):
                raise ValueError("object required")
            is_receipt = (relative.parts[0] == "receipts" and path.suffix == ".json"
                          and known_receipt(record) and isinstance(record.get("status"), str))
            known_import = (len(relative.parts) == 3 and relative.parts[0] == "imports"
                            and re.fullmatch(r"[0-9a-f]{64}", relative.parts[1])
                            and relative.parts[2] in ("agent.json", "eval.json")
                            and isinstance(record.get("scope"), dict) and record.get("retrieved_at"))
            if not is_receipt and not known_import:
                raise ValueError("unrecognized machine record")
            saved_scope = record.get("scope") or record.get("plan", {}).get("scope")
            if (not isinstance(saved_scope, dict) or not isinstance(saved_scope.get("api_base"), str)
                    or not isinstance(saved_scope.get("workspace_id"), str)
                    or not saved_scope["api_base"] or not saved_scope["workspace_id"]):
                raise ValueError("scope unknown")
            if saved_scope["api_base"].rstrip("/") != project.target["api_base"].rstrip("/") or saved_scope["workspace_id"] != project.target["workspace_id"]:
                raise ValueError("scope differs")
            if saved_scope.get("agent_id") is not None and saved_scope["agent_id"] != project.target.get("agent_id"):
                raise ValueError("Agent scope differs")
            if is_receipt and record["status"] not in COMPLETED:
                protected[name] = "unfinished or unrecognized outcome"
                continue
            if current_time - path.stat().st_mtime < days * 86400:
                protected[name] = "newer than requested age"
                continue
            hashes = {hashlib.sha256(contents[name]).hexdigest(), fingerprint(record)}
            if known_import:
                hashes.add(fingerprint({key: value for key, value in record.items() if key != "retrieved_at"}))
            candidates[name] = {"path": name, "absolute": str(path), "bytes": len(contents[name]), "hashes": hashes}
        except (ValueError, TypeError, KeyError):
            unknown.append(name)
    if unknown:
        # Scope/contract cannot be reconstructed: retain this whole binding.
        protected.update({name: "binding contains unrecognized history" for name in candidates})
        candidates = {}
    roots = set(contents) - set(candidates)
    reachable = set()
    for name in roots:
        path = project.root / name
        if path.suffix in TEXT or name == ".codeer/keep.json":
            # Invalid current state was rejected above; corrupt root evidence is
            # still scanned as raw text, and conservatively stops all cleanup.
            if path.suffix == ".json" and name not in unknown:
                try:
                    json.loads(contents[name])
                except ValueError as exc:
                    raise ProjectError(f"Cannot establish cleanup roots: {name}") from exc
            found = relative_references(contents[name], path, project.root, candidates)
            for key in found:
                protected.setdefault(key, f"referenced by {name}")
            reachable |= found
    pending = list(reachable)
    while pending:
        name = pending.pop()
        for other in relative_references(contents[name], project.root / name, project.root, candidates) - reachable:
            reachable.add(other)
            protected[other] = f"referenced by retained {name}"
            pending.append(other)
    # Delete referrers before dependencies. An interrupted cleanup must not leave
    # a surviving machine record citing an already-deleted operation. Cycles
    # (and their dependencies) are retained rather than partially dismantled.
    unreferenced = set(candidates) - reachable
    edges = {name: relative_references(contents[name], project.root / name, project.root, candidates) & unreferenced
             for name in unreferenced}
    incoming = {name: 0 for name in unreferenced}
    for targets in edges.values():
        for name in targets:
            incoming[name] += 1
    ready = sorted(name for name, count in incoming.items() if count == 0)
    order = []
    while ready:
        name = ready.pop(0)
        order.append(name)
        for target in sorted(edges[name]):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
                ready.sort()
    for name in unreferenced - set(order):
        protected[name] = "cyclic operation references or their dependencies"
    removable = [candidates[name] for name in order]
    rows = [{key: row[key] for key in ("path", "bytes")} for row in removable]
    plan = {"binding": project.deployment, "older_than": older_than, "candidates": rows,
            "file_count": len(rows), "bytes": sum(row["bytes"] for row in rows),
            "protected": protected, "unknown": unknown, "offline": True,
            "limitation": "Stop direct file editors/audit/pin tools during cleanup; only current CLI writers share the lock"}
    plan["token"] = fingerprint({"plan": plan, "inventory": inventory})
    return plan


def clean(project, *, dry_run=False, expected=None, older_than=None):
    if dry_run:
        return preview(project, older_than)
    with project_lock(project.root):
        plan = preview(project, older_than)
        if not expected or expected != plan["token"]:
            raise ProjectError("Missing/stale clean --expect; review a fresh offline dry-run")
        removed = []
        for row in plan["candidates"]:
            path = project.root / row["path"]
            if not path.resolve().is_relative_to(project.local_dir.resolve()) or path.is_symlink():
                raise ProjectError("Cleanup candidate escaped the selected binding")
            path.unlink()
            removed.append(row)
        return {"binding": project.deployment, "removed": removed, "file_count": len(removed),
                "bytes": sum(row["bytes"] for row in removed), "remote_mutations": 0}


def keep(project, value, reason):
    path = project.resolve_path("keep", value)
    if not path.exists() or not reason or not reason.strip():
        raise ProjectError("Keep requires an existing project path and a nonempty reason")
    with project_lock(project.root):
        index = project.root / ".codeer/keep.json"
        record = keep_index(project)
        name = str(path.relative_to(project.root))
        entries = [row for row in record["entries"] if row.get("path") != name]
        record["entries"] = [*entries, {"path": name, "reason": reason.strip()}]
        save_json(index, record)
        return {"kept": name, "reason": reason.strip(), "remote_mutations": 0}
