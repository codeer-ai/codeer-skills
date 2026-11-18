"""Machine-readable contracts for the local project files the CLI reads.

``codeer agent schema`` and ``codeer eval schema`` print these so an agent can
write ``agent/settings.json`` and ``evals/design.json`` from one command instead
of reading the CLI source. Keep them aligned with ``project_agent.FIELDS``,
``_validate`` and ``project_eval.validate_design``; tests compare them.
"""

from __future__ import annotations

from typing import Any

from .constants import (
    FORM_FIELD_TYPES,
    MAX_CALL_AGENT_TOOLS,
    MAX_MEMORY_TOOLS,
    MAX_TOOLS_PER_AGENT,
    REQUIRED_FORM_FIELD_KEYS,
    UNIFIED_TOOL_TYPES,
)
from .project import PATHS

_KB_FILE_REF = r"^kb:[^/\s]+/.+$"


def _tool_schema() -> dict[str, Any]:
    def requires(tool_type: str, *fields: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        then: dict[str, Any] = {"required": list(fields)}
        if extra:
            then["properties"] = extra
        return {"if": {"properties": {"type": {"const": tool_type}}}, "then": then}

    form_field = {
        "type": "object",
        "required": list(REQUIRED_FORM_FIELD_KEYS),
        "properties": {
            "type": {"enum": sorted(FORM_FIELD_TYPES)},
            "options": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "object", "required": ["value", "label"]},
                "description": "Required when type is dropdown or radio.",
            },
        },
    }
    return {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
            "id": {"type": "string", "minLength": 1, "description": "Stable local tool ID."},
            "type": {"enum": sorted(UNIFIED_TOOL_TYPES)},
            "name": {"type": ["string", "null"]},
            "description": {"type": ["string", "null"]},
            "invocation_instruction": {"type": ["string", "null"], "description": "When the Agent should call this tool."},
            "knowledge_node_ids": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "pattern": _KB_FILE_REF},
                "description": (
                    "knowledge_base only. List file references kb:<local-id>/<path>; "
                    "the folder reference kb:<local-id> is rejected by the server."
                ),
            },
            "knowledge_node_id": {
                "type": "string",
                "pattern": _KB_FILE_REF,
                "description": "tabular_data only. One file reference kb:<local-id>/<path>.",
            },
            "custom_form_schema": {
                "type": "object",
                "required": ["fields"],
                "properties": {"title": {"type": "string"}, "fields": {"type": "array", "minItems": 1, "items": form_field}},
            },
            "http_request": {
                "type": "object",
                "required": ["method", "url_template"],
                "description": "Credentials and credential headers must be env:<VARIABLE> references.",
            },
        },
        "allOf": [
            requires("knowledge_base", "knowledge_node_ids"),
            requires("tabular_data", "knowledge_node_id"),
            requires("request_form", "custom_form_schema"),
            requires("http_request", "http_request"),
        ],
    }


def agent_schema() -> dict[str, Any]:
    from .project_agent import FIELDS

    properties: dict[str, Any] = {
        "name": {"type": "string", "minLength": 1},
        "system_prompt": {
            "type": "string",
            "description": f"Omit when {PATHS['instructions']} exists; that file is the instructions authority.",
        },
        "description": {"type": ["string", "null"]},
        "llm_model": {"type": "string", "description": "A model_id from `codeer model list --type text`."},
        "llm_model_settings": {"type": "object", "description": "Keyed by model_id."},
        "unified_tools": {"type": "array", "maxItems": MAX_TOOLS_PER_AGENT, "items": _tool_schema()},
        "attachment_ids": {"type": "array", "items": {"type": "string", "pattern": "^attachment:"}},
        "primary_object_ids": {"type": "array", "items": {"type": "string", "pattern": "^env:"}},
        "use_search": {"type": "boolean"},
        "suggested_questions": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 200}},
        "human_handoff": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "enabled": {"type": "boolean"},
                "idle_timeout_minutes": {"type": "integer"},
                "handoff_instructions": {"type": "string"},
            },
        },
        "response_mode": {"type": "string", "description": "Applied only when updating an existing Agent."},
        "output_presentation_policy": {"type": "object", "description": "Applied only when updating an existing Agent."},
    }
    assert set(properties) == set(FIELDS), "agent schema drifted from project_agent.FIELDS"
    return {
        "file": PATHS["agent"],
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "required": ["name"],
            "properties": properties,
        },
        "rules": [
            f"Instructions live in {PATHS['instructions']}; do not also set system_prompt.",
            "knowledge_node_ids lists kb file references (kb:<local-id>/<path>), never the folder kb:<local-id>.",
            "Upload KB files first with `codeer kb upload`; `codeer agent bindings` lists resolvable references.",
            f"At most {MAX_TOOLS_PER_AGENT} tools, {MAX_CALL_AGENT_TOOLS} call_agent tools and {MAX_MEMORY_TOOLS} memory tool.",
            "call_agent tools are read-only in projects and cannot be deployed with agent apply.",
        ],
        "example": {
            "name": "Support Assistant",
            "llm_model": "<model_id from codeer model list --type text>",
            "suggested_questions": ["How do I return an item?"],
            "unified_tools": [
                {
                    "id": "support-kb",
                    "type": "knowledge_base",
                    "name": "Support knowledge base",
                    "invocation_instruction": "Search before answering policy questions.",
                    "knowledge_node_ids": ["kb:support/01_policy.md"],
                }
            ],
        },
    }


