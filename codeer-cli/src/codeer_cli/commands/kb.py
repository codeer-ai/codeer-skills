from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .. import kb as kb_mod
from ._util import log, print_json, strip_noisy_fields, truncate, write_json

POLL_INTERVAL = 3
POLL_TIMEOUT = 600


def _add_crawl_config_args(parser):
    parser.add_argument("--config-json", default=None, help="JSON object for crawl_config")
    parser.add_argument("--limit", type=int, default=None, help="Maximum pages to crawl (backend max: 5000)")
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum crawl depth (backend max: 10)")
    parser.add_argument(
        "--include-path",
        action="append",
        dest="include_paths",
        default=None,
        help="Clean path pattern to include; repeatable. Supports * wildcards.",
    )
    parser.add_argument(
        "--exclude-path",
        action="append",
        dest="exclude_paths",
        default=None,
        help="Clean path pattern to exclude; repeatable. Supports * wildcards.",
    )
    parser.add_argument("--allow-subdomains", action="store_true", default=None,
                        help="Allow crawling subdomains of the start URL host")
    parser.add_argument("--allow-external-links", action="store_true", default=None,
                        help="Allow crawling links outside the start URL host")
    parser.add_argument("--ignore-query-parameters", action="store_true", dest="ignore_query_parameters", default=None,
                        help="Treat URLs that differ only by query string as the same page")
    parser.add_argument("--use-query-parameters", action="store_false", dest="ignore_query_parameters",
                        help="Treat URLs with different query strings as distinct pages")
    parser.add_argument("--ignore-sitemap", action="store_true", dest="ignore_sitemap", default=None,
                        help="Skip sitemap discovery")
    parser.add_argument("--use-sitemap", action="store_false", dest="ignore_sitemap",
                        help="Allow sitemap discovery")
    parser.add_argument("--only-main-content", action="store_true", dest="only_main_content", default=None,
                        help="Extract only the main content area")
    parser.add_argument("--include-page-chrome", action="store_false", dest="only_main_content",
                        help="Keep page navigation, footer, and other chrome")


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

    p = sub.add_parser("faq-list", help="List Context Object FAQ entries")
    p.add_argument("--context-object-id", type=int, default=None,
                   help="Filter to a KB file snapshot_object_id")
    p.add_argument("--limit", type=int, default=100, help="Page size, 1-200")
    p.add_argument("--offset", type=int, default=0, help="Page offset")
    p.add_argument("--full", action="store_true",
                   help="Print full FAQ metadata.")
    p.add_argument("--out", default=None,
                   help="Write full FAQ metadata to this file; stdout stays compact unless --full.")
    p.set_defaults(func=run_faq_list)

    p = sub.add_parser("faq-get", help="Get one Context Object FAQ entry")
    p.add_argument("faq_id", type=int)
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_faq_get)

    p = sub.add_parser("faq-create", help="Create a Context Object FAQ entry; run --dry-run first")
    p.add_argument("--context-object-id", type=int, required=True,
                   help="KB file snapshot_object_id from `codeer kb files`")
    p.add_argument("--question", required=True)
    p.add_argument("--range", dest="ranges", action="append", type=_parse_faq_range, default=None,
                   help="Reserve matching chunks that overlap START_LINE:END_LINE; repeatable")
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_faq_create)

    p = sub.add_parser("faq-update", help="Update a Context Object FAQ entry; run --dry-run first")
    p.add_argument("faq_id", type=int)
    p.add_argument("--context-object-id", type=int, default=None,
                   help="Move FAQ to a different KB file snapshot_object_id")
    p.add_argument("--question", default=None)
    p.add_argument("--range", dest="ranges", action="append", type=_parse_faq_range, default=None,
                   help="Replace reserved ranges with START_LINE:END_LINE; repeatable")
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_faq_update)

    p = sub.add_parser("faq-delete", help="Delete a Context Object FAQ entry; run --dry-run first")
    p.add_argument("faq_id", type=int)
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_faq_delete)

    p = sub.add_parser("crawl-create", help="Create a website-crawler KB folder; run --dry-run first")
    p.add_argument("--url", required=True, help="Starting URL to crawl")
    p.add_argument("--folder-name", default=None, help="KB folder name")
    _add_crawl_config_args(p)
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_crawl_create)

    p = sub.add_parser("crawl-update", help="Update a website crawl target; run --dry-run first")
    p.add_argument("--target-id", type=int, required=True)
    p.add_argument("--url", required=True, help="Updated starting URL")
    _add_crawl_config_args(p)
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_crawl_update)

    p = sub.add_parser("crawl-state", help="Read website crawl state for a crawler folder")
    p.add_argument("--folder-id", required=True, help="KnowledgeNode folder UUID")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_crawl_state)

    p = sub.add_parser("crawl-sync", help="Start a website crawl sync job; run --dry-run first")
    p.add_argument("--target-id", type=int, required=True)
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_crawl_sync)

    p = sub.add_parser("crawl-cancel", help="Cancel the active website crawl job; run --dry-run first")
    p.add_argument("--target-id", type=int, required=True)
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_crawl_cancel)

    p = sub.add_parser("crawl-failures", help="List failed pages for a website crawl job")
    p.add_argument("--job-id", type=int, required=True)
    p.add_argument("--status", default="DOWNLOAD_FAILED,FAILED")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_crawl_failures)


