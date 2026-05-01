"""Reusable: create (or reuse) a Codeer KB and upload all files from a directory.

Usage:
    $SKILL_DIR/scripts/codeer-python $SKILL_DIR/scripts/kb_upload.py \
        --kb-dir ./kb \
        --name "My KB" \
        --workspace <ws_id> \
        --org <org_id> \
        [--description "..."] \
        [--glob "*.md"] \
        [--out kb_ids.json]

Idempotent on KB name: if a KB with the same name already exists at the
workspace top level, it is reused and new files are uploaded into it
(existing files with the same `original_name` are NOT deduped — the backend
allows duplicates, so re-running this script after editing a single file
will create a duplicate node; delete the old one in the UI first if that
matters).

Writes a JSON object to stdout (and optionally to --out):
    {"kb_id": "...", "node_ids": [...], "name_to_id": {"01_foo.md": "...", ...}}
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codeer_cli import CodeerClient, kb  # noqa: E402

POLL_INTERVAL = 3
POLL_TIMEOUT = 600


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--kb-dir", required=True, help="Directory containing files to upload")
    ap.add_argument("--name", required=True, help="KB display name (idempotent)")
    ap.add_argument("--workspace", required=True, help="Workspace UUID")
    ap.add_argument("--org", required=True, help="Organization UUID")
    ap.add_argument("--description", default=None)
    ap.add_argument("--glob", default="*", help="File glob within --kb-dir (default: all files)")
    ap.add_argument("--out", default=None, help="Write the result JSON to this file too")
    ap.add_argument("--poll-timeout", type=int, default=POLL_TIMEOUT)
    args = ap.parse_args()

    kb_dir = Path(args.kb_dir).resolve()
    if not kb_dir.is_dir():
        _log(f"error: --kb-dir {kb_dir} is not a directory")
        return 2

    files = sorted(p for p in kb_dir.glob(args.glob) if p.is_file())
    if not files:
        _log(f"error: no files matched in {kb_dir} (glob={args.glob})")
        return 2
    _log(f"uploading {len(files)} files to KB '{args.name}'")

    with CodeerClient.from_env() as c:
        existing = kb.list_nodes(c, organization_id=args.org, workspace_id=args.workspace)
        match = next((n for n in existing if n.get("name") == args.name), None)
        if match:
            kb_id = match.get("node_id") or match.get("id")
            _log(f"reusing KB '{args.name}' id={kb_id}")
        else:
            created = kb.create_kb(
                c, organization_id=args.org, workspace_id=args.workspace,
                name=args.name, description=args.description,
            )
            kb_id = created.get("node_id") or created.get("id")
            _log(f"created KB '{args.name}' id={kb_id}")

        t0 = time.time()
        resp = kb.upload_files(
            c, organization_id=args.org, workspace_id=args.workspace,
            kb_id=kb_id, file_paths=[str(p) for p in files], parent_id=kb_id,
        )
        _log(f"upload returned in {time.time()-t0:.1f}s, {len(resp.get('nodes', []))} nodes")

        nodes = resp.get("nodes", [])
        node_ids = [n["node_id"] for n in nodes if n.get("node_id")]
        name_to_id = {n.get("original_name", "?"): n.get("node_id") for n in nodes}
        if not node_ids:
            _log("error: no node_ids returned from upload")
            return 1

        deadline = time.time() + args.poll_timeout
        last_status = []
        while time.time() < deadline:
            last_status = kb.file_status(
                c, organization_id=args.org, workspace_id=args.workspace, node_ids=node_ids,
            )
            counts: dict[str, int] = {}
            for s in last_status:
                k = s.get("status", "?").upper()
                counts[k] = counts.get(k, 0) + 1
            _log(f"  status: {counts}")
            terminal = sum(counts.get(k, 0) for k in ("READY", "FAILED", "ERROR"))
            if terminal >= len(node_ids):
                break
            time.sleep(POLL_INTERVAL)

        not_ready = [s for s in last_status if s.get("status", "").upper() != "READY"]
        if not_ready:
            _log(f"warning: {len(not_ready)} files NOT in READY state")
            for s in not_ready:
                _log(f"  {s}")

        result = {"kb_id": kb_id, "node_ids": node_ids, "name_to_id": name_to_id}
        out_text = json.dumps(result, indent=2, ensure_ascii=False)
        print(out_text)
        if args.out:
            Path(args.out).write_text(out_text + "\n")
            _log(f"wrote {args.out}")
        return 0 if not not_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
