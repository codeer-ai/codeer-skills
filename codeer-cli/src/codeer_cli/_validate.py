"""Client-side validation for unified-tool payloads.

These checks exist because the backend's form-schema validator is lenient
(``extra="allow"``) and silently accepts unknown ``type`` strings, which then
render as blank fields in the web builder. Catching the common mistakes here
gives actionable errors before the PUT/POST round-trip.
"""

from __future__ import annotations

from typing import Any, Iterable

from .constants import (
    FORM_FIELD_TYPES,
    MAX_CALL_AGENT_TOOLS,
    MAX_MEMORY_TOOLS,
    MAX_TOOLS_PER_AGENT,
    REQUIRED_FORM_FIELD_KEYS,
    UNIFIED_TOOL_TYPES,
)


class ToolValidationError(ValueError):
    """Raised when a unified_tools payload is definitely wrong."""


def validate_unified_tools(tools: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Raise ToolValidationError on invalid payloads; otherwise return the list.

    Validates type strings against the backend enum and walks into
    ``custom_form_schema.fields`` for request_form tools so we catch the
    ``type: "text" | "email" | "select"`` mistake the UI renders as blank.
    """
    tools_list = list(tools or [])
    if len(tools_list) > MAX_TOOLS_PER_AGENT:
        raise ToolValidationError(
            f"{len(tools_list)} tools configured, max allowed is {MAX_TOOLS_PER_AGENT} "
            "(see user-docs/agent-creation/tools/index.md)."
        )

    call_agent_count = sum(1 for t in tools_list if t.get("type") == "call_agent")
    if call_agent_count > MAX_CALL_AGENT_TOOLS:
        raise ToolValidationError(
            f"{call_agent_count} call_agent tools configured, max is {MAX_CALL_AGENT_TOOLS}."
        )

    memory_count = sum(1 for t in tools_list if t.get("type") == "memory")
    if memory_count > MAX_MEMORY_TOOLS:
        raise ToolValidationError(
            f"{memory_count} memory tools configured, max is {MAX_MEMORY_TOOLS}."
        )

    for i, tool in enumerate(tools_list):
        _validate_single_tool(tool, i)

    return tools_list


def _validate_single_tool(tool: dict[str, Any], index: int) -> None:
    prefix = f"unified_tools[{index}]"
    tool_type = tool.get("type")
    if tool_type not in UNIFIED_TOOL_TYPES:
        raise ToolValidationError(
            f"{prefix}.type = {tool_type!r} is not a valid UnifiedToolType. "
            f"Valid values: {sorted(UNIFIED_TOOL_TYPES)}."
        )
    if not tool.get("id"):
        raise ToolValidationError(f"{prefix}.id is required and must be non-empty.")

    if tool_type == "request_form":
        _validate_form_schema(tool.get("custom_form_schema"), prefix)
    elif tool_type == "knowledge_base":
        node_ids = tool.get("knowledge_node_ids")
        if node_ids is None or (isinstance(node_ids, list) and not node_ids):
            raise ToolValidationError(
                f"{prefix}: knowledge_base tool needs non-empty knowledge_node_ids."
            )
    elif tool_type == "call_agent":
        if not tool.get("agent_id"):
            raise ToolValidationError(f"{prefix}: call_agent tool requires agent_id.")
    elif tool_type == "http_request":
        cfg = tool.get("http_request")
        if not cfg or not cfg.get("method") or not cfg.get("url_template"):
            raise ToolValidationError(
                f"{prefix}: http_request tool requires http_request.method and http_request.url_template."
            )


def _validate_form_schema(schema: Any, prefix: str) -> None:
    if schema is None:
        raise ToolValidationError(
            f"{prefix}: request_form tool requires custom_form_schema "
            "(with title, fields[], ...)."
        )
    if not isinstance(schema, dict):
        raise ToolValidationError(f"{prefix}.custom_form_schema must be an object.")
    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        raise ToolValidationError(
            f"{prefix}.custom_form_schema.fields must be a non-empty list."
        )

    for j, field in enumerate(fields):
        fp = f"{prefix}.custom_form_schema.fields[{j}]"
        if not isinstance(field, dict):
            raise ToolValidationError(f"{fp} must be an object.")
        for key in REQUIRED_FORM_FIELD_KEYS:
            if key not in field or field[key] in (None, ""):
                raise ToolValidationError(
                    f"{fp}.{key} is required and must be non-empty."
                )
        ftype = field.get("type")
        if ftype not in FORM_FIELD_TYPES:
            # The two traps we already hit — surface a hint, not just a rejection.
            hint = ""
            if ftype == "text":
                hint = "  (use 'shortText' for single-line or 'longText' for multi-line)"
            elif ftype == "email":
                hint = "  (there is no 'email' type — use 'shortText' and add placeholder/helpText)"
            elif ftype == "select":
                hint = "  (use 'dropdown' with options=[{value,label}])"
            raise ToolValidationError(
                f"{fp}.type = {ftype!r} is not a valid FormFieldType. "
                f"Valid: {sorted(FORM_FIELD_TYPES)}.{hint}"
            )
        if ftype == "dropdown" or ftype == "radio":
            options = field.get("options")
            if not isinstance(options, list) or not options:
                raise ToolValidationError(
                    f"{fp}: type={ftype!r} requires non-empty options=[{{value,label}}]."
                )
