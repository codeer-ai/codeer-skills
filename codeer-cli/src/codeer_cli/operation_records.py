"""Small current receipts and repeated-observation deduplication."""
import hashlib
import uuid

from .project import fingerprint, now, read_json, save_json
from .evidence_references import TEXT, relative_references


def recovery_plan(plan):
    """Keep request, identity, local checkpoint and recovery-specific metadata.

    Comparison and three-way inputs are only preview diagnostics; the authoritative
    checkpoints remain in state. FAQ replay has its own full preimage contract.
    """
    return {key: value for key, value in plan.items()
            if key not in ("base", "local_base", "remote", "comparison")}


def import_snapshot(project, kind, value):
    path = project.local_dir / "imports" / fingerprint(value) / f"{kind}.json"
    if not path.exists():
        save_json(path, {**value, "retrieved_at": now()})
    return path


def mutable_receipt(project, entry, field="receipt", record=None):
    """Derive a live recovery record when fixed evidence cites the original.

    No evidence is reclassified; the derivative keeps the same request, IDs and
    unknown outcome, with an exact original hash/path as provenance.
    """
    path = project.resolve_path("receipt", entry[field])
    raw = path.read_bytes()
    record = read_json(path) if record is None else record
    digest = hashlib.sha256(raw).hexdigest()
    relative = str(path.relative_to(project.root))
    candidates = {relative: {"absolute": str(path), "hashes": {digest, fingerprint(read_json(path))}}}
    pinned = False
    for source in project.root.rglob("*"):
        if source.is_symlink() or not source.is_file() or source.suffix not in TEXT:
            continue
        name = source.relative_to(project.root)
        if name.parts[0] in (".git", "_plans") or name.parts[:2] == (".codeer", "deployments"):
            continue
        if relative_references(source.read_bytes(), source, project.root, candidates):
            pinned = True
            break
    if pinned:
        destination = project.local_dir / "receipts" / f"recovery-{uuid.uuid4().hex}.json"
        record["provenance"] = {"original_path": relative, "original_sha256": digest}
        save_json(destination, record)
        entry[field] = str(destination.relative_to(project.root))
        path = destination
    return path, record
