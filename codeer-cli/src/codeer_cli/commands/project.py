"""Offline project entry points."""
from pathlib import Path
import json

from ..project import Project, ProjectError, discover, now
from ._util import print_json


def register(sub):
    p = sub.add_parser("init", help="Initialize a local Agent development directory (offline)")
    p.add_argument("directory", nargs="?", default=".")
    p.add_argument("--name")
    p.add_argument("--legacy", action="store_true", help="Initialize the previous single-target format for compatibility")
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
        "README.md": (
            "# Agent development project\n\n"
            "Tell the coding agent your goals and where the source material is. It reads first, "
            "summarizes intended behavior, recommends choices and asks only material unresolved questions. "
            "It maintains the design and pending decisions for you as discovery proceeds. You need not "
            "learn internal mode names or fill an Agent design template. Clear instructions can be "
            "recorded with their basis without another document approval; conflicts and new material "
            "choices still need a decision. Design decisions do not authorize remote writes or publication.\n\n"
            "Original SOP/PDF files belong in `sources/documents/`; the builder lists paths or URLs, "
            "purpose, version, authority and gaps in `sources/index.md`. Keep originals; extracted text "
            "is a separate derivative. Curated upload content belongs in `kb/`. Raw histories/AI Draft "
            "exports belong in `sources/history/<collection-id>/`.\n\n"
            "Use `codeer status` and `codeer validate` offline. Requests such as 'Build an Agent from "
            "this SOP' or 'Diagnose only this failed handoff' route to the appropriate skill workflow. "
            "Existing Agents start with `agent pull --agent <id>`; import KB/Eval separately.\n\n"
            "Builder-maintained design basis: `design/agent-design.md`; pending proposals: "
            "`design/agent-design.draft.md`; acceptance narrative: `design/acceptance.md`; "
            "machine acceptance scope: `design/acceptance.json`. Editable settings: `agent/settings.json`; "
            "the only prompt authority is `agent/instructions.md`. Eval design: `evals/design.json`. "
            "Reviews hold source/instruction evidence, proposals and scope-bound confirmations. "
            "Each run/release has its own evidence directory.\n\n"
            "These are new-project defaults. Use `[paths].design` for another design file; "
            "legacy `[paths].contract` remains supported. Without an explicit setting, an existing "
            "`design/behavior-contract.md` or `.draft.md` keeps the old pair in use. If both naming "
            "pairs exist, select the intended source with `[paths].design`. Pending proposals use "
            "the selected file's sibling `<stem>.draft.md`. Do not create a second design authority "
            "or move existing files just to follow the new name.\n\n"
            "Append important reasons and outcomes to `log.md`, linking actual reviews/runs/releases. "
            "Status derives from structured evidence, not this log. Unknown business decisions require "
            "confirmation; imports are not acceptance.\n"
        ),
        "log.md": "# Decision and change log\n\nAppend dated proposals, confirmations, apply and verification outcomes with reasons and evidence links. Do not record secrets or every command.\n",
        "sources/index.md": "# Source index\n\n| Source path or URL | Purpose | Version/date | Authority | Derivative/KB | Gaps |\n| --- | --- | --- | --- | --- | --- |\n",
        ".gitignore": ".codeer/\nsources/history/\nruns/\nreleases/*/raw*\n*.pdf\n",
    }
    existing = root / "project.toml"
    legacy = args.legacy or existing.exists() and Project.load(root).config["schema_version"] == 1
    if not legacy:
        files["project.toml"] = f'schema_version = 2\nname = {json.dumps(args.name or root.name)}\n\n[paths]\n# Override paths to adopt existing local files without moving them.\n'
        files[".gitignore"] = ".codeer/\nsources/history/\nruns/\nreleases/\n"
        del files["log.md"]
        # Continue an authored legacy log rather than creating a second authority.
        if not (root / "log.md").exists() and not any((root / "logs").glob("*.md")):
            files[f"logs/{now()[:7]}.md"] = "# Decisions and milestones\n\nRecord important proposals, confirmations, applied changes, verification and unresolved work with evidence links. Never record secrets or every command.\n"
        files["README.md"] = files["README.md"].replace("Each run/release has its own evidence directory.", "Eval evidence uses runs/<id>/; release receipts use unique releases/<timestamp>-<id>.json files.").replace("Append important reasons and outcomes to `log.md`", "Append important reasons and outcomes to `logs/YYYY-MM.md` (continue an existing `log.md`)")
        files["README.md"] += (
            "\nKeep this project in your own repository, e.g. `projects/<stable-name>/`. A repository README can link projects; shared AGENTS can document maintenance rules. Add `.codeer/` to the repository-root ignore too, protecting inherited profile selection. Init preserves parent files. No workspace registry is needed.\n\n"
            "Clone preserves portable content; `.codeer/` and ordinary runs/releases stay local. Keep required PDF/attachment originals in Git or controlled storage with verifiable bytes. Never commit credentials or raw customer histories.\n\n"
            "Connection: `codeer profile current`, then `codeer check`. Existing parent/global profiles or explicit environment variables can be reused. If missing, explicitly run `codeer profile add <name>` (non-default platform: `--api-base`); if unselected, use `codeer profile use <name>`. Correct environment overrides directly. Network failure means connection unverified.\n\n"
            "Explicitly configure `codeer agent bind --alias dev --new` or `--agent <id>`, then `codeer agent use dev`. Use global `--deployment <alias>` for one operation. Each deployment has separate target, resource mappings, bases and receipts. Targets are not committed.\n\n"
            "Declare originals/KB in `resources.json` (schema_version 1, attachments and knowledge objects keyed by stable local IDs). Settings reference `attachment:<id>`, `kb:<id>[/path]`, or `env:<VARIABLE>` for environment values/credentials. Upload attachments with `agent attachment --local-id <id> --dry-run` and KB with the matching local ID/directory/glob; apply only the reviewed --expect token.\n\n"
            "For takeover, pull observations and use `agent adopt --resource agent --keep-local|--remote --dry-run`, then the same command with --expect. Map case/tester/pairs IDs explicitly with --remote-id; never match by name. Declare a genuinely new case/tester with --remote-id new and --keep-local. Aligned, pending_apply and undecided content are distinct; unresolved fields block resource writes. Adoption performs no remote writes and is not business acceptance.\n"
        )
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
    project = args.project or required()
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
    issues = (args.project or required()).validate()
    print_json({"structurally_valid": not issues, "issues": issues, "semantic_audit": "not performed"})
    return 1 if issues else 0
