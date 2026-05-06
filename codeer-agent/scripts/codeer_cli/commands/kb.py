from __future__ import annotations

import json
import time
from pathlib import Path

from .. import kb as kb_mod
from ._util import log

POLL_INTERVAL = 3
POLL_TIMEOUT = 600


def register(subparsers):
    k = subparsers.add_parser("kb", help="Knowledge base operations")
    sub = k.add_subparsers(dest="action", required=True)

    # codeer kb list
    p = sub.add_parser("list", help="List knowledge bases in workspace")
    p.add_argument("--workspace", required=True, help="Workspace UUID")
    p.add_argument("--org", required=True, help="Organization UUID")
    p.set_defaults(func=run_list)

    p = sub.add_parser("upload", help="Create/reuse KB and upload files from a directory")
    p.add_argument("--dir", required=True, help="Directory containing files to upload")
    p.add_argument("--name", required=True, help="KB display name (idempotent on name)")
    p.add_argument("--workspace", required=True, help="Workspace UUID")
    p.add_argument("--org", required=True, help="Organization UUID")
    p.add_argument("--description", default=None)
    p.add_argument("--glob", default="*", help="File glob within --dir (default: all files)")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.add_argument("--poll-timeout", type=int, default=POLL_TIMEOUT)
    p.set_defaults(func=run_upload)


def run_list(args, client) -> int:
    nodes = kb_mod.list_nodes(client, organization_id=args.org, workspace_id=args.workspace)
    print(json.dumps(nodes, ensure_ascii=False, indent=2, default=str))
    return 0


def run_upload(args, client) -> int:
    kb_dir = Path(args.dir).resolve()
    if not kb_dir.is_dir():
        log(f"error: --dir {kb_dir} is not a directory")
        return 2

    files = sorted(p for p in kb_dir.glob(args.glob) if p.is_file())
    if not files:
        log(f"error: no files matched in {kb_dir} (glob={args.glob})")
        return 2
    log(f"uploading {len(files)} files to KB '{args.name}'")

    existing = kb_mod.list_nodes(client, organization_id=args.org, workspace_id=args.workspace)
    match = next((n for n in existing if n.get("name") == args.name), None)
    if match:
        kb_id = match.get("node_id") or match.get("id")
        log(f"reusing KB '{args.name}' id={kb_id}")
    else:
        created = kb_mod.create_kb(
            client, organization_id=args.org, workspace_id=args.workspace,
            name=args.name, description=args.description,
        )
        kb_id = created.get("node_id") or created.get("id")
        log(f"created KB '{args.name}' id={kb_id}")

    t0 = time.time()
    resp = kb_mod.upload_files(
        client, organization_id=args.org, workspace_id=args.workspace,
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
            client, organization_id=args.org, workspace_id=args.workspace, node_ids=node_ids,
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
