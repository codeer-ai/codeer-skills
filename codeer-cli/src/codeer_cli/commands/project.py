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
    p.add_argument("--full", action="store_true", help="Include per-pair evidence issues and complete recorded run details")
    p.add_argument("--human", action="store_true", help="Show a readable summary; default JSON output is unchanged")
    p.set_defaults(func=run_status, no_client=True)
    p = sub.add_parser("validate", help="Validate local structure and references (offline)")
    p.set_defaults(func=run_validate, no_client=True)
    p = sub.add_parser("clean", help="Offline cleanup of completed, unreferenced machine history in one binding")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--expect")
    p.add_argument("--older-than", help="Minimum age, e.g. 30d")
    p.add_argument("--keep", help="Persistently retain an existing project file/directory")
    p.add_argument("--reason", help="Reason for manual retention")
    p.set_defaults(func=run_clean, no_client=True)


def run_clean(args, client=None):
    from ..clean import clean, keep
    project = args.project or required()
    if args.keep:
        if args.dry_run or args.expect or args.older_than:
            raise ProjectError("--keep is a separate local operation; omit cleanup flags")
        result = keep(project, args.keep, args.reason)
    else:
        if args.reason:
            raise ProjectError("--reason requires --keep")
        result = clean(project, dry_run=args.dry_run, expected=args.expect, older_than=args.older_than)
    print_json(result)
    return 0


def required():
    project = discover()
    if project is None:
        raise ProjectError("No project.toml found; run codeer init or use a resource command")
    return project


def project_readme():
    log = "logs/YYYY-MM.md (continue an existing log.md)"
    return f"""# Agent development project

Describe the people, tasks and outcomes this Agent should support. The coding
agent reads your sources, explains gaps and recommends the next step. Use your
working language; the Agent's customer language may differ.

## Start here

- `project.toml`: project identity and configured paths; existing paths win.
- `sources/index.md`: originals, applicable versions, authority and gaps.
- `design/agent-design.md` and sibling `.draft.md`: established behavior / open decisions.
- `agent/instructions.md`, `agent/settings.json`, `kb/`: implementation; one editable prompt.
- `evals/cases.draft.md`: unresolved candidates; `evals/design.json`: admitted cases and judgments.
- `reviews/batches/<batch-id>/report.md`: material findings, decisions and evidence links.
- `{log}`: concise milestones; `runs/<id>/`: exact test evidence.

These files grow with the work; init does not create a finished Agent. Reuse
configured and legacy design/review paths. Additional analysis is welcome when
its purpose and relationship to the primary files are clear. Generated reading
copies are not another editable authority. Keep current status out of multiple
hand-maintained tables; inspect the recorded evidence behind old prose.

## Continue

Run `codeer status --human` for offline guidance and `codeer validate` for
structure; default `codeer status` remains JSON. Tell the coding agent to build,
test or diagnose in ordinary language. It should explain progress, missing
prerequisites, the recommended next action and what finishes it. A normal test
request includes results and initial diagnosis; you can request export only.

Preserve originals and local `.codeer/` mappings/recovery receipts. Do not commit
credentials or raw customer histories. Skill project documentation owns full
setup, deployment and evidence rules. Inspect the actual CLI/skill revision;
updating tools does not deploy an Agent or approve new operations. Show reviewed
diffs before remote writes, reuse existing authorization and authorize publication
separately. Existing projects need no reinitialization or bulk migration.
"""


def run_init(args, client=None):
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "project.toml": f'schema_version = 2\nname = {json.dumps(args.name or root.name)}\n\n[paths]\n# Override paths to adopt existing local files without moving them.\n',
        "README.md": project_readme(),
        "sources/index.md": "# Source index\n\n| Source path or URL | Purpose | Version/date | Authority | Derivative/KB | Gaps |\n| --- | --- | --- | --- | --- | --- |\n",
        ".gitignore": ".codeer/\nsources/history/\nruns/\nreleases/\n",
    }
    existing = root / "project.toml"
    if existing.exists():
        Project.load(root)
    if not (root / "log.md").exists() and not any((root / "logs").glob("*.md")):
        files[f"logs/{now()[:7]}.md"] = "# Decisions and milestones\n\nRecord important proposals, confirmations, applied changes, verification and unresolved work with evidence links. Never record secrets or every command.\n"
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
    if not args.full and result["eval_design"]:
        def compact_gap(gap):
            return {k: v for k, v in gap.items() if k != "affected_pairs"} | {"affected_pair_count": len(gap["affected_pairs"])}
        gaps = result["eval_design"]["evidence_gaps"]
        result["evidence_issue_count"] = len(result.pop("evidence_issues"))
        result["eval_design"] = {k: v for k, v in result["eval_design"].items()
                                 if k in ("design_complete", "apply_ready", "pair_count")}
        result["eval_design"]["evidence_gaps"] = [compact_gap(g) for g in gaps]
        if result["next_action"]["code"] == "verify_evidence_contracts":
            result["next_action"]["evidence"] = result["eval_design"]["evidence_gaps"]
    if result["latest_run"] and not args.full:
        result["latest_run"] = {k: result["latest_run"].get(k) for k in ("id", "history_id", "status", "counts", "revision", "local_stale", "environment_stale", "remote_stale_at_last_query", "comparison")}
    if args.human:
        print(f"Project: {result['project']} (binding: {result.get('binding') or 'unselected'})")
        print(f"Offline evidence; last remote query: {result.get('last_remote_query') or 'none'}")
        run = result.get("latest_run")
        print(f"Latest run: {run['id']} — {run['status']} {run.get('counts') or {}}" if run else "Latest run: none recorded")
        if run and run.get("environment_stale"):
            print("Run environment differs from the current referenced variables.")
        issues = sum(len(result.get(k, [])) for k in ("structural_issues", "design_issues", "operation_issues"))
        print(f"Local issues: {issues}; evidence issues: {result.get('evidence_issue_count', len(result.get('evidence_issues', [])))}")
        print(f"Next: {result['next_action']['action']}")
        print(f"Done when: {result['next_action']['completion_condition']}")
        print("This summary does not check live readiness or approve changes.")
    else:
        print_json(result)
    return 0


def run_validate(args, client=None):
    validation = (args.project or required()).validation()
    issues = validation["structural_issues"] + validation["design_issues"] + validation["evidence_issues"] + validation["operation_issues"]
    print_json({"structurally_valid": not validation["structural_issues"], "issues": issues,
                **validation, "semantic_audit": "not performed"})
    return 1 if issues else 0
