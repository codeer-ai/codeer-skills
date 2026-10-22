"""Original attachment bytes with per-deployment upload receipts."""
import hashlib
import uuid

import httpx

from .portable import definitions
from .project import ProjectError, fingerprint, now, read_json, save_json
from .client import CodeerError
from .kb import guess_upload_mime


def download(client, attachment_id, expected_size=None, *, record=None):
    from .resource_exports import attachment, attachment_text, original
    metadata = attachment(client, attachment_id)
    if record is not None:
        record.update(metadata=metadata, provenance=metadata.get("stored_file", {}).get("provenance", "unknown"))
        if metadata.get("text_snapshot", {}).get("available"):
            record["text_snapshot"] = attachment_text(client, metadata)
    content, receipt = original(client, metadata, attachment_id=attachment_id)
    if expected_size is not None and len(content) != expected_size:
        raise ProjectError("Original bytes do not match the declared size")
    if record is not None:
        record.update(receipt, metadata=metadata)
    return content


def upload(project, client, local_id, *, dry_run, expected=None, reconcile=False, remote_id=None, new=False):
    if not project.target:
        raise ProjectError("Configure a portable deployment before uploading attachments")
    definition = definitions(project).get("attachments", {}).get(local_id)
    if not definition:
        raise ProjectError("Unknown attachment local ID in resources.json")
    path = project.resolve_path("attachment", definition["path"])
    content = path.read_bytes()
    scope = project.check_scope(client)
    key = f"attachment:{local_id}"
    state = project.state()
    entry = state.setdefault("resources", {}).get(key, {})
    digest = hashlib.sha256(content).hexdigest()
    if remote_id:
        if new or reconcile or entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
            raise ProjectError("Existing-original mapping is separate from upload/recovery; reconcile recorded operations first")
        if entry.get("server_id") not in (None, remote_id):
            raise ProjectError("Attachment ID differs from the saved mapping")
        if any(other != key and other.startswith("attachment:") and mapped.get("server_id") == remote_id for other, mapped in state["resources"].items()):
            raise ProjectError("Original is already mapped; reuse its stable local ID instead of adding an ambiguous alias")
        from . import agents, eval_ as api
        aid = project.target.get("agent_id")
        if not aid:
            raise ProjectError("Attachment takeover requires an explicitly selected existing Agent")
        hid = agents.get_latest_history_id(client, aid)
        history = agents.get_version(client, aid, hid) if hid else {}
        candidates = list(history.get("attachments", []))
        if not any(row.get("id") == remote_id for row in candidates):
            for case in api.list_cases(client, aid):
                if remote_id in {a.get("id") for a in case.get("attachments", [])} or remote_id in case.get("attachment_ids", []):
                    candidates.extend(api.get_case(client, case["id"]).get("attachments", []))
        matches = [row for row in candidates if row.get("id") == remote_id]
        if not matches:
            raise ProjectError("Original metadata/identity is absent from this Agent/Eval; do not infer it by filename")
        original = matches[0]
        if original.get("attachment_type", "file") not in ("file", "generated_image", "generated_audio"):
            raise ProjectError("This is a context/web reference, not a verifiable original file")
        actual = download(client, remote_id, original.get("size"))
        if actual != content:
            raise ProjectError("Existing attachment bytes differ; retain the local proposal and explicitly review a new attachment/reference")
        plan = {"resource": key, "operation": "bind_original", "scope": scope, "remote_id": remote_id,
                "path": definition["path"], "sha256": digest, "size": len(content), "operator": project.preview_identity(client)}
        plan["token"] = fingerprint(plan)
        if dry_run:
            return plan
        if expected != plan["token"]:
            raise ProjectError("Missing/stale original mapping --expect")
        entry.update(server_id=remote_id, sha256=digest, status="ready", scope=scope, tracked_at=now())
        state["resources"][key] = entry
        save_json(project.local_dir / "imports" / f"attachment-{uuid.uuid4().hex}.json", plan)
        project.save_state(state)
        return {"resource": key, "status": "ready", "remote_mutations": 0}
    if (project.target.get("intent") != "create" or project.target.get("agent_id")) and not entry and not new:
        raise ProjectError("Takeover requires --remote-id <uuid> with byte verification, or an explicitly reviewed --new upload")
    plan = {"resource": key, "scope": scope, "path": definition["path"], "sha256": digest,
            "size": len(content), "purpose": definition.get("purpose"), "previous": entry, "new": new}
    plan["operator"] = project.preview_identity(client)
    plan["token"] = fingerprint(plan)
    if dry_run:
        return plan
    if entry.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
        if not reconcile:
            raise ProjectError("Unresolved upload; inspect receipt and use --reconcile; never retry unknown create")
        receipt = read_json(project.root / entry["receipt"], {})
        response = receipt.get("response", {})
        if not response.get("uuid"):
            raise ProjectError("Upload identity unknown; coordinate recovery before any retry")
        actual = download(client, response["uuid"], receipt["plan"]["size"])
        if hashlib.sha256(actual).hexdigest() != receipt["plan"]["sha256"]:
            raise ProjectError("Original readback mismatch; receipt retained")
        entry.update(server_id=response["uuid"], status="ready", sha256=receipt["plan"]["sha256"])
        from .operation_records import mutable_receipt
        receipt_path, receipt = mutable_receipt(project, entry)
        receipt.update(status="ready", reconciled_at=now())
        save_json(receipt_path, receipt)
        project.save_state(state)
        return {"resource": key, "status": "ready", "remote_mutations": 0}
    if expected != plan["token"]:
        raise ProjectError("Missing or stale attachment --expect")
    if entry.get("server_id"):
        if entry.get("sha256") != digest:
            raise ProjectError("Attachment replacement requires a new local ID and reviewed references")
        return {"resource": key, "status": entry["status"], "unchanged": True}
    receipt_path = project.local_dir / "receipts" / f"attachment-{uuid.uuid4().hex}.json"
    receipt = {"plan": plan, "status": "pending"}
    entry = {"status": "pending", "receipt": str(receipt_path.relative_to(project.root)), "scope": scope}
    state["resources"][key] = entry
    save_json(receipt_path, receipt)
    project.save_state(state)
    try:
        response = client.post("/external/files", files={"file": (path.name, content, guess_upload_mime(path.name))},
                               params={"scope": "persistent", **({"purpose": definition["purpose"]} if definition.get("purpose") else {})})
        receipt["response"] = response
        save_json(receipt_path, receipt)
        entry["server_id"] = response.get("uuid")
        project.save_state(state)
        if not entry["server_id"]:
            raise ProjectError("Upload returned no identity; inspect receipt before retry")
        verification = {}
        actual = download(client, response["uuid"], len(content), record=verification)
        receipt["verification"] = verification
        if actual != content:
            entry["status"] = "readback_mismatch"
        else:
            entry.update(status="ready", sha256=digest)
        receipt.update(status=entry["status"], readback_sha256=hashlib.sha256(actual).hexdigest())
    except BaseException:
        receipt["status"] = entry["status"] = "outcome_unknown"
        raise
    finally:
        save_json(receipt_path, receipt)
        project.save_state(state)
    return {"resource": key, "status": entry["status"], "receipt": str(receipt_path)}


