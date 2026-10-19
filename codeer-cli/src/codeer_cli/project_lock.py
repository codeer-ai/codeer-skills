"""One local process lock for CLI-controlled project writes and cleanup."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path

from .project import ProjectError

_held = ContextVar("codeer_project_locks", default=frozenset())


@contextmanager
def project_lock(root):
    root = Path(root).resolve()
    if root in _held.get():
        yield
        return
    directory = root / ".codeer"
    path = directory / "project.lock"
    if not directory.resolve().is_relative_to(root) or path.is_symlink():
        raise ProjectError("Project lock path escapes the project or is a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        token = _held.set(_held.get() | {root})
        try:
            yield
        finally:
            _held.reset(token)
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def writes_project(args):
    if getattr(args, "dry_run", False):
        # FAQ previews persist their observed comparison for offline status.
        return args.group == "kb" and getattr(args, "action", None) == "faq-sync"
    if args.group in ("skill", "profile", "model", "check", "validate"):
        return False
    if args.group == "status":
        return args.refresh
    if args.group == "agent" and args.action in ("bindings",):
        return False
    if args.group == "eval" and args.action == "inspect-run":
        return False
    return True
