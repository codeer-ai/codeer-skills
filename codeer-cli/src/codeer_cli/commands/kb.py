from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .. import kb as kb_mod
from ..client import AuthError, CodeerError
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

    # codeer kb export
    p = sub.add_parser(
        "export",
        help="Export available KB file snapshot contents as local UTF-8 Markdown files.",
    )
    p.add_argument("--node-id", required=True, help="File, folder, or KB root node UUID to export")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--file", help="Local output path for single-file export")
    target.add_argument("--dir", help="Local output directory for recursive folder export")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing export file(s). Without this flag, the export is blocked before writing.",
    )
    p.add_argument("--full", action="store_true", help="Print the full per-file export manifest.")
    p.add_argument(
        "--out",
        default=None,
        help="Write the full export manifest JSON to this file; stdout stays compact unless --full.",
    )
    p.set_defaults(func=run_export)

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

    p = sub.add_parser("node-rename", help="Rename a KB root, folder, or file node; run --dry-run first")
    p.add_argument("--node-id", required=True, help="KnowledgeNode UUID")
    p.add_argument("--name", required=True, help="New display name")
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_node_rename)

    p = sub.add_parser("node-delete", help="Delete a KB root, folder, or file node and descendants; run --dry-run first")
    p.add_argument("--node-id", required=True, help="KnowledgeNode UUID")
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_node_delete)

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
    _add_faq_range_args(p)
    p.add_argument("--dry-run", action="store_true",
                   help="Print intended request without writing server state.")
    p.add_argument("--out", default=None, help="Write result JSON to this file too")
    p.set_defaults(func=run_faq_create)

    p = sub.add_parser("faq-update", help="Update a Context Object FAQ entry; run --dry-run first")
    p.add_argument("faq_id", type=int)
    p.add_argument("--context-object-id", type=int, default=None,
                   help="Move FAQ to a different KB file snapshot_object_id")
    p.add_argument("--question", default=None)
    _add_faq_range_args(p, verb="Replace")
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


def _add_faq_range_args(parser, *, verb: str = "Reserve") -> None:
    parser.add_argument(
        "--range",
        dest="ranges",
        action="append",
        type=_parse_faq_range,
        default=None,
        help=(
            f"{verb} matching passages as "
            "START_LINE:START_COLUMN-END_LINE:END_COLUMN; repeatable"
        ),
    )


def _parse_faq_range(value: str) -> dict[str, int]:
    try:
        start_raw, end_raw = value.split("-", 1)
        start_line_raw, start_column_raw = start_raw.split(":", 1)
        end_line_raw, end_column_raw = end_raw.split(":", 1)
        faq_range = {
            "start_line": int(start_line_raw),
            "start_column": int(start_column_raw),
            "end_line": int(end_line_raw),
            "end_column": int(end_column_raw),
        }
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "expected START_LINE:START_COLUMN-END_LINE:END_COLUMN"
        ) from exc
    _validate_faq_range_position(faq_range)
    return faq_range


def _validate_faq_range_position(faq_range: dict[str, int]) -> None:
    start_line = faq_range["start_line"]
    end_line = faq_range["end_line"]
    start_column = faq_range["start_column"]
    end_column = faq_range["end_column"]
    if start_line < 1 or end_line < 1:
        raise argparse.ArgumentTypeError("line numbers must be >= 1")
    if start_column < 0 or end_column < 0:
        raise argparse.ArgumentTypeError("column numbers must be >= 0")
    if (end_line, end_column) < (start_line, start_column):
        raise argparse.ArgumentTypeError("end position must be >= start position")


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


_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _safe_export_component(value: str | None, *, fallback: str) -> str:
    """Return one portable path component without allowing path traversal."""
    raw = (value or "").strip()
    cleaned = "".join(
        "_" if ord(char) < 32 or char in '<>:"/\\|?*' else char
        for char in raw
    ).rstrip(" .")
    if not cleaned or cleaned in {".", ".."}:
        cleaned = fallback
    if cleaned.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned


