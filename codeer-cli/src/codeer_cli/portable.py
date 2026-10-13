"""Portable definitions and explicit deployment dependency resolution.

Only variables named by the project's definitions are read. Resolved secrets
exist at the HTTP boundary; previews, state and evidence retain logical names.
"""
from copy import deepcopy
import os
import re
from pathlib import Path

from .project import ProjectError, fingerprint, read_json


def definitions(project):
    value = read_json(project.root / "resources.json", {"schema_version": 1, "attachments": {}, "knowledge": {}})
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ProjectError("resources.json requires schema_version 1")
    for kind in ("attachments", "knowledge"):
        if not isinstance(value.get(kind, {}), dict):
            raise ProjectError(f"resources.{kind} must be an object keyed by stable local ID")
        for local_id, entry in value.get(kind, {}).items():
            fields = ("path",) if kind == "attachments" else ("directory", "glob")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", local_id) or not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) or not entry[k] for k in fields):
                raise ProjectError(f"Invalid {kind} definition: {local_id}; require stable ID and {fields}")
            if Path(entry[fields[0]]).is_absolute():
                raise ProjectError("Portable source paths must be relative to the project")
            project.resolve_path(kind, entry[fields[0]])
            for key in ("faq_file", "manifest"):
                if key in entry:
                    if not isinstance(entry[key], str) or not entry[key] or Path(entry[key]).is_absolute():
                        raise ProjectError(f"Portable {key} must be a relative project path")
                    project.resolve_path(kind, entry[key])
    return value


def content_files(project):
    result = {}
    path = project.root / "resources.json"
    result["resources"] = fingerprint(path.read_bytes().hex()) if path.is_file() else None
    for name, entry in definitions(project).get("attachments", {}).items():
        path = project.resolve_path("attachment", entry["path"])
        result[f"attachment:{name}"] = fingerprint(path.read_bytes().hex()) if path.is_file() else None
    from .project_kb import local_sources
    for name, entry in definitions(project).get("knowledge", {}).items():
        project.resolve_path("knowledge", entry["directory"])
        result[f"kb:{name}"] = local_sources(project, {"source": entry})
        if entry.get("faq_file"):
            path = project.resolve_path("knowledge", entry["faq_file"])
            result[f"faq:{name}"] = fingerprint(path.read_bytes().hex()) if path.is_file() else None
    return result


def input_paths(project):
    from .project import PATHS
    from .project_eval import references
    paths = {project.path(key) for key in PATHS}
    paths.update((project.root / "project.toml", project.root / "resources.json"))
    paths.update(project.resolve_path("reference", p) for p in references(read_json(project.path("evals"), {})) if not p.startswith(("http://", "https://")))
    data = definitions(project)
    required = set()
    required.update(project.resolve_path("attachment", row["manifest"]) for row in data.get("attachments", {}).values() if row.get("manifest"))
    paths.update(project.resolve_path("attachment", row["path"]) for row in data.get("attachments", {}).values())
    for row in data.get("knowledge", {}).values():
        directory = project.resolve_path("knowledge", row["directory"])
        paths.update(p.resolve() for p in directory.glob(row["glob"]) if p.is_file())
        required.update(project.resolve_path("knowledge", row[k]) for k in ("faq_file", "manifest") if row.get(k))
    required.update((project.root / "sources/exports").glob("*.json"))
    paths.update(required)
    # Resolve every collected path, including auto-discovered export evidence.
    paths = {p.resolve() for p in paths}
    state_root = (project.root / ".codeer").resolve()
    if any(not p.is_relative_to(project.root) or p.is_relative_to(state_root) for p in paths):
        raise ProjectError("Portable input evidence must remain inside project content, outside .codeer")
    if any(not p.is_file() for p in required):
        raise ProjectError("Required FAQ/manifest input is missing or not a file")
    return sorted(p for p in paths if p.is_file())


def environment(project):
    """Resolve only explicit env: references, never search files for credentials."""
    names = set()
    def visit(value):
        if isinstance(value, str) and value.startswith("env:"):
            names.add(value[4:])
        elif isinstance(value, dict):
            for key in value.get("llm_model_settings", {}):
                visit(key)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(read_json(project.path("agent"), {}))
    visit(read_json(project.path("evals"), {}))
    return {f"env:{name}": os.environ.get(name) for name in sorted(names)}


def bindings(project, *, canonical=False):
    result = {}
    for key, entry in project.state().get("resources", {}).items():
        if key.startswith(("attachment:", "kb:")) and entry.get("server_id"):
            if entry.get("status") not in ("ready", "aligned"):
                continue
            if entry.get("root_reference", True):
                result[key] = entry["server_id"]
            if key.startswith("kb:"):
                for path, sid in entry.get("file_ids", {}).items():
                    result[f"{key}/{path}"] = sid
    if canonical:
        for key, entry in project.state().get("resources", {}).items():
            for path, reference in entry.get("file_aliases", {}).items():
                alias = f"{key}/{path}"
                if alias != reference and result.get(alias) is not None and result.get(alias) == result.get(reference):
                    result.pop(alias)
    return result


