"""Enum values and known identifiers, kept in sync with the backend + frontend.

Having these in one place stops callers from inventing strings like ``"text"``
or ``"select"`` that silently save as broken config. If you're adding a new
tool type or form field type, update both the backend (``codeer/agents/types.py``,
``web/src/types/requestForm.ts``) and this file.
"""

from __future__ import annotations

# Unified tool types accepted on an Agent's ``unified_tools[]`` list.
# Source: codeer/agents/types.py :: UnifiedToolType
UNIFIED_TOOL_TYPES: frozenset[str] = frozenset({
    "knowledge_base",
    "web_search",
    "call_agent",
    "image_generation",
    "request_form",
    "payment",
    "memory",
    "http_request",
})

# Valid type values for a field inside ``custom_form_schema.fields[]``.
# Source: web/src/types/requestForm.ts :: FormFieldType
# NOTE: there is no ``"email"`` / ``"text"`` / ``"select"`` type. Common gotchas:
#   email  → use "shortText" (plus helpText/placeholder to hint the format)
#   text   → use "shortText" (single-line) or "longText" (multi-line)
#   select → use "dropdown" (with ``options: [{value,label}]``)
FORM_FIELD_TYPES: frozenset[str] = frozenset({
    "shortText",
    "longText",
    "number",
    "dropdown",
    "radio",
    "checkbox",
    "date",
})

# An agent's ``publish_state``.
# Source: codeer/agents/types.py :: PublishState
PUBLISH_STATES: frozenset[str] = frozenset({
    "private",
    "in_organization",
    "public",
})

# ``AgentHistory.status`` values returned by ``GET /agents/{id}/histories``.
# Source: codeer/agents/types.py :: AgentHistoryStatus
AGENT_HISTORY_STATUSES: frozenset[str] = frozenset({
    "draft",
    "published",
    "archived",
})

# Hard limits mirrored from user-docs/agent-creation/tools/index.md. Enforce
# client-side so we fail before the server rejects.
MAX_TOOLS_PER_AGENT = 10
MAX_CALL_AGENT_TOOLS = 5
MAX_MEMORY_TOOLS = 1

# Fields that must be set (and non-empty) on every form-builder field so the UI
# renders labels and the backend can capture submissions by a stable key.
# ``name`` is the submission key, ``label`` is the analytics/column name,
# ``question`` is the user-facing prompt.
REQUIRED_FORM_FIELD_KEYS: tuple[str, ...] = ("id", "type", "name", "label", "question", "required")
