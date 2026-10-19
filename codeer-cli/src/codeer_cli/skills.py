"""Install the three Codeer skills from immutable GitHub snapshots.

These operations are local and never use Codeer credentials. An installation
receipt lives inside the copied directory; only unchanged, managed directories
can be updated or removed. Updates stage the full package and retain the old
directory until publication succeeds.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

REPOSITORY = "codeer-ai/codeer-skills"
RECEIPT = ".codeer-skill-install.json"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_SKILL_BYTES = 16 * 1024 * 1024
CATALOG = {
    "codeer-agent": "Design, evaluate, publish, and improve Codeer agents.",
    "codeer-audience-value-narrative": "Shape audience-first Codeer narratives.",
    "codeer-presentations": "Build and review Codeer sales and investor decks.",
}


class SkillError(ValueError):
    """Invalid source, conflicting installation, or unsafe local state."""


def skill_root(target: str, scope: str, *, project: Path | None = None) -> Path:
    if target not in ("codex", "claude") or scope not in ("user", "project"):
        raise SkillError("Choose target codex/claude and scope user/project.")
    base = Path.home() if scope == "user" else (project or Path.cwd())
    # Normalize OS aliases such as macOS /var -> /private/var before checking
    # the installation subtree for user-created symlinks.
    return base.resolve() / (".agents" if target == "codex" else ".claude") / "skills"


def _require_name(name: str) -> None:
    if name not in CATALOG:
        raise SkillError(f"Unknown Codeer skill: {name}")


def _require_plain_path(path: Path) -> None:
    # Check ancestors too: resolving a symlink would let installation/removal
    # escape the selected target or operate on someone else's shared skills.
    for part in (path, *path.parents):
        if part.is_symlink():
            raise SkillError(f"Refusing symlinked installation path: {part}")


def _fingerprint(directory: Path) -> dict[str, str]:
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise SkillError(f"Skill contains a symlink: {path}")
        if path.is_dir():
            if not any(path.iterdir()):
                raise SkillError(f"Skill has local changes (empty directory): {path}")
            continue
        if not path.is_file():
            raise SkillError(f"Skill contains a non-regular file: {path}")
        relative = path.relative_to(directory).as_posix()
        if relative != RECEIPT:
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _read_receipt(directory: Path, name: str) -> dict:
    path = directory / RECEIPT
    if path.is_symlink() or not path.is_file():
        raise SkillError(f"Unmanaged skill at {directory}; no files were changed.")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SkillError(f"Invalid installation receipt at {path}") from exc
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != 1
        or receipt.get("repository") != REPOSITORY
        or receipt.get("skill") != name
        or not isinstance(receipt.get("commit"), str)
        or not re.fullmatch(r"[0-9a-f]{40}", receipt["commit"])
        or not isinstance(receipt.get("files"), dict)
        or "SKILL.md" not in receipt["files"]
    ):
        raise SkillError(f"Invalid installation receipt at {path}")
    return receipt


def _require_unchanged(directory: Path, name: str) -> dict:
    receipt = _read_receipt(directory, name)
    if _fingerprint(directory) != receipt["files"]:
        raise SkillError(
            f"Skill has local changes at {directory}; preserve them before updating or removing it."
        )
    return receipt


def list_skills(*, target: str | None = None, scope: str = "user") -> list[dict]:
    rows = []
    for name, description in CATALOG.items():
        installations = []
        for tool in [target] if target else ["codex", "claude"]:
            path = skill_root(tool, scope) / name
            status = "not_installed"
            commit = None
            try:
                _require_plain_path(path)
                if path.exists():
                    receipt = _read_receipt(path, name)
                    commit = receipt["commit"]
                    try:
                        status = (
                            "installed"
                            if _fingerprint(path) == receipt["files"]
                            else "modified"
                        )
                    except SkillError:
                        status = "modified"
            except (SkillError, OSError):
                status = "unmanaged"
            installations.append(
                {"target": tool, "path": str(path), "status": status, "commit": commit}
            )
        rows.append(
            {
                "name": name,
                "description": description,
                "scope": scope,
                "installations": installations,
            }
        )
    return rows


def _fetch_skill(name: str, ref: str) -> tuple[str, dict[str, tuple[bytes, int]]]:
    if not ref.strip():
        raise SkillError("--ref must not be empty.")
    # Resolve once, then download by commit so a moving branch cannot change
    # between metadata lookup and download. Never forward a Codeer API key.
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(
            f"https://api.github.com/repos/{REPOSITORY}/commits/{quote(ref, safe='')}",
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        metadata = response.json()
        commit = metadata.get("sha") if isinstance(metadata, dict) else None
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise SkillError("GitHub did not return an immutable commit SHA.")
        archive = bytearray()
        with client.stream(
            "GET", f"https://codeload.github.com/{REPOSITORY}/zip/{commit}"
        ) as download:
            download.raise_for_status()
            for chunk in download.iter_bytes():
                archive.extend(chunk)
                if len(archive) > MAX_ARCHIVE_BYTES:
                    raise SkillError("GitHub archive exceeds the 32 MiB limit.")
    return commit, _archive_files(bytes(archive), name, commit)


def _archive_files(
    archive: bytes, name: str, commit: str
) -> dict[str, tuple[bytes, int]]:
    prefix = f"codeer-skills-{commit}/skills/{name}/"
    files = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            for entry in bundle.infolist():
                if not entry.filename.startswith(prefix):
                    continue
                relative = entry.filename[len(prefix) :]
                path = PurePosixPath(relative)
                mode = entry.external_attr >> 16
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in relative
                    or any(":" in part for part in path.parts)
                    or stat.S_ISLNK(mode)
                    or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                ):
                    raise SkillError(f"Unsafe skill archive entry: {entry.filename}")
                if entry.is_dir():
                    continue
                if (
                    not relative
                    or relative == RECEIPT
                    or path.as_posix() != relative
                    or relative in files
                ):
                    raise SkillError(f"Invalid skill archive entry: {entry.filename}")
                total += entry.file_size
                if total > MAX_SKILL_BYTES:
                    raise SkillError("Expanded skill exceeds the 16 MiB limit.")
                files[relative] = (bundle.read(entry), 0o755 if mode & 0o111 else 0o644)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise SkillError("GitHub returned an invalid skill archive.") from exc
    manifest = files.get("SKILL.md", (b"", 0))[0]
    try:
        text = manifest.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SkillError("SKILL.md must be UTF-8 text.") from exc
    frontmatter = text.split("---", 2)
    if (
        not text.startswith("---\n")
        or len(frontmatter) < 3
        or not re.search(rf"(?m)^name:\s*{re.escape(name)}\s*$", frontmatter[1])
        or not re.search(r"(?m)^description:\s*\S", frontmatter[1])
    ):
        raise SkillError(f"Missing or invalid SKILL.md for {name}.")
    return files


def install(
    name: str,
    *,
    target: str,
    scope: str = "user",
    ref: str = "main",
    dry_run: bool = False,
) -> dict:
    _require_name(name)
    destination = skill_root(target, scope) / name
    _require_plain_path(destination)
    existing = _require_unchanged(destination, name) if destination.exists() else None
    commit, files = _fetch_skill(name, ref)
    hashes = {
        path: hashlib.sha256(content).hexdigest()
        for path, (content, _) in files.items()
    }
    result = {
        "skill": name,
        "target": target,
        "scope": scope,
        "path": str(destination),
        "repository": REPOSITORY,
        "ref": ref,
        "commit": commit,
        "file_count": len(files),
        "dry_run": dry_run,
    }
    if existing:
        _check_existing(destination, name, existing)
        if existing["files"] == hashes:
            return {
                **result,
                "status": "already_installed",
                "installed_commit": existing["commit"],
            }
        result["previous_commit"] = existing["commit"]
    if dry_run:
        return {**result, "status": "would_update" if existing else "would_install"}

    destination.parent.mkdir(parents=True, exist_ok=True)
    _require_plain_path(destination)
    with tempfile.TemporaryDirectory(
        prefix=".codeer-skill-", dir=destination.parent
    ) as temporary:
        staged = Path(temporary) / name
        staged.mkdir()
        for relative, (content, mode) in files.items():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(mode)
        if _fingerprint(staged) != hashes:
            raise SkillError(
                "Skill filenames collide on this filesystem; no installation was created."
            )
        receipt = {
            "schema": 1,
            "repository": REPOSITORY,
            "skill": name,
            "ref": ref,
            "commit": commit,
            "files": hashes,
        }
        (staged / RECEIPT).write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        if existing:
            _check_existing(destination, name, existing)
            # Keep the backup outside TemporaryDirectory so failed restoration
            # never causes automatic cleanup to delete the original package.
            backup_root = Path(
                tempfile.mkdtemp(prefix=".codeer-skill-backup-", dir=destination.parent)
            )
            backup = backup_root / name
            try:
                destination.rename(backup)
            except OSError:
                backup_root.rmdir()
                raise
            try:
                _publish_staged(staged, destination)
            except OSError:
                try:
                    backup.rename(destination)
                except OSError as exc:
                    raise SkillError(
                        f"Update failed and restoration failed; original skill backup is at {backup}."
                    ) from exc
                backup_root.rmdir()
                raise
            shutil.rmtree(backup_root)
        else:
            _publish_staged(staged, destination)
    return {**result, "status": "updated" if existing else "installed"}


def _check_existing(destination: Path, name: str, expected: dict) -> None:
    _require_plain_path(destination)
    if _require_unchanged(destination, name) != expected:
        raise SkillError(f"Installation changed at {destination}; retry the command.")


def _publish_staged(staged: Path, destination: Path) -> None:
    # Reserving the directory prevents replacing a concurrent installation.
    destination.mkdir()
    try:
        for child in staged.iterdir():
            child.rename(destination / child.name)
    except OSError:
        shutil.rmtree(destination)
        raise


def uninstall(
    name: str, *, target: str, scope: str = "user", dry_run: bool = False
) -> dict:
    _require_name(name)
    destination = skill_root(target, scope) / name
    _require_plain_path(destination)
    result = {
        "skill": name,
        "target": target,
        "scope": scope,
        "path": str(destination),
        "dry_run": dry_run,
    }
    if not destination.exists():
        return {**result, "status": "not_installed"}
    receipt = _require_unchanged(destination, name)
    if not dry_run:
        shutil.rmtree(destination)
    return {
        **result,
        "commit": receipt["commit"],
        "status": "would_uninstall" if dry_run else "uninstalled",
    }