def _snapshot_filename(name: str | None, *, node_id: str) -> str:
    safe_name = _safe_export_component(name, fallback=f"file-{node_id[:8]}")
    if Path(safe_name).suffix.lower() not in {".md", ".markdown"}:
        safe_name = f"{safe_name}.md"
    return safe_name


def _unique_export_component(component: str, *, node_id: str, used: set[str]) -> str:
    candidate = component
    index = 1
    while candidate.casefold() in used:
        suffix = f"__{node_id[:8]}" if index == 1 else f"__{node_id[:8]}-{index}"
        path = Path(component)
        candidate = f"{path.stem}{suffix}{path.suffix}" if path.suffix else f"{component}{suffix}"
        index += 1
    used.add(candidate.casefold())
    return candidate


def _collect_export_files(
    client,
    *,
    organization_id: str,
    workspace_id: str,
    root_node_id: str,
) -> tuple[list[dict], list[dict]]:
    """Walk the KB tree and assign deterministic, collision-safe local paths."""
    pending: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [(root_node_id, (), ())]
    seen: set[str] = set()
    files: list[dict] = []
    issues: list[dict] = []

    while pending:
        parent_id, output_parts, source_parts = pending.pop()
        if parent_id in seen:
            issues.append({"node_id": parent_id, "reason": "cycle_or_duplicate_folder"})
            continue
        seen.add(parent_id)

        nodes = kb_mod.list_nodes(
            client,
            organization_id=organization_id,
            workspace_id=workspace_id,
            parent_id=parent_id,
        )
        nodes = sorted(
            nodes,
            key=lambda node: (
                str(node.get("node_type") or node.get("type") or "").upper() != "FOLDER",
                str(node.get("name") or node.get("original_name") or "").casefold(),
                str(node.get("id") or node.get("node_id") or ""),
            ),
        )
        used_components: set[str] = set()
        child_folders: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []

        for node in nodes:
            node_id = str(node.get("id") or node.get("node_id") or "")
            node_type = str(node.get("node_type") or node.get("type") or "").upper()
            node_name = str(node.get("name") or node.get("original_name") or "")
            if not node_id:
                issues.append({"name": node_name, "reason": "missing_node_id"})
                continue

            if node_type == "FOLDER":
                component = _safe_export_component(node_name, fallback=f"folder-{node_id[:8]}")
                component = _unique_export_component(component, node_id=node_id, used=used_components)
                child_folders.append(
                    (
                        node_id,
                        (*output_parts, component),
                        (*source_parts, node_name or node_id),
                    )
                )
                continue

            if node_type != "FILE":
                issues.append({"node_id": node_id, "name": node_name, "reason": f"unknown_node_type:{node_type}"})
                continue

            filename = _snapshot_filename(node_name, node_id=node_id)
            filename = _unique_export_component(filename, node_id=node_id, used=used_components)
            files.append(
                {
                    "node_id": node_id,
                    "name": node_name,
                    "source_path": "/".join((*source_parts, node_name or node_id)),
                    "server_status": str(node.get("status") or "").upper() or None,
                    "relative_output_path": str(Path(*output_parts, filename)),
                }
            )

        pending.extend(reversed(child_folders))

    files.sort(key=lambda item: item["relative_output_path"].casefold())
    return files, issues


def _compact_export_result(result: dict) -> dict:
    problems = [
        {
            "node_id": item.get("node_id"),
            "source_path": item.get("source_path"),
            "result": item.get("result"),
            "reason": item.get("reason"),
        }
        for item in result.get("files", [])
        if item.get("result") != "exported"
    ]
    return {
        key: result.get(key)
        for key in (
            "operation",
            "mode",
            "node_id",
            "directory",
            "output_file",
            "server_status",
            "exported_while_not_ready",
            "complete",
            "file_count",
            "exported_count",
            "non_ready_exported_count",
            "skipped_count",
            "failed_count",
            "issue_count",
            "reason",
        )
    } | {
        "problems": problems[:20],
        "additional_problem_count": max(0, len(problems) - 20),
        "blocked_paths": result.get("blocked_paths", [])[:20],
        "additional_blocked_path_count": max(0, len(result.get("blocked_paths", [])) - 20),
    }


