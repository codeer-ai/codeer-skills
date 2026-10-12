"""Codeer CLI — unified interface for agent lifecycle operations.

    codeer check
    codeer skill list|install|uninstall
    codeer agent list|get|apply|diff|versions
    codeer model list
    codeer kb list|files|export|upload|node-rename|node-delete|faq-list|faq-get|faq-create|faq-update|faq-delete
    codeer eval list|label-list|label-create|label-update|label-delete|case-update|case-delete|evaluators|evaluator-create|evaluator-update|run|export|reconcile|cases-apply|rubrics|rubrics-apply
    codeer history list|get|conversations|ai-drafts|negative-feedback|create|send
"""

from __future__ import annotations

import argparse
import json
import sys

from .client import AuthError, CodeerClient, CodeerError
from .commands import check, skill
from .histories import HistoryExportError
from .project import ProjectError, discover


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Codeer CLI — self-describing agent lifecycle tools.",
        epilog="""\
Safe workflow for coding agents:
  codeer skill list
  codeer skill install codeer-agent --target codex --dry-run
  codeer check --json
  codeer model list --type text
  codeer agent list
  codeer agent get <agent-id> --full
  codeer kb list
  codeer kb files --kb-id <kb-id>
  codeer kb export --node-id <file-id> --file guide.md
  codeer kb export --node-id <folder-id> --dir kb-export
  codeer eval list --agent <agent-id>
  codeer eval label-list
  codeer eval case-update --case <case-id> --input "..." --dry-run
  codeer eval evaluators
  codeer agent diff --agent <agent-id> --from-version <n> --to-version <n>
  codeer eval reconcile --agent <agent-id> --manifest .codeer/eval_cases.json

Preview mutations before applying:
  codeer agent apply --payload agent.json --dry-run
  codeer eval case-update --case <case-id> --input "..." --dry-run
  codeer eval label-create --name "routing" --color "#0969da" --dry-run
  codeer eval case-delete --case <case-id> --dry-run
  codeer eval cases-apply --agent <agent-id> --cases eval_cases.json --dry-run
  codeer eval rubrics-apply --rubrics rubrics.json --dry-run
  codeer kb upload --dir kb --name "Product KB" --dry-run
  codeer kb node-rename --node-id <node-id> --name "New Name" --dry-run
  codeer kb node-delete --node-id <node-id> --dry-run
  codeer kb faq-create --context-object-id <snapshot-object-id> --question "..." --dry-run

Use --out <path> for large raw artifacts; stdout defaults to compact summaries.
""",
    )
    parser.add_argument("--outside-project", action="store_true", help="Explicitly operate outside the discovered project binding")
    sub = parser.add_subparsers(dest="group")
    from .commands import project as project_cmd
    project_cmd.register(sub)

    check.register(sub)
    skill.register(sub)

    try:
        from .commands import model as model_cmd
        model_cmd.register(sub)
    except ImportError:
        pass

    # Phase 2-4: agent, kb, eval commands will register here
    try:
        from .commands import agent as agent_cmd
        agent_cmd.register(sub)
    except ImportError:
        pass

    try:
        from .commands import kb as kb_cmd
        kb_cmd.register(sub)
    except ImportError:
        pass

    try:
        from .commands import eval_cmd
        eval_cmd.register(sub)
    except ImportError:
        pass

    try:
        from .commands import history as history_cmd
        history_cmd.register(sub)
    except ImportError:
        pass

    try:
        from .commands import profile as profile_cmd
        profile_cmd.register(sub)
    except ImportError:
        pass

    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 2

    try:
        project = None if args.outside_project else discover()
        args.project = project
        if project and not getattr(args, "no_client", False):
            expected = project.target.get("agent_id")
            for field in ("agent", "agent_id"):
                if hasattr(args, field):
                    explicit = getattr(args, field)
                    if expected and explicit and explicit != expected:
                        raise ProjectError("Agent differs from project binding; use --outside-project for a separate operation")
                    if not explicit:
                        setattr(args, field, expected)
        # Legacy export/reconcile resolve client/env fallbacks in their handlers.
        # Required targets are declared by each command, independent of its group.
        if getattr(args, "requires_agent", False) and not args.agent:
            parser.error("--agent is required outside a bound project")
    except ProjectError as e:
        print(f"project: {e}", file=sys.stderr)
        return 2

    if getattr(args, "no_client", False):
        client = None
    else:
        try:
            client = CodeerClient.from_env()
        except AuthError as e:
            if args.group == "check":
                if getattr(args, "json", False):
                    print(json.dumps({
                        "status": "fail",
                        "auth": {
                            "ok": False,
                            "error": str(e),
                        },
                        "next_step": "Configure CODEER_API_KEY or a codeer profile",
                    }, ensure_ascii=False, indent=2))
                    return 1
                print(f"FAIL  Auth: {e}", file=sys.stderr)
                print("      Configure CODEER_API_KEY or a codeer profile", file=sys.stderr)
                return 1
            print(f"auth error: {e}", file=sys.stderr)
            return 2

    try:
        if project and client is not None:
            project.check_scope(client)
        return args.func(args, client)
    except HistoryExportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except AuthError as e:
        print(f"auth: {e}", file=sys.stderr)
        return 3
    except CodeerError as e:
        print(f"error: {e}", file=sys.stderr)
        if e.body:
            print(json.dumps(e.body, ensure_ascii=False, indent=2, default=str), file=sys.stderr)
        return 1
    except (ProjectError, OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
