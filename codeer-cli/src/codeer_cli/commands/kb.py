from __future__ import annotations

import json
import time
from pathlib import Path

from .. import kb as kb_mod
from ._util import log, print_json, strip_noisy_fields, truncate, write_json

POLL_INTERVAL = 3
POLL_TIMEOUT = 600


def register(subparsers):
    k = subparsers.add_parser("kb", help="Knowledge base operations")
    sub = k.add_subparsers(dest="action", required=True)

    # codeer kb list
    p = sub.add_parser(
        "list",
        help="List knowledge bases. Defaults to compact KB node summaries for LLM context safety.",
    )
    p.add_argument("--parent-id", default=None, help="List children of this node (omit for top-level KBs)")
    p.add_argument("--full", action="store_true",
                   help="Print stripped full node metadata.")
    p.add_argument("--out", default=None,
                   help="Write stripped full node metadata to this file; stdout stays compact unless --full.")
    p.set_defaults(func=run_list)

    # codeer kb files
    p = sub.add_parser(
        "files",
        help="List files inside a knowledge base. Defaults to compact file summaries.",
    )
    p.add_argument("--kb-id", required=True, help="KB node UUID to list files from")
    p.add_argument("--full", action="store_true",
                   help="Print stripped full file metadata.")
    p.add_argument("--out", default=None,
                   help="Write stripped full file metadata to this file; stdout stays compact unless --full.")
    p.set_defaults(func=run_files)

    p = sub.add_parser("upload", help="Create/reuse KB and upload files from a directory; run --dry-run first")
    p.add_argument("--dir", required=True, help="Directory containing files to upload")
    p.add_argument("--name", required=True, help="KB display name (idempotent on name)")
    p.add_argument("--description", default=None)
    p.add_argument("--glob", default="*", help="File glob within --dir (default: all files)")
    p.add_argument("--dry-run", action="store_true",
                   help="Validate directory/glob and print intended upload without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.add_argument("--poll-timeout", type=int, default=POLL_TIMEOUT)
    p.set_defaults(func=run_upload)


def _node_summary(node: dict) -> dict:
    return {
        "id": node.get("id") or node.get("node_id"),
        "node_id": node.get("node_id"),
        "name": node.get("name") or node.get("original_name"),
        "original_name": node.get("original_name"),
        "type": node.get("type") or node.get("node_type"),
        "status": node.get("status"),
        "created_at": node.get("created_at"),
        "updated_at": node.get("updated_at"),
        "description_preview": truncate(node.get("description") or "", 160),
        "children_count": node.get("children_count") or node.get("child_count"),
    }


def run_list(args, client) -> int:
    workspace_id, organization_id = client.resolve_scope()
    nodes = kb_mod.list_nodes(
        client, organization_id=organization_id, workspace_id=workspace_id,
        parent_id=getattr(args, "parent_id", None),
    )
    full_nodes = strip_noisy_fields(nodes)
    write_json(args.out, full_nodes)
    print_json(full_nodes if args.full else [_node_summary(n) for n in nodes])
    return 0


def run_files(args, client) -> int:
    workspace_id, organization_id = client.resolve_scope()
    nodes = kb_mod.list_nodes(
        client, organization_id=organization_id, workspace_id=workspace_id,
        parent_id=args.kb_id,
    )
    full_nodes = strip_noisy_fields(nodes)
    write_json(args.out, full_nodes)
    print_json(full_nodes if args.full else [_node_summary(n) for n in nodes])
    return 0


def run_upload(args, client) -> int:
    workspace_id, organization_id = client.resolve_scope()
    kb_dir = Path(args.dir).resolve()
    if not kb_dir.is_dir():
        log(f"error: --dir {kb_dir} is not a directory")
        return 2

    files = sorted(p for p in kb_dir.glob(args.glob) if p.is_file())
    if not files:
        log(f"error: no files matched in {kb_dir} (glob={args.glob})")
        return 2

    if args.dry_run:
        result = {
            "dry_run": True,
            "operation": "kb_upload",
            "workspace_id": workspace_id,
            "organization_id": organization_id,
            "kb_name": args.name,
            "description": args.description,
            "directory": str(kb_dir),
            "glob": args.glob,
            "file_count": len(files),
            "files": [str(p) for p in files],
            "would_write_server_state": True,
            "next_step": "Review this summary, then rerun without --dry-run after approval.",
        }
        out_text = json.dumps(result, indent=2, ensure_ascii=False)
        print(out_text)
        if args.out:
            Path(args.out).write_text(out_text + "\n")
            log(f"wrote {args.out}")
        return 0

    log(f"uploading {len(files)} files to KB '{args.name}'")

    existing = kb_mod.list_nodes(client, organization_id=organization_id, workspace_id=workspace_id)
    match = next((n for n in existing if n.get("name") == args.name), None)
    if match:
        kb_id = match.get("node_id") or match.get("id")
        log(f"reusing KB '{args.name}' id={kb_id}")
    else:
        created = kb_mod.create_kb(
            client, organization_id=organization_id, workspace_id=workspace_id,
            name=args.name, description=args.description,
        )
        kb_id = created.get("node_id") or created.get("id")
        log(f"created KB '{args.name}' id={kb_id}")

    t0 = time.time()
    resp = kb_mod.upload_files(
        client, organization_id=organization_id, workspace_id=workspace_id,
        kb_id=kb_id, file_paths=[str(p) for p in files], parent_id=kb_id,
    )
    log(f"upload returned in {time.time()-t0:.1f}s, {len(resp.get('nodes', []))} nodes")

    nodes = resp.get("nodes", [])
    node_ids = [n["node_id"] for n in nodes if n.get("node_id")]
    name_to_id = {n.get("original_name", "?"): n.get("node_id") for n in nodes}
    if not node_ids:
        log("error: no node_ids returned from upload")
        return 1

    deadline = time.time() + args.poll_timeout
    last_status = []
    while time.time() < deadline:
        last_status = kb_mod.file_status(
            client, organization_id=organization_id, workspace_id=workspace_id, node_ids=node_ids,
        )
        counts: dict[str, int] = {}
        for s in last_status:
            k = s.get("status", "?").upper()
            counts[k] = counts.get(k, 0) + 1
        log(f"  status: {counts}")
        terminal = sum(counts.get(k, 0) for k in ("READY", "FAILED", "ERROR"))
        if terminal >= len(node_ids):
            break
        time.sleep(POLL_INTERVAL)

    not_ready = [s for s in last_status if s.get("status", "").upper() != "READY"]
    if not_ready:
        log(f"warning: {len(not_ready)} files NOT in READY state")
        for s in not_ready:
            log(f"  {s}")

    result = {"kb_id": kb_id, "node_ids": node_ids, "name_to_id": name_to_id}
    out_text = json.dumps(result, indent=2, ensure_ascii=False)
    print(out_text)
    if args.out:
        Path(args.out).write_text(out_text + "\n")
        log(f"wrote {args.out}")
    return 0 if not not_ready else 1
