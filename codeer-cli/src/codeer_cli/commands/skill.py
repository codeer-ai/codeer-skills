"""Local Codeer skill management; no Codeer client or credentials required."""

from __future__ import annotations

import sys

import httpx

from .. import skills
from ._util import print_json


def register(subparsers):
    parser = subparsers.add_parser(
        "skill", help="Install, update, and remove Codeer skills locally"
    )
    parser.set_defaults(no_client=True)
    sub = parser.add_subparsers(dest="action", required=True)

    list_ = sub.add_parser(
        "list", help="List Codeer skills and local installation status (offline)"
    )
    list_.add_argument("--target", choices=("codex", "claude"))
    list_.add_argument("--scope", choices=("user", "project"), default="user")
    list_.set_defaults(func=run_list)

    for action, handler in (("install", run_install), ("uninstall", run_uninstall)):
        command = sub.add_parser(
            action,
            help=(
                "Install or update a Codeer skill; preserve local changes"
                if action == "install"
                else "Remove an unchanged, managed Codeer skill"
            ),
        )
        command.add_argument("name", choices=tuple(skills.CATALOG))
        command.add_argument("--target", choices=("codex", "claude"), required=True)
        command.add_argument("--scope", choices=("user", "project"), default="user")
        command.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without changing installation files",
        )
        if action == "install":
            command.add_argument(
                "--ref",
                default="main",
                help="GitHub branch, tag, or commit (default: main)",
            )
        command.set_defaults(func=handler)


def run_list(args, client=None) -> int:
    return _run(lambda: skills.list_skills(target=args.target, scope=args.scope))


def run_install(args, client=None) -> int:
    return _run(
        lambda: skills.install(
            args.name,
            target=args.target,
            scope=args.scope,
            ref=args.ref,
            dry_run=args.dry_run,
        )
    )


def run_uninstall(args, client=None) -> int:
    return _run(
        lambda: skills.uninstall(
            args.name, target=args.target, scope=args.scope, dry_run=args.dry_run
        )
    )


def _run(operation) -> int:
    try:
        print_json(operation())
        return 0
    except (skills.SkillError, OSError, httpx.HTTPError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
