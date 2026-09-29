"""HTTP input *configuration* checks; value conversion belongs to the server.

Key generation follows collect_http_request_agent_placeholders in the backend's
http_request/execution.py. Keep its traversal and collision rules in sync.
"""

from __future__ import annotations

import re
from typing import Any


_AGENT_PLACEHOLDER_RE = re.compile(r"\{\{\s*agent\[(.*?)\]\s*\}\}")
_CONTRACT_FIELDS = {
    "type": ("string", "number", "integer", "boolean", "object", "array"),
    "format": ("text", "json"),
    "json_type": ("any", "object", "array"),
}


def _contract_defaults(contract: Any, key: str) -> dict[str, str]:
    prefix = f"input_contracts[{key!r}]"
    if not isinstance(contract, dict):
        raise ValueError(f"{prefix} must be an object.")
    if any(field not in _CONTRACT_FIELDS for field in contract):
        raise ValueError(
            f"{prefix} accepts only type, format, json_type (snake_case, not jsonType)."
        )
    resolved = {}
    for field, choices in _CONTRACT_FIELDS.items():
        value = contract.get(field, choices[0])
        if not isinstance(value, str) or value not in choices:
            raise ValueError(f"{prefix}.{field} must be one of: {', '.join(choices)}.")
        resolved[field] = value
    if resolved["format"] == "json" and resolved["type"] != "string":
        raise ValueError(f"{prefix}: format=json is only available for type=string.")
    if resolved["format"] != "json" and resolved["json_type"] != "any":
        raise ValueError(f"{prefix}: json_type requires format=json unless it is any.")
    return resolved


def validate_http_input_contracts(body: Any) -> list[dict[str, Any]]:
    """Validate without mutation and return value-free input format summaries.

    An omitted body is supplied as {} by callers; template may be null/absent.
    Unconfigured placeholders retain string/text/any, including mixed text.
    Unknown body fields follow the backend's existing ignore policy, except the
    frontend alias inputContracts: reject it rather than silently losing intent.
    Contract entries themselves are strict and reject all unknown fields.
    """
    if not isinstance(body, dict):
        raise ValueError("body must be an object; omit it for no body.")
    if "inputContracts" in body:
        raise ValueError("use input_contracts (snake_case), not inputContracts.")
    contracts = body.get("input_contracts", {})
    if not isinstance(contracts, dict) or any(
        not isinstance(key, str) for key in contracts
    ):
        raise ValueError("input_contracts must be an object with string keys.")
    resolved = {
        key: _contract_defaults(contract, key) for key, contract in contracts.items()
    }
    summaries: list[dict[str, Any]] = []
    used_keys: set[str] = set()

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else key)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
            return
        if not isinstance(value, str):
            return

        matches = list(_AGENT_PLACEHOLDER_RE.finditer(value))
        for index, match in enumerate(matches):
            if not match.group(1).strip():
                raise ValueError("Agent placeholder instruction cannot be empty.")
            base = (
                re.sub(r"[^a-zA-Z0-9]+", "_", path or "body").strip("_").lower()
                or "body"
            )
            if len(matches) > 1:
                base = f"{base}_{index + 1}"
            key = base
            suffix = 2
            while key in used_keys:
                key = f"{base}_{suffix}"
                suffix += 1
            used_keys.add(key)
            contract = resolved.get(key) or _contract_defaults({}, key)
            if (contract["type"] != "string" or contract["format"] == "json") and (
                len(matches) != 1 or match.group(0) != value
            ):
                raise ValueError(
                    f"Input {key!r}: typed and JSON-text inputs must occupy the entire template value."
                )
            summaries.append({"key": key, **contract, "configured": key in contracts})

    walk(body.get("template"), "")
    if set(contracts) - used_keys:
        raise ValueError(
            "input_contracts contains keys that do not match current placeholders; "
            "remove stale contracts or regenerate keys after changing template paths/order."
        )
    return summaries
