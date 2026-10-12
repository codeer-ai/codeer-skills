"""Local Agent project contract. No credentials, network, or inferred approvals."""
from __future__ import annotations

import hashlib
import json
import re
import tomllib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class ProjectError(ValueError):
    pass


PATHS = {
    "agent": "agent/settings.json",
    "instructions": "agent/instructions.md",
    "evals": "evals/design.json",
    "sources": "sources/index.md",
    "design": "design/agent-design.md",
    "acceptance": "design/acceptance.json",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    # Preserve object insertion order: HTTP template input ordering is meaningful.
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (ValueError, OSError) as exc:
        raise ProjectError(f"Cannot read {path}: {exc}") from exc


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def scope_matches(saved, current, *, allow_unbound_agent=False):
    """Older receipts may omit profile; known scope fields must still agree."""
    return all(current.get(k) == v or k == "agent_id" and v is None and allow_unbound_agent for k, v in saved.items())


def discover(start=None):
    start = Path(start or Path.cwd()).resolve()
    for directory in (start, *start.parents):
        if (directory / "project.toml").is_file():
            return Project.load(directory)
    return None


@dataclass
class Project:
    root: Path
    config: dict

    @classmethod
    def load(cls, root):
        root = Path(root).resolve()
        try:
            config = tomllib.loads((root / "project.toml").read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise ProjectError(f"Invalid project.toml: {exc}") from exc
        if config.get("schema_version") != 1:
            raise ProjectError("Unsupported project schema_version (expected 1)")
        if not isinstance(config.get("name"), str) or not config["name"].strip():
            raise ProjectError("project.toml requires a nonempty name")
        for table in ("target", "paths"):
            if not isinstance(config.get(table, {}), dict):
                raise ProjectError(f"{table} must be a TOML table")
            if any(not isinstance(v, str) for v in config.get(table, {}).values()):
                raise ProjectError(f"{table} values must be strings")
        result = cls(root, config)
        for key in PATHS:
            result.path(key)
        return result

    def path(self, key):
        # Keep the previous Python lookup and project.toml setting as aliases.
        if key == "contract":
            key = "design"
        if key == "design":
            return self.design_path()
        value = self.config.get("paths", {}).get(key, PATHS[key])
        return self.resolve_path(key, value)

    def resolve_path(self, key, value):
        path = (self.root / value).resolve()
        if not path.is_relative_to(self.root):
            raise ProjectError(f"Project path escapes root: {key}={value}")
        return path

    def design_path(self):
        paths = self.config.get("paths", {})
        explicit = [self.resolve_path(key, paths[key]) for key in ("design", "contract") if key in paths]
        if explicit:
            if len(set(explicit)) > 1:
                raise ProjectError("Conflicting [paths].design and [paths].contract; select one Agent design path")
            return explicit[0]
        candidates = [self.root / PATHS["design"], self.root / "design/behavior-contract.md"]
        present = [p for p in candidates if p.exists() or p.with_name(f"{p.stem}.draft.md").exists()]
        if len(present) > 1:
            raise ProjectError("Both Agent design file families exist; set [paths].design to select the intended source")
        return self.resolve_path("design", present[0] if present else candidates[0])

    @property
    def target(self):
        return self.config.get("target", {})

    @property
    def state_path(self):
        return self.root / ".codeer/state.json"

    def state(self):
        return read_json(self.state_path, {"schema_version": 1, "resources": {}})

    def save_state(self, state):
        save_json(self.state_path, state)

    def bind(self, **fields):
        """Update only simple target strings, retaining all comments and other text.

        Exotic valid TOML target spellings are refused rather than rewritten.
        """
        path = self.root / "project.toml"
        text = path.read_text(encoding="utf-8")
        match = re.search(r"(?m)^\[target\][ \t]*(?:#.*)?$", text)
        if not match:
            if "target" in self.config:
                raise ProjectError("Use a literal [target] table before binding")
            text += "\n[target]\n"
            match = re.search(r"(?m)^\[target\]$", text)
        end_match = re.search(r"(?m)^\[", text[match.end():])
        end = match.end() + end_match.start() if end_match else len(text)
        section = text[match.end():end]
        for key, value in fields.items():
            pattern = rf'(?m)^({re.escape(key)}[ \t]*=[ \t]*)"(?:[^"\\]|\\.)*"([ \t]*(?:#.*)?)$'
            found = re.search(pattern, section)
            if found:
                section = section[:found.start()] + found[1] + json.dumps(str(value)) + found[2] + section[found.end():]
            elif key in self.target:
                raise ProjectError(f"Cannot safely edit target.{key}; use a single-line basic string")
            else:
                section += f"{key} = {json.dumps(str(value))}\n"
        updated = text[:match.end()] + section + text[end:]
        parsed = tomllib.loads(updated)
        if any(parsed["target"].get(k) != str(v) for k, v in fields.items()):
            raise ProjectError("Target update verification failed")
        path.write_text(updated, encoding="utf-8")
        self.config = parsed

    def check_scope(self, client):
        ws, _ = client.resolve_scope()
        base = client.base_url.rstrip("/")
        if self.target.get("agent_id") and getattr(client, "agent_id", None) not in (None, self.target["agent_id"]):
            raise ProjectError("CODEER_AGENT_ID differs from the project binding")
        for key, actual in (("api_base", base), ("workspace_id", str(ws))):
            expected = self.target.get(key)
            if expected and expected.rstrip("/") != actual:
                raise ProjectError(f"Project {key} mismatch: expected {expected}, got {actual}. Use --outside-project for an explicit separate operation.")
        from .commands.profile import resolve_profile
        expected = self.target.get("profile")
        profile = resolve_profile().get("name")
        if expected and profile != expected:
            raise ProjectError(f"Project expects profile {expected}; select it with codeer profile use")
        return {"api_base": base, "workspace_id": str(ws), "agent_id": self.target.get("agent_id"), "profile": profile}

    def revision(self):
        files = {}
        for key in PATHS:
            path = self.path(key)
            # Retain the persisted pre-rename identity and ordering: a naming
            # change alone must not invalidate existing audit/run/release hashes.
            identity = "contract" if key == "design" else key
            files[identity] = fingerprint(path.read_text(encoding="utf-8")) if path.is_file() else None
        from .project_eval import references
        design = read_json(self.path("evals"), {})
        if isinstance(design, dict):
            for reference in references(design):
                if reference.startswith(("https://", "http://")):
                    continue
                path = (self.root / reference).resolve()
                files["reference:" + reference] = fingerprint(path.read_bytes().hex()) if path.is_relative_to(self.root) and path.is_file() else None
        from .project_kb import local_sources
        for key, entry in self.state().get("resources", {}).items():
            if key.startswith("kb:"):
                files[key] = local_sources(self, entry)
        return fingerprint({"target": self.target, "files": files})

    def validate(self):
        issues = []
        settings = read_json(self.path("agent"))
        if settings is not None:
            if not isinstance(settings, dict):
                issues.append("Agent settings must be an object")
            elif "system_prompt" in settings and self.path("instructions").exists():
                issues.append("Instructions have two editable authorities; remove system_prompt from settings.json")
        design = read_json(self.path("evals"))
        if design is not None:
            from .project_eval import validate_design
            issues.extend(validate_design(design, self.state(), self.root).get("unresolved", []))
        return issues

    def status(self):
        state = self.state()
        revision = self.revision()
        issues = self.validate()
        audits = sorted((self.root / "reviews").glob("*.audit.json"))
        audit = read_json(audits[-1]) if audits else None
        runs = sorted((self.root / "runs").glob("*/run.json"))
        run = read_json(runs[-1]) if runs else None
        releases = sorted((self.root / "releases").glob("*/release.json"))
        local_changes = []
        from .sync import checkpoint
        from .project_kb import local_sources
        for key, entry in state.get("resources", {}).items():
            if key.startswith("kb:") and local_sources(self, entry) != entry.get("local", {}):
                local_changes.append(key)
        if self.path("agent").is_file() and not issues:
            from .project_agent import local_settings
            base = checkpoint(state.get("resources", {}).get("agent", {}), "agent", local=True)
            local_changes.extend(f"agent.{k}" for k, v in local_settings(self).items() if base.get(k) != v)
        if self.path("evals").is_file() and not issues:
            from .project_eval import CASE_FIELDS, TESTER_FIELDS, select
            design = read_json(self.path("evals"), {})
            for kind, rows, fields in (("tester", design.get("testers", []), TESTER_FIELDS), ("case", design.get("cases", []), CASE_FIELDS)):
                for row in rows:
                    key = f"{kind}:{row.get('local_id')}"
                    base = checkpoint(state.get("resources", {}).get(key, {}), key, local=True)
                    if any(base.get(k) != v for k, v in select(row, fields).items()):
                        local_changes.append(key)
            for case in design.get("cases", []):
                key = f"pairs:{case.get('local_id')}"
                entry = state.get("resources", {}).get(key, {})
                base = checkpoint(entry, key, local=True)
                for pair in case.get("pairs", []):
                    sid = state.get("resources", {}).get(f"tester:{pair.get('tester')}", {}).get("server_id")
                    if not sid or base.get(sid) != pair.get("rubric"):
                        local_changes.append(key)
                        break
                if any(tid not in entry.get("removed_ids", []) for tid in case.get("remove_tester_ids", [])):
                    local_changes.append(key)
        cached = state.get("last_anchor", {})
        from .evidence import audit_matches
        wanted = cached.get("snapshot", {}).get("pairs", [])
        audit_local = any(audit_matches(self, read_json(path), {**cached, "revision": revision}, wanted, remote=False) for path in audits)
        audit_cached = any(audit_matches(self, read_json(path), {**cached, "revision": revision}, wanted) for path in audits)
        for path in reversed(audits):
            candidate = read_json(path)
            if audit_matches(self, candidate, {**cached, "revision": revision}, wanted, remote=audit_cached):
                audit = candidate
                break
        if run:
            run = {**run, "local_stale": run.get("revision") != revision,
                   "remote_stale_at_last_query": bool(cached and cached.get("remote_fingerprint") != run.get("remote_fingerprint"))}
            if len(runs) > 1:
                previous = read_json(runs[-2])
                old, current = previous.get("snapshot", {}), run.get("snapshot", {})
                run["comparison"] = {
                    "previous_run": previous.get("id"),
                    "agent_changed": old.get("agent") != current.get("agent"),
                    "kb_changed": old.get("kb") != current.get("kb"),
                    "measurement_changed": any(old.get(k) != current.get(k) for k in ("cases", "testers", "pairs")),
                    "interpretation": "Configuration comparison only; score differences do not establish causation",
                }
        release = read_json(releases[-1]) if releases else None
        release_matches_run = bool(release and run and all(
            release.get("plan", {}).get(k) == run.get(k)
            for k in ("history_id", "revision", "remote_fingerprint")))
        if issues:
            next_step = "Resolve structural issues before apply or validation clearance."
        elif local_changes:
            next_step = "Review local proposals and compare current remote changes before apply."
        elif release and release.get("status") in ("pending", "outcome_unknown", "readback_mismatch"):
            next_step = "Previous publication is unresolved; inspect its receipt and run agent publish --reconcile before retrying."
        elif release_matches_run and release.get("status") in ("published", "published_reconciled") and run.get("status") == "passed" and not run["local_stale"] and not run["remote_stale_at_last_query"]:
            next_step = "Recorded release readback is complete; observe production feedback when requested. Live remote state is not checked."
        elif run and run.get("status") == "passed" and not run["local_stale"] and not run["remote_stale_at_last_query"]:
            next_step = "Review semantic evidence and confirmed acceptance coverage; publish only within explicit authorization."
        else:
            next_step = "Review sources, unresolved decisions and current evidence. Imported state is not acceptance."
        return {
            "project": self.config["name"], "target": self.target,
            "last_remote_query": state.get("queried_at"),
            "revision": revision, "structural_issues": issues,
            "local_changes": sorted(set(local_changes)),
            "resources": {k: {"server_id": v.get("server_id"), "status": v.get("status")} for k, v in state.get("resources", {}).items()},
            "audit": {"local_revision_valid": audit_local, "valid_at_last_remote_query": audit_cached,
                      "checked_pair_scope": wanted,
                      "live_remote_validity": "not checked by offline status", "record": audit},
            "latest_run": run, "latest_release": release,
            "next_step": next_step,
        }
