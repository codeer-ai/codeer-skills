"""Knowledge base CRUD + file upload.

KBs are tree-shaped (KnowledgeNode): the root node is the KB itself, children are
folders or files. All endpoints are scoped under an organization + workspace.
"""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any, List, Optional

from .client import CodeerClient


# Extensions whose MIME type the system table often gets wrong on macOS/Linux,
# and what the Codeer upload validator expects. Backend accepts any ``text/*``
# subtype plus a fixed set of document/image mimetypes — see
# ``codeer/common/files.py :: validate_uploaded_file``.
_MIME_OVERRIDES = {
    ".md":       "text/markdown",
    ".markdown": "text/markdown",
    ".txt":      "text/plain",
    ".csv":      "text/csv",
}


def _guess_mime(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in _MIME_OVERRIDES:
        return _MIME_OVERRIDES[ext]
    guess, _ = mimetypes.guess_type(filename)
    # Last-resort fallback. Backend rejects application/octet-stream with
    # "Content-Type is missing"-class errors, so prefer text/plain for anything
    # unknown — validator then only passes if the extension is also allowed.
    return guess or "application/octet-stream"


def _base(organization_id: str, workspace_id: str) -> str:
    del organization_id, workspace_id
    return "/knowledge-bases"


def list_nodes(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    parent_id: Optional[str] = None,
) -> list[dict]:
    """List children of a node. Omit parent_id to list top-level KBs."""
    params = {"parent_id": parent_id} if parent_id else None
    return client.get(f"{_base(organization_id, workspace_id)}/nodes", params=params)


def create_kb(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a top-level KB (a folder with no parent).

    ``POST /nodes`` has no ``type`` field — the server infers KB-root vs nested
    folder from whether ``parent_id`` is set. Use :func:`create_folder` for
    folders under an existing KB.
    """
    body: dict[str, Any] = {"name": name}
    if description is not None:
        body["description"] = description
    return client.post("/knowledge-bases", json=body)


def create_folder(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    parent_id: str,
    name: str,
    description: Optional[str] = None,
) -> dict:
    """Create a folder inside a KB. **Pass the KB root id as ``parent_id``.**

    A KB is structured as exactly one level of folders: KB root → files or
    folders → files (inside folders). Nested folders (folder-inside-folder)
    are a UI-level non-feature — don't pass a folder's id as ``parent_id``
    here, or the resulting structure will be invisible in the file manager.

    When flattening source material for a KB, use the ``kb-indexing`` skill
    first to collapse deep trees into single-level folder names encoded in
    the filename (e.g. ``products／a.md``). See that skill's docs.
    """
    body: dict[str, Any] = {"parent_id": parent_id, "name": name}
    if description is not None:
        body["description"] = description
    return client.post(f"/knowledge-bases/{parent_id}/folders", json={"name": name, "parent_id": parent_id})


def create_node(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    name: str,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Generic create — ``parent_id=None`` creates a KB root, otherwise a folder.

    Kept for cases where the caller is iterating a tree and only has the parent
    id to decide. Prefer :func:`create_kb` / :func:`create_folder` in new code.
    """
    body: dict[str, Any] = {"name": name}
    if parent_id is not None:
        body["parent_id"] = parent_id
    if description is not None:
        body["description"] = description
    if parent_id is None:
        return client.post("/knowledge-bases", json=body)
    return client.post(f"/knowledge-bases/{parent_id}/folders", json={"name": name, "parent_id": parent_id})


def update_node(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    node_id: str,
    name: Optional[str] = None,
) -> dict:
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    return client.patch(f"/knowledge-bases/nodes/{node_id}", json=body)


def delete_node(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    node_id: str,
) -> Any:
    return client.delete(f"/knowledge-bases/nodes/{node_id}")


def upload_file(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    kb_id: str,
    file_path: str | Path,
    parent_id: str,
) -> dict:
    """Upload a single file. See :func:`upload_files` for the bulk form.

    ``parent_id`` is required (the KB root counts as a folder — pass its id to
    put a file at the top level).
    """
    return upload_files(
        client,
        organization_id=organization_id,
        workspace_id=workspace_id,
        kb_id=kb_id,
        file_paths=[file_path],
        parent_id=parent_id,
    )


def upload_files(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    kb_id: str,
    file_paths: List[str | Path],
    parent_id: str,
) -> dict:
    """Upload one or more files into a KB folder in a single request.

    Backend quirks baked in:

    - The form body is a single JSON-encoded field named ``form`` (Django
      Ninja's default for a ``Schema``-typed form param), not flattened.
    - Each file must include an explicit ``Content-Type``; httpx's default
      ``application/octet-stream`` gets rejected by the KB validator.
      :func:`_guess_mime` supplies a sensible default per extension.
    - The response is ``{"nodes": [{"node_id": "...", "status": "PENDING", ...}]}``.
    - Upload kicks off async indexing. Poll :func:`file_status` on the returned
      ``node_id`` values until each is ``READY``/``FAILED``.
    """
    if not parent_id:
        raise ValueError("parent_id is required (use the KB root id to upload at top level)")
    if not file_paths:
        raise ValueError("file_paths must contain at least one path")

    paths = [Path(p) for p in file_paths]
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(p)

    url = f"/knowledge-bases/{kb_id}/files:upload"
    open_handles = [p.open("rb") for p in paths]
    try:
        files = [("files[]", (p.name, fh, _guess_mime(p.name))) for p, fh in zip(paths, open_handles)]
        data = {"parent_id": parent_id}
        return client.post(url, files=files, data=data)
    finally:
        for fh in open_handles:
            fh.close()


def file_status(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    node_ids: List[str],
) -> list[dict]:
    """Batch-check indexing status for KB file nodes."""
    return client.post(
        "/knowledge-bases/files:status",
        json={"node_ids": node_ids},
    )


def read_file_content(
    client: CodeerClient,
    *,
    organization_id: str,
    workspace_id: str,
    kb_id: str,
    node_id: str,
) -> dict:
    return client.get(f"/knowledge-bases/{kb_id}/files/{node_id}/content")
