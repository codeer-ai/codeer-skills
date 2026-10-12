"""Offline project entry points."""
from pathlib import Path
import json

from ..project import Project, ProjectError, discover, now
from ._util import print_json


def register(sub):
    p = sub.add_parser("init", help="Initialize a local Agent development directory (offline)")
    p.add_argument("directory", nargs="?", default=".")
    p.add_argument("--name")
    p.set_defaults(func=run_init, no_client=True)
    p = sub.add_parser("status", help="Read local evidence; --refresh explicitly queries remote")
    p.add_argument("--refresh", action="store_true")
    p.set_defaults(func=run_status, no_client=True)
    p = sub.add_parser("validate", help="Validate local structure and references (offline)")
    p.set_defaults(func=run_validate, no_client=True)


def required():
    project = discover()
    if project is None:
        raise ProjectError("No project.toml found; run codeer init or use a resource command")
    return project


def run_init(args, client=None):
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "project.toml": f'schema_version = 1\nname = {json.dumps(args.name or root.name)}\n\n[target]\n# Bound by agent pull/apply after scope verification. No credentials here.\n\n[paths]\n# Override paths to adopt existing local files without moving them.\n',
        "README.md": "# Agent development project\n\nPut original SOP/PDF files in `sources/documents/`; list paths or URLs, purpose, version, authority and gaps in `sources/index.md`. Keep originals; extracted text is a separate derivative. Curated upload content belongs in `kb/`. Raw histories/AI Draft exports belong in `sources/history/<collection-id>/`.\n\nUse `codeer status` and `codeer validate` offline. Ask codeer-agent to build, cases, audit, apply, eval, improve, publish or observe. Existing Agents start with `agent pull --agent <id>`; import KB/Eval separately.\n\nAccepted behavior: `design/behavior-contract.md`; pending behavior: `design/behavior-contract.draft.md`; acceptance narrative: `design/acceptance.md`; machine acceptance scope: `design/acceptance.json`. Editable settings: `agent/settings.json`; the only prompt authority is `agent/instructions.md`. Eval design: `evals/design.json`. Reviews hold proposals and scope-bound confirmations. Each run/release has its own evidence directory.\n\nAppend important reasons and outcomes to `log.md`, linking actual reviews/runs/releases. Status derives from structured evidence, not this log. Unknown business decisions require confirmation; imports are not acceptance.\n",
        "log.md": "# Decision and change log\n\nAppend dated proposals, confirmations, apply and verification outcomes with reasons and evidence links. Do not record secrets or every command.\n",
        "sources/index.md": "# Source index\n\n| Source path or URL | Purpose | Version/date | Authority | Derivative/KB | Gaps |\n| --- | --- | --- | --- | --- | --- |\n",
        ".gitignore": ".codeer/\nsources/history/\nruns/\nreleases/*/raw*\n*.pdf\n",
    }
    created, updated = [], []
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(name)
        elif name == ".gitignore":
            existing, defaults = path.read_bytes(), content.encode("utf-8")
            # Append the defaults last so earlier negations cannot expose evidence.
            # Keep authored rules intact and leave an already-complete suffix alone.
            if not existing.endswith(defaults):
                path.write_bytes(existing + (b"\n" if existing and not existing.endswith(b"\n") else b"") + defaults)
                updated.append(name)
    (root / "sources/documents").mkdir(parents=True, exist_ok=True)
    Project.load(root)
    print_json({"root": str(root), "created": created, "updated": updated, "remote_mutations": 0})
    return 0


def run_status(args, client=None):
    project = required()
    if args.refresh:
        from ..client import CodeerClient
        from .. import agents
        with CodeerClient.from_env() as remote:
            scope = project.check_scope(remote)
            state = project.state()
            state["remote"] = agents.get(remote, scope["agent_id"]) if scope["agent_id"] else None
            if scope["agent_id"]:
                from ..evidence import snapshot
                history_id = agents.get_latest_history_id(remote, scope["agent_id"])
                if history_id:
                    state["last_anchor"] = snapshot(project, remote, history_id)
            state["queried_at"] = now()
            project.save_state(state)
    result = project.status()
    # Status is compact; raw run results remain in runs/.
    if result["latest_run"]:
        result["latest_run"] = {k: result["latest_run"].get(k) for k in ("id", "history_id", "status", "counts", "revision", "local_stale", "remote_stale_at_last_query", "comparison")}
    print_json(result)
    return 0


def run_validate(args, client=None):
    issues = required().validate()
    print_json({"structurally_valid": not issues, "issues": issues, "semantic_audit": "not performed"})
    return 1 if issues else 0
