"""Consumers of the external resource-export contract (backend Phases 1–4)."""
import hashlib
from tempfile import TemporaryFile

import httpx

from .client import CodeerError, _api_url
from .project import ProjectError, now


def knowledge(client, node_id, *, expected=None):
    params = {"expected_export_revision": expected} if expected else None
    value = client.get(f"/external/knowledge-bases/files/{node_id}/export", params=params)
    metadata, snapshot, faqs = value.get("metadata", {}), value.get("snapshot", {}), value.get("faqs")
    sid = metadata.get("snapshot_object_id")
    if (metadata.get("node_id") != node_id or not sid or snapshot.get("snapshot_object_id") != sid
            or not isinstance(faqs, list) or any(f.get("context_object_id") != sid for f in faqs)
            or len({f.get("id") for f in faqs}) != len(faqs) or not value.get("export_revision")
            or snapshot.get("content") is not None and not isinstance(snapshot["content"], str)):
        raise ProjectError("Invalid KB export: metadata/text/complete FAQ must share one snapshot")
    value["faqs"] = sorted(faqs, key=lambda f: f["id"])
    return value


def attachment(client, attachment_id):
    value = client.get(f"/external/files/{attachment_id}")
    if value.get("attachment_id") != attachment_id:
        raise ProjectError("Attachment metadata identity differs")
    return value


def attachment_text(client, metadata):
    identity = metadata.get("text_snapshot", {}).get("revision")
    sid = metadata["attachment_id"]
    if identity is None:
        raise ProjectError("Attachment text requires its own metadata revision")
    result = client.get(f"/external/files/{sid}/content", params={"expected_revision": identity})
    if result.get("attachment_id") != sid or result.get("content_revision") != identity or not isinstance(result.get("content"), str):
        raise ProjectError("Attachment text identity/content mismatch")
    return result


def original(client, metadata, *, node_id=None, attachment_id=None):
    """Stage authenticated bytes, validate identity/length/digest, then return them.

    No redirects, source-URL fallback, or successful partial-file records.
    """
    stored = metadata.get("stored_file", {})
    if not stored.get("available"):
        raise ProjectError("Original unavailable: " + str(stored.get("reason") or "capability_gap"))
    if node_id:
        identity = metadata.get("snapshot_object_id")
        path = f"/external/knowledge-bases/files/{node_id}/download"
        params, header = {"expected_snapshot_object_id": identity}, "X-Codeer-Snapshot-Object-Id"
    else:
        identity = stored.get("revision")
        path = f"/external/files/{attachment_id}/download"
        params, header = {"expected_revision": identity}, "X-Codeer-Content-Revision"
    if identity is None:
        raise ProjectError("Download requires snapshot/revision identity")
    digest, size = hashlib.sha256(), 0
    try:
        with TemporaryFile() as staged, client._client.stream("GET", _api_url(path), params=params) as response:
            if response.status_code != 200:
                response.read()
                if response.status_code >= 400:
                    client._parse(response)
                raise ProjectError("Resource download must return bytes without redirects")
            if response.headers.get(header) != str(identity):
                raise ProjectError("Download snapshot/revision header mismatch")
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 100 * 1024 * 1024:
                    raise ProjectError("Original exceeds 100 MiB download limit")
                staged.write(chunk)
                digest.update(chunk)
            lengths = [stored.get("size_bytes"), response.headers.get("Content-Length")]
            if any(length is not None and (not str(length).isdigit() or size != int(length)) for length in lengths):
                raise ProjectError("Original received length mismatch")
            sha = digest.hexdigest()
            if stored.get("sha256") and sha != stored["sha256"]:
                raise ProjectError("Original server digest mismatch")
            staged.seek(0)
            content = staged.read()
    except httpx.HTTPError:
        raise ProjectError("Original transfer interrupted; no successful file was saved") from None
    receipt = {"node_id": node_id, "attachment_id": attachment_id,
               "snapshot_object_id": metadata.get("snapshot_object_id"), "revision": stored.get("revision"),
               "representation": "stored_file", "provenance": stored.get("provenance", "unknown"),
               "server_size_bytes": stored.get("size_bytes"), "server_sha256": stored.get("sha256"),
               "received_size_bytes": size, "local_sha256": sha, "downloaded_at": now(),
               "verification": ("size_digest_verified" if any(v is not None for v in lengths) else "digest_verified") if stored.get("sha256") else "no_server_digest",
               "gaps": [] if stored.get("sha256") else ["server_digest_unavailable"]}
    return content, receipt


def gap(exc):
    """Bounded diagnostics without URLs, server text, or credentials."""
    body = getattr(exc, "body", None)
    data = body.get("data") if isinstance(body, dict) else None
    reason = data.get("reason") if isinstance(data, dict) else None
    known = {"not_ready", "snapshot_missing", "stored_file_missing", "storage_unavailable", "resource_changed",
             "original_missing", "unsupported_source", "unsupported_attachment_type", "content_missing",
             "workspace_required", "permission_denied", "resource_not_found", "not_found"}
    if reason in known:
        return {"reason": reason, "status": getattr(exc, "status", None), "original_obtained": False}
    return {"reason": "export_api_unavailable" if isinstance(exc, CodeerError) and exc.status in (404, 405, 501)
            else "resource_changed" if isinstance(exc, CodeerError) and exc.status == 409
            else type(exc).__name__, "status": getattr(exc, "status", None), "original_obtained": False}