def _node_summary(node: dict) -> dict:
    return {
        "id": node.get("id") or node.get("node_id"),
        "node_id": node.get("node_id"),
        "snapshot_object_id": node.get("snapshot_object_id"),
        "name": node.get("name") or node.get("original_name"),
        "original_name": node.get("original_name"),
        "type": node.get("type") or node.get("node_type"),
        "status": node.get("status"),
        "created_at": node.get("created_at"),
        "updated_at": node.get("updated_at"),
        "description_preview": truncate(node.get("description") or "", 160),
        "children_count": node.get("children_count") or node.get("child_count"),
    }


def _faq_summary(faq: dict) -> dict:
    return {
        "id": faq.get("id"),
        "context_object_id": faq.get("context_object_id"),
        "question": faq.get("question"),
        "ranges": faq.get("ranges") or [],
        "has_question_embedding": faq.get("has_question_embedding"),
        "updated_at": faq.get("updated_at"),
    }


def _print_and_write(path: str | None, value: dict | list[dict]) -> None:
    print_json(value)
    write_json(path, value)


def _dry_run(path: str | None, result: dict) -> int:
    print_json(result)
    write_json(path, result)
    return 0


def _parse_faq_range(value: str) -> dict[str, int]:
    try:
        start_raw, end_raw = value.split(":", 1)
        start_line = int(start_raw)
        end_line = int(end_raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected START_LINE:END_LINE") from exc
    if start_line < 1 or end_line < 1:
        raise argparse.ArgumentTypeError("line numbers must be >= 1")
    if end_line < start_line:
        raise argparse.ArgumentTypeError("END_LINE must be >= START_LINE")
    return {"start_line": start_line, "end_line": end_line}


def _parse_config_json(config_json: str | None) -> dict | None:
    if not config_json:
        return None
    value = json.loads(config_json)
    if not isinstance(value, dict):
        raise SystemExit("--config-json must decode to a JSON object")
    return value


def _crawl_config_from_args(args) -> dict | None:
    config = _parse_config_json(args.config_json)
    has_config = config is not None
    if config is None:
        config = {}

    for key, attr in (
        ("limit", "limit"),
        ("maxDepth", "max_depth"),
        ("includePaths", "include_paths"),
        ("excludePaths", "exclude_paths"),
        ("allowSubdomains", "allow_subdomains"),
        ("allowExternalLinks", "allow_external_links"),
        ("ignoreQueryParameters", "ignore_query_parameters"),
        ("ignoreSitemap", "ignore_sitemap"),
        ("onlyMainContent", "only_main_content"),
    ):
        value = getattr(args, attr)
        if value is not None:
            config[key] = value
            has_config = True

    return config if has_config else None


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


def run_faq_list(args, client) -> int:
    faqs = kb_mod.list_context_obj_faqs(
        client,
        context_object_id=args.context_object_id,
        limit=args.limit,
        offset=args.offset,
    )
    full_faqs = strip_noisy_fields(faqs)
    write_json(args.out, full_faqs)
    print_json(full_faqs if args.full else [_faq_summary(f) for f in faqs])
    return 0


def run_faq_get(args, client) -> int:
    faq = strip_noisy_fields(kb_mod.get_context_obj_faq(client, faq_id=args.faq_id))
    _print_and_write(args.out, faq)
    return 0


def run_faq_create(args, client) -> int:
    body = {"context_object_id": args.context_object_id, "question": args.question}
    if args.ranges is not None:
        body["ranges"] = args.ranges
    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_faq_create",
                "method": "POST",
                "path": "/external/context-object-faqs",
                "body": body,
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    faq = strip_noisy_fields(
        kb_mod.create_context_obj_faq(
            client,
            context_object_id=args.context_object_id,
            question=args.question,
            ranges=args.ranges,
        )
    )
    _print_and_write(args.out, faq)
    return 0


def run_faq_update(args, client) -> int:
    if args.context_object_id is None and args.question is None and args.ranges is None:
        log("error: provide --context-object-id, --question, or --range")
        return 2

    body: dict[str, object] = {}
    if args.context_object_id is not None:
        body["context_object_id"] = args.context_object_id
    if args.question is not None:
        body["question"] = args.question
    if args.ranges is not None:
        body["ranges"] = args.ranges

    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_faq_update",
                "method": "PATCH",
                "path": f"/external/context-object-faqs/{args.faq_id}",
                "body": body,
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    faq = strip_noisy_fields(
        kb_mod.update_context_obj_faq(
            client,
            faq_id=args.faq_id,
            context_object_id=args.context_object_id,
            question=args.question,
            ranges=args.ranges,
        )
    )
    _print_and_write(args.out, faq)
    return 0


def run_faq_delete(args, client) -> int:
    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_faq_delete",
                "method": "DELETE",
                "path": f"/external/context-object-faqs/{args.faq_id}",
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(kb_mod.delete_context_obj_faq(client, faq_id=args.faq_id))
    _print_and_write(args.out, response)
    return 0


def run_crawl_create(args, client) -> int:
    crawl_config = _crawl_config_from_args(args)
    body: dict[str, object] = {"start_url": args.url}
    if args.folder_name is not None:
        body["folder_name"] = args.folder_name
    if crawl_config is not None:
        body["crawl_config"] = crawl_config

    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_crawl_create",
                "method": "POST",
                "path": "/external/knowledge-bases/website-crawls",
                "body": body,
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(
        kb_mod.create_website_crawl(
            client,
            start_url=args.url,
            folder_name=args.folder_name,
            crawl_config=crawl_config,
        )
    )
    _print_and_write(args.out, response)
    return 0


def run_crawl_update(args, client) -> int:
    crawl_config = _crawl_config_from_args(args)
    body: dict[str, object] = {"start_url": args.url}
    if crawl_config is not None:
        body["crawl_config"] = crawl_config

    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_crawl_update",
                "method": "PATCH",
                "path": f"/external/knowledge-bases/website-crawls/{args.target_id}",
                "body": body,
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(
        kb_mod.update_website_crawl(
            client,
            target_id=args.target_id,
            start_url=args.url,
            crawl_config=crawl_config,
        )
    )
    _print_and_write(args.out, response)
    return 0


def run_crawl_state(args, client) -> int:
    response = strip_noisy_fields(kb_mod.get_website_crawl_state(client, folder_id=args.folder_id))
    _print_and_write(args.out, response)
    return 0


def run_crawl_sync(args, client) -> int:
    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_crawl_sync",
                "method": "POST",
                "path": f"/external/knowledge-bases/website-crawls/{args.target_id}:sync",
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(kb_mod.sync_website_crawl(client, target_id=args.target_id))
    _print_and_write(args.out, response)
    return 0


def run_crawl_cancel(args, client) -> int:
    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_crawl_cancel",
                "method": "POST",
                "path": f"/external/knowledge-bases/website-crawls/{args.target_id}:cancel",
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(kb_mod.cancel_website_crawl(client, target_id=args.target_id))
    _print_and_write(args.out, response)
    return 0


def run_crawl_failures(args, client) -> int:
    response = strip_noisy_fields(
        kb_mod.get_website_crawl_failures(
            client,
            job_id=args.job_id,
            status=args.status,
            limit=args.limit,
            offset=args.offset,
        )
    )
    _print_and_write(args.out, response)
    return 0