def _print_export_result(args, result: dict) -> None:
    write_json(args.out, result)
    print_json(result if args.full else _compact_export_result(result))


def _read_export_content(
    client,
    *,
    organization_id: str,
    workspace_id: str,
    item: dict,
) -> str | None:
    try:
        response = kb_mod.read_file_content(
            client,
            organization_id=organization_id,
            workspace_id=workspace_id,
            node_id=item["node_id"],
        )
    except AuthError:
        raise
    except CodeerError as exc:
        if exc.status not in {400, 404}:
            raise
        item.update(result="failed", reason=f"api_error:{exc.status}:{exc.message}")
        return None

    response_status = str(response.get("status") or "").upper()
    response_name = str(response.get("name") or "")
    content = response.get("content")
    item["server_status"] = response_status or item.get("server_status")
    if response_name:
        item["name"] = response_name
    item.setdefault("source_path", response_name or item["node_id"])
    if content is None:
        item.update(
            result="skipped",
            reason=f"content_unavailable:{response_status or 'UNKNOWN'}",
        )
        return None
    if not isinstance(content, str):
        item.update(result="failed", reason="content_is_not_text")
        return None
    return content


def _write_export_content(target: Path, content: str, item: dict) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        item.update(result="failed", reason=f"local_write_error:{exc}")
        return
    item.update(
        result="exported",
        bytes_written=len(content.encode("utf-8")),
        exported_while_not_ready=item.get("server_status") != "READY",
    )


def _export_counts(files: list[dict]) -> dict:
    exported_count = sum(item.get("result") == "exported" for item in files)
    return {
        "file_count": len(files),
        "exported_count": exported_count,
        "non_ready_exported_count": sum(
            item.get("result") == "exported" and item.get("server_status") != "READY"
            for item in files
        ),
        "skipped_count": sum(item.get("result") == "skipped" for item in files),
        "failed_count": sum(item.get("result") == "failed" for item in files),
    }


def _run_file_export(args, client, *, workspace_id: str, organization_id: str) -> int:
    output_file = Path(args.file).expanduser().resolve()
    if args.out and Path(args.out).expanduser().resolve() == output_file:
        log("error: --out manifest path must differ from --file content path")
        return 2
    if output_file.exists() and (output_file.is_dir() or not args.overwrite):
        log("error: single-file export blocked before writing; use --overwrite only if replacement is intended")
        return 2

    existing_parent = output_file.parent
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent
    if existing_parent.exists() and not existing_parent.is_dir():
        log(f"error: output parent {existing_parent} is not a directory")
        return 2

    item = {
        "node_id": args.node_id,
        "output_path": str(output_file),
    }
    content = _read_export_content(
        client,
        organization_id=organization_id,
        workspace_id=workspace_id,
        item=item,
    )
    if content is not None:
        _write_export_content(output_file, content, item)

    counts = _export_counts([item])
    complete = counts["skipped_count"] == 0 and counts["failed_count"] == 0
    result = {
        "operation": "kb_export",
        "mode": "file",
        "node_id": args.node_id,
        "directory": str(output_file.parent),
        "output_file": str(output_file),
        "server_status": item.get("server_status"),
        "exported_while_not_ready": item.get("exported_while_not_ready", False),
        "complete": complete,
        **counts,
        "issue_count": 0,
        "issues": [],
        "files": [item],
    }
    _print_export_result(args, result)
    return 0 if complete else 1


