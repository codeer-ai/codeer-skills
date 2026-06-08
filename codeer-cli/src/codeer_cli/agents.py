"""Agent CRUD, versioning, and publishing.

Each function returns the parsed `data` field from the Ninja response envelope.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ._validate import validate_unified_tools
from .client import CodeerClient


def create(
    client: CodeerClient,
    *,
    workspace_id: str,
    name: str,
    system_prompt: str,
    unified_tools: Optional[List[dict]] = None,
    use_search: bool = False,
    llm_model: Optional[str] = None,
    description: Optional[str] = None,
    suggested_questions: Optional[List[str]] = None,
    primary_object_ids: Optional[List[int]] = None,
    attachment_ids: Optional[List[str]] = None,
) -> dict:
    validated_tools = validate_unified_tools(unified_tools)
    body: dict[str, Any] = {
        "name": name,
        "system_prompt": system_prompt,
        "unified_tools": validated_tools,
        "primary_object_ids": primary_object_ids or [],
        "attachment_ids": attachment_ids or [],
        "use_search": use_search,
        "suggested_questions": suggested_questions or [],
    }
    if description is not None:
        body["description"] = description
    if llm_model is not None:
        body["llm_model"] = llm_model
    return client.post("/external/agents", json=body)


def update(
    client: CodeerClient,
    agent_id: str,
    *,
    name: str,
    system_prompt: str,
    unified_tools: List[dict],
    use_search: bool,
    version_note: str = "",
    description: Optional[str] = None,
    llm_model: Optional[str] = None,
    suggested_questions: Optional[List[str]] = None,
    primary_object_ids: Optional[List[int]] = None,
    attachment_ids: Optional[List[str]] = None,
) -> dict:
    """PUT creates a new AgentHistory snapshot (draft)."""
    validated_tools = validate_unified_tools(unified_tools)
    body: dict[str, Any] = {
        "name": name,
        "system_prompt": system_prompt,
        "unified_tools": validated_tools,
        "primary_object_ids": primary_object_ids or [],
        "attachment_ids": attachment_ids or [],
        "use_search": use_search,
        "version_note": version_note,
        "suggested_questions": suggested_questions or [],
    }
    if description is not None:
        body["description"] = description
    if llm_model is not None:
        body["llm_model"] = llm_model
    return client.patch(f"/external/agents/{agent_id}", json=body)


def get(client: CodeerClient, agent_id: str) -> dict:
    return client.get(f"/external/agents/{agent_id}")


def get_default(client: CodeerClient) -> dict:
    """Read whichever agent ``CODEER_AGENT_ID`` points to (project env).

    Workspace and organization scope come from the API-key virtual user's
    profile. Raises if no ``agent_id`` is in scope.
    """
    if not client.agent_id:
        raise ValueError(
            "No agent_id in scope. Set CODEER_AGENT_ID in .claude/settings.json, "
            "export it in your shell, or pass agent_id explicitly to from_env()."
        )
    return get(client, client.agent_id)


def get_latest_draft_history_id(client: CodeerClient, agent_id: str) -> Optional[str]:
    """Return the id of the most recent unpublished AgentHistory, or None.

    "Most recent" = highest ``version_number`` among ``status == 'draft'``.
    Returns ``None`` if every version has been published (so there's no
    open draft to pin a test against).
    """
    versions = list_versions(client, agent_id)
    drafts = [v for v in versions if v.get("status") == "draft"]
    if not drafts:
        return None
    drafts.sort(key=lambda v: v.get("version_number") or 0, reverse=True)
    return drafts[0].get("id")


def get_latest_history_id(client: CodeerClient, agent_id: str) -> Optional[str]:
    """Return the id of the most recent AgentHistory, draft or published."""
    versions = list_versions(client, agent_id)
    if not versions:
        return None
    versions.sort(key=lambda v: v.get("version_number") or 0, reverse=True)
    return versions[0].get("id")


def list_in_workspace(client: CodeerClient, workspace_id: str) -> list[dict]:
    """List **published** agents in a workspace (drafts are hidden).

    If you need drafts too — which is almost always the case while iterating
    on an agent — use :func:`list_all` with both workspace_id and organization_id.
    """
    return client.get("/external/agents")


def list_all(
    client: CodeerClient,
    *,
    workspace_id: str,
    organization_id: str,
) -> list[dict]:
    """List every agent in a workspace including drafts.

    Both IDs are required — ``GET /agents/all`` returns 400 ``Organization ID
    is required`` if you omit ``oid``. Look up the org for a workspace via
    ``/accounts/me`` → ``profile.workspace_organization_map``.
    """
    return client.get("/external/agents/all")


def list_versions(client: CodeerClient, agent_id: str) -> list[dict]:
    return client.get(f"/external/agents/{agent_id}/versions")


def get_version(client: CodeerClient, agent_id: str, history_id: str) -> dict:
    return client.get(f"/external/agents/{agent_id}/versions/{history_id}")


def check_impact(client: CodeerClient, agent_id: str) -> dict:
    """List downstream agents that call this one. Call before publishing breaking changes."""
    return client.get(f"/external/agents/{agent_id}/impact")


def publish_version(client: CodeerClient, agent_id: str, history_id: str) -> dict:
    """Promote one AgentHistory version to the published runtime version."""
    return client.post(f"/external/agents/{agent_id}/versions/{history_id}:publish", json={})
