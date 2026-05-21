"""Codeer CLI — unified interface for agent lifecycle operations.

    codeer check
    codeer agent list|get|apply|diff|versions
    codeer kb list|files|upload
    codeer eval list|evaluators|evaluator-create|evaluator-update|run|export|reconcile|cases-apply|rubrics|rubrics-apply
    codeer history list|get|conversations|negative-feedback
"""

from __future__ import annotations

import argparse
import json
import sys

from .client import AuthError, CodeerClient, CodeerError
from .commands import check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codeer")
    sub = parser.add_subparsers(dest="group")

    check.register(sub)

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

    if getattr(args, "no_client", False):
        client = None
    else:
        try:
            client = CodeerClient.from_env()
        except AuthError as e:
            if args.group == "check":
                print(f"FAIL  Auth: {e}", file=sys.stderr)
                print("      Configure CODEER_API_KEY or a codeer profile", file=sys.stderr)
                return 1
            print(f"auth error: {e}", file=sys.stderr)
            return 2

    try:
        return args.func(args, client)
    except AuthError as e:
        print(f"auth: {e}", file=sys.stderr)
        return 3
    except CodeerError as e:
        print(f"error: {e}", file=sys.stderr)
        if e.body:
            print(json.dumps(e.body, ensure_ascii=False, indent=2, default=str), file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