def _run_folder_export(args, client, *, workspace_id: str, organization_id: str) -> int:
    output_dir = Path(args.dir).expanduser().resolve()
    if output_dir.exists() and not output_dir.is_dir():
        log(f"error: --dir {output_dir} exists and is not a directory")
        return 2

    files, issues = _collect_export_files(
        client,
        organization_id=organization_id,
        workspace_id=workspace_id,
        root_node_id=args.node_id,
    )

    blocked_paths: list[str] = []
    for item in files:
        target = output_dir / item["relative_output_path"]
        if target.exists() and (target.is_dir() or not args.overwrite):
            blocked_paths.append(str(target))
        parent = target.parent
        while parent != output_dir:
            if parent.exists() and not parent.is_dir():
                blocked_paths.append(str(parent))
                break
            parent = parent.parent

    if blocked_paths:
        result = {
            "operation": "kb_export",
            "mode": "folder",
            "node_id": args.node_id,
            "directory": str(output_dir),
            "output_file": None,
            "complete": False,
            "file_count": len(files),
            "exported_count": 0,
            "non_ready_exported_count": 0,
            "skipped_count": 0,
            "failed_count": len(set(blocked_paths)),
            "issue_count": len(issues),
            "issues": issues,
            "files": [],
            "blocked_paths": sorted(set(blocked_paths)),
            "reason": "existing_paths_require_overwrite_or_conflict_with_directories",
        }
        _print_export_result(args, result)
        log("error: export blocked before writing; use --overwrite only if replacing existing files is intended")
        return 2

    for item in files:
        target = output_dir / item["relative_output_path"]
        content = _read_export_content(
            client,
            organization_id=organization_id,
            workspace_id=workspace_id,
            item=item,
        )
        if content is not None:
            _write_export_content(target, content, item)

    counts = _export_counts(files)
    complete = not issues and counts["skipped_count"] == 0 and counts["failed_count"] == 0
    result = {
        "operation": "kb_export",
        "mode": "folder",
        "node_id": args.node_id,
        "directory": str(output_dir),
        "output_file": None,
        "complete": complete,
        **counts,
        "issue_count": len(issues),
        "issues": issues,
        "files": files,
    }
    _print_export_result(args, result)
    return 0 if complete else 1


def run_export(args, client) -> int:
    workspace_id, organization_id = client.resolve_scope()
    if args.file:
        return _run_file_export(
            args,
            client,
            workspace_id=workspace_id,
            organization_id=organization_id,
        )
    return _run_folder_export(
        args,
        client,
        workspace_id=workspace_id,
        organization_id=organization_id,
    )


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


def run_node_rename(args, client) -> int:
    workspace_id, organization_id = client.resolve_scope()
    path = f"/external/knowledge-bases/nodes/{args.node_id}"
    body = {"name": args.name}
    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_node_rename",
                "method": "PATCH",
                "path": path,
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "node_id": args.node_id,
                "body": body,
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(
        kb_mod.update_node(
            client,
            organization_id=organization_id,
            workspace_id=workspace_id,
            node_id=args.node_id,
            name=args.name,
        )
    )
    _print_and_write(args.out, response)
    return 0


def run_node_delete(args, client) -> int:
    workspace_id, organization_id = client.resolve_scope()
    path = f"/external/knowledge-bases/nodes/{args.node_id}"
    if args.dry_run:
        return _dry_run(
            args.out,
            {
                "dry_run": True,
                "operation": "kb_node_delete",
                "method": "DELETE",
                "path": path,
                "workspace_id": workspace_id,
                "organization_id": organization_id,
                "node_id": args.node_id,
                "deletes_descendants": True,
                "would_write_server_state": True,
                "next_step": "Review this summary, then rerun without --dry-run after approval.",
            },
        )

    response = strip_noisy_fields(
        kb_mod.delete_node(
            client,
            organization_id=organization_id,
            workspace_id=workspace_id,
            node_id=args.node_id,
        )
    )
    _print_and_write(args.out, response)
    return 0


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