def translate(project, value, *, reverse=False):
    if not project.portable:
        return deepcopy(value)
    refs = {**bindings(project, canonical=reverse), **environment(project)}
    if reverse:
        inverse = {}
        for key, resolved in refs.items():
            if resolved is not None:
                inverse.setdefault(str(resolved), []).append(key)
    def walk(item):
        if isinstance(item, str):
            if reverse:
                matches = inverse.get(item, [])
                if len(matches) > 1:
                    raise ProjectError("Ambiguous reverse dependency mapping; use unique logical references")
                return matches[0] if matches else item
            if item.startswith(("attachment:", "kb:", "env:", "unresolved:")):
                if item not in refs or refs[item] is None:
                    raise ProjectError(f"Unresolved deployment dependency: {item}")
                return refs[item]
        if isinstance(item, list):
            return [walk(v) for v in item]
        if isinstance(item, dict):
            result = {k: walk(v) for k, v in item.items()}
            if isinstance(result.get("llm_model_settings"), dict):
                result["llm_model_settings"] = {walk(k): v for k, v in result["llm_model_settings"].items()}
            return result
        return item
    return walk(value)


def connection_fingerprint(project):
    # Detect variable changes between preview and apply without persisting values.
    return fingerprint(environment(project))


def redact(project, value):
    if not project.portable:
        return value
    refs = [(resolved, reference) for reference, resolved in environment(project).items() if resolved and len(resolved) >= 8]
    def walk(item):
        if isinstance(item, str):
            for resolved, reference in refs:
                item = item.replace(resolved, reference)
        elif isinstance(item, dict):
            item = {k: walk(v) for k, v in item.items()}
        elif isinstance(item, list):
            item = [walk(v) for v in item]
        return item
    return walk(value)


def logical_remote(project, value):
    result = redact(project, translate(project, value, reverse=True))
    if not project.portable:
        return result
    def missing(kind, sid):
        return f"unresolved:{kind}:{fingerprint(str(sid))[:12]}"
    env = environment(project)
    for field, kind, prefix in (("attachment_ids", "attachment", "attachment:"), ("primary_object_ids", "context", "env:"), ("label_ids", "label", "env:")):
        if field in result:
            if prefix == "env:":
                result[field] = [next((ref for ref, val in env.items() if val is not None and str(val) == str(item)), item) for item in result[field]]
            result[field] = [v if isinstance(v, str) and v.startswith(prefix) else missing(kind, v) for v in result[field]]
    for tool in result.get("unified_tools", []) or []:
        if tool.get("knowledge_node_ids"):
            tool["knowledge_node_ids"] = [v if v.startswith("kb:") else missing("kb", v) for v in tool["knowledge_node_ids"]]
        if tool.get("knowledge_node_id") and not tool["knowledge_node_id"].startswith("kb:"):
            tool["knowledge_node_id"] = missing("kb", tool["knowledge_node_id"])
        config = tool.get("http_request") or {}
        auth = config.get("auth") or {}
        for key in ("token", "api_key", "username", "password", "header_value"):
            if auth.get(key) and not str(auth[key]).startswith("env:"):
                auth[key] = missing("secret", auth[key])
        for key, val in (config.get("headers") or {}).items():
            if key.lower() in ("authorization", "x-api-key", "cookie") and not str(val).startswith("env:"):
                config["headers"][key] = missing("secret", val)
    return result


def check_agent(project, settings):
    if not project.portable:
        return
    if any(t.get("agent_id") or t.get("type") == "agent" for t in settings.get("unified_tools", []) or []):
        raise ProjectError("Sub-Agent references are retained for read-only diagnosis; project deployment is unsupported")
    for field, prefix in (("attachment_ids", "attachment:"), ("primary_object_ids", "env:")):
        if any(not isinstance(v, str) or not v.startswith(prefix) for v in settings.get(field, [])):
            raise ProjectError(f"Portable {field} requires logical references; import observations are not deployable definitions")
    for tool in settings.get("unified_tools", []) or []:
        config = tool.get("http_request") or {}
        auth = config.get("auth") or {}
        for key in ("token", "api_key", "username", "password", "header_value"):
            if auth.get(key) and not str(auth[key]).startswith("env:"):
                raise ProjectError("HTTP tool credentials must use env:<VARIABLE> references")
        for key, val in (config.get("headers") or {}).items():
            if key.lower() in ("authorization", "x-api-key", "cookie") and not str(val).startswith("env:"):
                raise ProjectError("HTTP credential headers must use env:<VARIABLE> references")
        nodes = tool.get("knowledge_node_ids") or []
        if tool.get("knowledge_node_id"):
            nodes = [*nodes, tool["knowledge_node_id"]]
        if any(not isinstance(v, str) or not v.startswith("kb:") for v in nodes):
            raise ProjectError("Portable knowledge tools require kb:<local-id>[/path] references")
    translate(project, settings)


def check_models(project, client, settings):
    if not project.portable:
        return
    selected = translate(project, settings)
    wanted = {selected.get("llm_model"), selected.get("judge_llm_model_id")}
    wanted.update(t.get("image_model") for t in selected.get("unified_tools", []) or [])
    wanted.discard(None)
    if wanted:
        from .models import list_available
        models = list_available(client)
        available = {str(m.get(k)) for m in models for k in ("id", "model_id") if m.get(k)}
        if not wanted <= available:
            raise ProjectError("Selected model unavailable in this deployment; inspect codeer model list and explicit env references")