def import_originals(project, client, history):
    """Best-effort import; missing bytes stay explicit gaps, never URL backups."""
    resources = definitions(project)
    state = project.state()
    result = {"obtained": [], "gaps": []}
    for item in history.get("attachments", []):
        sid = item["id"]
        local_id = "imported-" + fingerprint(sid)[:12]
        # Untrusted names must not choose paths outside this attachment directory.
        from pathlib import Path
        relative = f"sources/documents/{local_id}/{Path(item.get('original_name') or 'original.bin').name}"
        path = project.resolve_path("attachment", relative)
        try:
            record = {}
            content = download(client, sid, record=record)
            if path.exists() and path.read_bytes() != content:
                raise ProjectError("Existing original differs; preserve it and resolve manually")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            record.update(path=relative, scope=project.check_scope(client), agent_version_id=history.get("id"))
            save_json(project.root / f"sources/exports/{local_id}.json", record)
            if record.get("provenance") == "uploaded_original":
                resources.setdefault("attachments", {})[local_id] = {"path": relative}
                state.setdefault("resources", {})[f"attachment:{local_id}"] = {"server_id": sid, "status": "ready", "sha256": hashlib.sha256(content).hexdigest(), "retrieved_at": now()}
            else:
                result["gaps"].append({"attachment_id": sid, "reason": "saved_representation_is_not_uploaded_original", "original_obtained": False})
            result["obtained"].append(relative)
        except (ProjectError, CodeerError, httpx.HTTPError, OSError) as exc:
            from .resource_exports import gap
            if record:
                save_json(project.root / f"sources/exports/{local_id}.json", {**record, "scope": project.check_scope(client),
                          "agent_version_id": history.get("id"), "gaps": [gap(exc)], "original_obtained": False})
            result["gaps"].append({"attachment_id": sid, **gap(exc)})
    save_json(project.root / "resources.json", resources)
    project.save_state(state)
    known = {item["id"] for item in history.get("attachments", [])}
    for sid in set(history.get("attachment_ids", [])) - known:
        result["gaps"].append({"attachment_id": sid, "reason": "original metadata/URL unavailable", "original_obtained": False})
    return result
