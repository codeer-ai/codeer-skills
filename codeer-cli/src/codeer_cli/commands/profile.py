from __future__ import annotations

import getpass
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from ..client import DEFAULT_CODEER_API_BASE

CONFIG_DIR = ".codeer"
LOCAL_PROFILE_FILE = "profile"
GLOBAL_PROFILE_FILE = "profiles.json"


def register(subparsers):
    p = subparsers.add_parser("profile", help="Manage named API-key profiles")
    p.set_defaults(no_client=True)
    sub = p.add_subparsers(dest="action")

    current = sub.add_parser("current", help="Show the selected profile")
    current.set_defaults(func=run_current, no_client=True)

    list_ = sub.add_parser("list", help="List configured profiles")
    list_.set_defaults(func=run_list, no_client=True)

    add = sub.add_parser("add", help="Add or update a global profile")
    add.add_argument("name")
    add.add_argument("--api-base", default=DEFAULT_CODEER_API_BASE)
    add.set_defaults(func=run_add, no_client=True)

    use = sub.add_parser("use", help="Use a profile in this directory")
    use.add_argument("name")
    use.set_defaults(func=run_use, no_client=True)

    default = sub.add_parser("default", help="Set the global default profile")
    default.add_argument("name")
    default.set_defaults(func=run_default, no_client=True)

    remove = sub.add_parser("remove", help="Remove a global profile")
    remove.add_argument("name")
    remove.set_defaults(func=run_remove, no_client=True)


def resolve_profile() -> dict[str, str | None]:
    if "CODEER_API_KEY" in os.environ:
        return {
            "name": os.environ.get("CODEER_PROFILE"),
            "source": "environment",
            "api_key": os.environ["CODEER_API_KEY"],
            "api_base": os.environ.get("CODEER_API_BASE") or DEFAULT_CODEER_API_BASE,
        }

    selected = os.environ.get("CODEER_PROFILE")
    source = "CODEER_PROFILE" if selected else None

    if not selected:
        local = _find_local_profile(Path.cwd())
        if local:
            selected = local.read_text(encoding="utf-8").strip()
            source = str(local)

    data = _read_profiles()
    if not selected:
        selected = data.get("default")
        source = str(_profiles_path()) if selected else None

    if not selected:
        return {"name": None, "source": None, "api_key": None, "api_base": DEFAULT_CODEER_API_BASE}

    profile = (data.get("profiles") or {}).get(selected)
    if not isinstance(profile, dict):
        return {"name": selected, "source": source, "api_key": None, "api_base": DEFAULT_CODEER_API_BASE}

    return {
        "name": selected,
        "source": source,
        "api_key": profile.get("api_key"),
        "api_base": profile.get("api_base") or DEFAULT_CODEER_API_BASE,
    }


def run_current(args, client=None) -> int:
    resolved = resolve_profile()
    name = resolved.get("name") or "(none)"
    source = resolved.get("source") or "(none)"
    api_key = resolved.get("api_key")
    api_base = resolved.get("api_base") or DEFAULT_CODEER_API_BASE

    print(f"Profile: {name}")
    print(f"Source: {source}")
    print(f"API base: {api_base}")
    print(f"API key: {_mask(api_key) if api_key else '(missing)'}")
    return 0 if api_key else 1


def run_list(args, client=None) -> int:
    data = _read_profiles()
    profiles = data.get("profiles") or {}
    default = data.get("default")
    if not profiles:
        print("No profiles configured")
        return 0

    for name in sorted(profiles):
        marker = "*" if name == default else " "
        api_base = profiles[name].get("api_base") or DEFAULT_CODEER_API_BASE
        print(f"{marker} {name}\t{api_base}")
    return 0


def run_add(args, client=None) -> int:
    api_key = getpass.getpass("API key: ").strip()
    if not api_key:
        print("error: API key is required", file=sys.stderr)
        return 2

    data = _read_profiles()
    profiles = data.setdefault("profiles", {})
    profiles[args.name] = {"api_key": api_key, "api_base": args.api_base}
    if not data.get("default"):
        data["default"] = args.name
    _write_profiles(data)
    print(f"Saved profile {args.name}")
    return run_use(args)


def run_use(args, client=None) -> int:
    data = _read_profiles()
    if args.name not in (data.get("profiles") or {}):
        print(f"error: profile {args.name!r} does not exist", file=sys.stderr)
        return 2

    path = Path.cwd() / CONFIG_DIR / LOCAL_PROFILE_FILE
    path.parent.mkdir(mode=0o700, exist_ok=True)
    path.write_text(args.name + "\n", encoding="utf-8")
    print(f"Using profile {args.name} in {Path.cwd()}")
    return 0


def run_default(args, client=None) -> int:
    data = _read_profiles()
    if args.name not in (data.get("profiles") or {}):
        print(f"error: profile {args.name!r} does not exist", file=sys.stderr)
        return 2
    data["default"] = args.name
    _write_profiles(data)
    print(f"Default profile is {args.name}")
    return 0


def run_remove(args, client=None) -> int:
    data = _read_profiles()
    profiles = data.get("profiles") or {}
    if args.name not in profiles:
        print(f"error: profile {args.name!r} does not exist", file=sys.stderr)
        return 2

    del profiles[args.name]
    if data.get("default") == args.name:
        data["default"] = sorted(profiles)[0] if profiles else None
    _write_profiles(data)
    print(f"Removed profile {args.name}")
    return 0


def _profiles_path() -> Path:
    return Path.home() / CONFIG_DIR / GLOBAL_PROFILE_FILE


def _read_profiles() -> dict[str, Any]:
    path = _profiles_path()
    if not path.exists():
        return {"default": None, "profiles": {}}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid profile config: {path}")
    data.setdefault("profiles", {})
    return data


def _write_profiles(data: dict[str, Any]) -> None:
    path = _profiles_path()
    path.parent.mkdir(mode=0o700, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _find_local_profile(start: Path) -> Path | None:
    for path in [start, *start.parents]:
        candidate = path / CONFIG_DIR / LOCAL_PROFILE_FILE
        if candidate.exists():
            return candidate
    return None


def _mask(value: str | None) -> str:
    if not value:
        return "(missing)"
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "..." + value[-4:]