def eval_schema() -> dict[str, Any]:
    from .project_eval import CASE_FIELDS, TESTER_FIELDS

    tester = {
        "type": "object",
        "required": ["local_id", "name", "system_prompt_template", "rationale"],
        "properties": {
            "local_id": {"type": "string", "minLength": 1},
            "name": {"type": "string", "minLength": 1},
            "system_prompt_template": {
                "type": "string",
                "minLength": 1,
                "description": "Judge prompt. Variables such as {output} or {tool_steps} must appear here to be visible.",
            },
            "description": {"type": ["string", "null"]},
            "judge_llm_model_id": {"type": ["string", "null"]},
            "rationale": {"type": "string", "minLength": 1, "description": "Why this Tester is reused, changed or new."},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["variable", "producer"],
                    "properties": {
                        "variable": {"type": "string"},
                        "producer": {"type": "string"},
                        "availability": {"enum": ["verified", "unverified"]},
                        "verification": {"type": "string", "description": "Project-relative file or URL proving delivery."},
                    },
                },
            },
        },
    }
    pair = {
        "type": "object",
        "required": ["tester", "rubric"],
        "properties": {
            "tester": {"type": "string", "description": "A tester local_id."},
            "rubric": {"type": "string", "minLength": 1},
            "required_evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tester evidence variables this pair depends on; each must be verified and in the template.",
            },
        },
    }
    case = {
        "type": "object",
        "required": ["local_id", "input", "source", "pairs"],
        "not": {"required": ["rubric"]},
        "properties": {
            "local_id": {"type": "string", "minLength": 1},
            "input": {"type": "string", "minLength": 1},
            "source": {
                "type": "object",
                "minProperties": 1,
                "description": "Where the case comes from, e.g. {\"document\": \"sources/sop.md\"}; local files must exist.",
            },
            "expected_output": {"type": ["string", "null"]},
            "attachment_ids": {"type": "array", "items": {"type": "string", "pattern": "^attachment:"}},
            "label_ids": {"type": "array", "items": {"type": "string", "pattern": "^env:"}},
            "meta": {"type": "object"},
            "note": {"type": ["string", "null"]},
            "pairs": {"type": "array", "minItems": 1, "items": pair},
        },
    }
    covered = {"input", "expected_output", "attachment_ids", "label_ids", "meta", "note"}
    assert covered == set(CASE_FIELDS), "eval schema drifted from project_eval.CASE_FIELDS"
    assert set(TESTER_FIELDS) <= set(tester["properties"]), "eval schema drifted from project_eval.TESTER_FIELDS"
    return {
        "file": PATHS["evals"],
        "schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["schema_version", "testers", "cases"],
            "properties": {
                "schema_version": {"const": 1},
                "testers": {"type": "array", "items": tester},
                "cases": {"type": "array", "minItems": 1, "items": case},
            },
        },
        "rules": [
            "A Rubric belongs to a case pair, never to the case itself.",
            "Each case needs at least one pair; a Tester may appear once per case.",
            "Map existing remote Testers with `codeer agent adopt --resource tester:<local-id> --remote-id <id>` before apply.",
            "Check the file with `codeer validate` before `codeer eval cases-apply --dry-run`.",
        ],
        "example": {
            "schema_version": 1,
            "testers": [
                {
                    "local_id": "content",
                    "name": "Content check",
                    "rationale": "New: no existing Tester judges answer content for this Agent.",
                    "system_prompt_template": "Judge the answer against the rubric.\nRubric: {rubric}\nAnswer: {output}",
                }
            ],
            "cases": [
                {
                    "local_id": "cancel-unshipped",
                    "input": "My order has not shipped. Can I cancel it?",
                    "source": {"document": "sources/documents/sop.md"},
                    "pairs": [{"tester": "content", "rubric": "Asks for the order number; does not claim the order is cancelled."}],
                }
            ],
        },
    }
