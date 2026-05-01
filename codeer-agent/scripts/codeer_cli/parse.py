"""Typed parsers for Codeer API response shapes.

Use these instead of digging through dicts in every caller. Each ``parse_*``
function accepts the raw envelope-unwrapped payload (i.e. what the
``codeer_cli`` helpers already return) and produces a small frozen dataclass
plus a few derived rollups that come up over and over again.

Parsers are deliberately tolerant: missing/extra fields don't raise, casing
mismatches (``FILE`` vs ``file``) are normalized to lowercase. They are NOT a
schema validator — for that, follow ``API_CHEATSHEET.md``.

KEY GAP, called out here so you don't waste time:

  Tool **arguments** (e.g. the regex passed to ``list_kb_files`` or the query
  passed to ``retrieve_context_objs``) and **outputs** are not persisted on the
  Conversation row. They flow over the WebSocket during execution and are
  dropped after the assistant turn is saved. What you CAN recover from a
  history is:

    - tool name + call id     (regex over ``content``: ``<tool id=...>name</tool>``)
    - per-call token usage    (``meta.token_usage.tool_calls[]``)
    - retrieved primary sources (``primary_sources[]`` — the end-to-end trace)
    - assistant's final text   (``content`` with tool markers stripped)

  If you need the raw tool args, you must capture them at execution time via
  the chat SSE stream, not from history reads.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional

# ---------------------------------------------------------------------------
# Tool calls (stored as `<tool id=call_xxx>tool_name</tool>` inside `content`)
# ---------------------------------------------------------------------------

_TOOL_TAG_RE = re.compile(r"<tool\s+id=([A-Za-z0-9_\-]+)>([A-Za-z_][A-Za-z_0-9]*)</tool>")


@dataclass(frozen=True)
class ToolCall:
    name: str
    call_id: str
    # The token-usage entry for this call (matched positionally to the tool tags
    # in `content`, since the API doesn't link the two by id). May be ``None``
    # if the assistant turn ended before tool execution finished.
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model: Optional[str] = None


@dataclass(frozen=True)
class EvalToolCall:
    name: str
    call_id: Optional[str] = None
    status: Optional[str] = None
    arguments: Any = None
    output: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    raw: dict = field(default_factory=dict)


_EVAL_TOOL_CONTAINER_KEYS = (
    "reasoning_steps",
    "tool_calls",
    "tool_call_trace",
    "tool_calling_trace",
    "tool_trace",
    "tool_traces",
    "trace",
)


def _first_present(raw: dict, keys: Iterable[str]) -> Any:
    for key in keys:
        if key in raw and raw.get(key) not in (None, ""):
            return raw.get(key)
    return None


def _duration_ms(raw: dict) -> Optional[float]:
    for key in ("duration_ms", "elapsed_ms", "latency_ms", "execution_time_ms", "time_ms"):
        val = raw.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    for key in ("duration_s", "elapsed_s", "latency_s", "execution_time", "execution_time_s"):
        val = raw.get(key)
        if isinstance(val, (int, float)):
            return float(val) * 1000
    started = _first_present(raw, ("start_at", "started_at", "start_time", "created_at"))
    ended = _first_present(raw, ("end_at", "ended_at", "end_time", "completed_at", "finished_at"))
    if isinstance(started, str) and isinstance(ended, str):
        try:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
        except ValueError:
            return None
        return max((end_dt - start_dt).total_seconds() * 1000, 0)
    return None


def _tool_name(raw: dict) -> str:
    name = _first_present(raw, ("name", "tool_name", "function_name", "type"))
    if name:
        return str(name)
    function = raw.get("function")
    if isinstance(function, dict) and function.get("name"):
        return str(function["name"])
    tool = raw.get("tool")
    if isinstance(tool, dict) and tool.get("name"):
        return str(tool["name"])
    return ""


def _normalize_eval_tool_call(raw: dict) -> EvalToolCall:
    function = raw.get("function") if isinstance(raw.get("function"), dict) else {}
    return EvalToolCall(
        name=_tool_name(raw),
        call_id=_first_present(raw, ("id", "call_id", "tool_call_id")),
        status=_first_present(raw, ("status", "state")),
        arguments=_first_present(raw, ("arguments", "args", "input", "parameters")) or function.get("arguments"),
        output=_first_present(raw, ("output", "result", "response")),
        error=_first_present(raw, ("error", "error_message")),
        duration_ms=_duration_ms(raw),
        started_at=_first_present(raw, ("start_at", "started_at", "start_time", "created_at")),
        ended_at=_first_present(raw, ("end_at", "ended_at", "end_time", "completed_at", "finished_at")),
        raw=raw,
    )


def _iter_eval_tool_payloads(value: Any) -> Iterable[dict]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(value, dict):
        return
    for key in ("calls", "tool_calls", "steps", "events", "items"):
        nested = value.get(key)
        if isinstance(nested, list):
            for item in nested:
                if isinstance(item, dict):
                    yield item
            return
    if _tool_name(value):
        yield value


def parse_eval_tool_calls(raw: dict) -> list[EvalToolCall]:
    """Extract tool-call trace details from an eval result row, if present.

    Current eval rows expose this as ``reasoning_steps`` when callers pass
    ``include_reasoning_steps=true``. The parser also accepts earlier trace
    field-name variants while this data was being added.
    """
    out: list[EvalToolCall] = []
    containers = [raw]
    for key in ("meta", "metadata", "debug", "execution", "run"):
        value = raw.get(key)
        if isinstance(value, dict):
            containers.append(value)
    for container in containers:
        for key in _EVAL_TOOL_CONTAINER_KEYS:
            if key in container:
                for item in _iter_eval_tool_payloads(container[key]):
                    call = _normalize_eval_tool_call(item)
                    if call.name or call.call_id:
                        out.append(call)
    if out:
        return out

    # Fallback for older rows where only the assistant output/content persisted
    # tool markers. This gives name + call id, but not args/output/timing.
    content = raw.get("output") or raw.get("actual_output") or raw.get("content") or ""
    return [
        EvalToolCall(name=tc.name, call_id=tc.call_id, raw={"source": "output_tool_marker"})
        for tc in parse_tool_calls(content)
    ]


def summarize_eval_tool_calls(calls: Iterable[EvalToolCall]) -> str:
    parts = []
    for call in calls:
        label = call.name or call.call_id or "tool"
        if call.duration_ms is not None:
            label = f"{label} ({call.duration_ms:g} ms)"
        parts.append(label)
    return ", ".join(parts)


def parse_tool_calls(content: str, token_usage: Optional[dict] = None) -> list[ToolCall]:
    """Pull tool calls out of an assistant turn's ``content``.

    ``token_usage`` is the assistant turn's ``meta.token_usage`` dict (so we
    can attach per-call token counts). It's optional — pass ``None`` to skip.
    """
    if not content:
        return []
    tags = _TOOL_TAG_RE.findall(content)
    usage_list: list[dict] = []
    if isinstance(token_usage, dict):
        usage_list = list(token_usage.get("tool_calls") or [])

    out: list[ToolCall] = []
    for i, (call_id, name) in enumerate(tags):
        u = usage_list[i] if i < len(usage_list) else {}
        out.append(ToolCall(
            name=name,
            call_id=call_id,
            prompt_tokens=u.get("prompt_tokens"),
            completion_tokens=u.get("completion_tokens"),
            total_tokens=u.get("total_tokens"),
            model=u.get("model"),
        ))
    return out


def strip_tool_markers(content: str) -> str:
    """Return the assistant's final-answer text with ``<tool …>`` markers removed."""
    if not content:
        return ""
    return _TOOL_TAG_RE.sub("", content).strip()


# ---------------------------------------------------------------------------
# Conversation turns (one row per system/user/assistant message)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConversationTurn:
    id: Optional[int]
    role: str  # "system" | "user" | "assistant"
    group_id: Optional[str]
    text: str            # content with tool markers stripped (use for display)
    raw_content: str     # original content including <tool …> tags
    tool_calls: list[ToolCall]
    primary_source_ids: list[str]
    score: Optional[int]
    feedback_tags: list[str]   # e.g. ["sys_helpful"], ["sys_improve"]
    feedback_comments: list[str]
    response_time_ms: Optional[int]
    total_tokens: Optional[int]
    cost_credits: Optional[float]


def parse_conversation_turn(raw: dict) -> ConversationTurn:
    meta = raw.get("meta") or {}
    token_usage = meta.get("token_usage") or {}
    primary = raw.get("primary_sources") or []
    feedbacks = raw.get("feedbacks") or []

    return ConversationTurn(
        id=raw.get("id"),
        role=raw.get("role") or "",
        group_id=raw.get("group_id"),
        text=strip_tool_markers(raw.get("content") or ""),
        raw_content=raw.get("content") or "",
        tool_calls=parse_tool_calls(raw.get("content") or "", token_usage),
        primary_source_ids=[ps.get("id") for ps in primary if isinstance(ps, dict) and ps.get("id")],
        score=raw.get("score") if raw.get("score") not in (0, None) else None,
        feedback_tags=[fb.get("tag") for fb in feedbacks if fb.get("tag")],
        feedback_comments=[fb.get("content") for fb in feedbacks if fb.get("content")],
        response_time_ms=meta.get("response_time_ms"),
        total_tokens=token_usage.get("total_tokens"),
        cost_credits=meta.get("cost_credits"),
    )


def parse_conversations(raw_list: Iterable[dict]) -> list[ConversationTurn]:
    return [parse_conversation_turn(c) for c in raw_list]


# ---------------------------------------------------------------------------
# History rollup (one history = many conversation turns)
# ---------------------------------------------------------------------------

@dataclass
class HistorySummary:
    id: int
    title: str
    agent_id: Optional[str]
    agent_name: Optional[str]
    external_user_id: Optional[str]
    share_type: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    n_turns: int
    n_user: int
    n_assistant: int
    n_system: int
    tool_counts: Counter            # tool_name -> call count
    primary_sources_seen: int       # distinct primary_source ids referenced
    total_tokens: int               # summed across turns
    total_credits: float            # summed across turns
    feedback_tags: Counter          # e.g. {"sys_helpful": 0, "sys_improve": 1}
    avg_response_time_ms: Optional[float]
    first_user_message: str
    last_assistant_message: str
    turns: list[ConversationTurn] = field(default_factory=list)


def summarize_history(history_raw: dict, conversations_raw: list[dict]) -> HistorySummary:
    turns = parse_conversations(conversations_raw)
    tool_counter: Counter = Counter()
    primary_ids: set[str] = set()
    feedback_counter: Counter = Counter()
    rt_samples: list[int] = []
    total_tokens = 0
    total_credits = 0.0

    for t in turns:
        for tc in t.tool_calls:
            tool_counter[tc.name] += 1
        for pid in t.primary_source_ids:
            primary_ids.add(pid)
        for tag in t.feedback_tags:
            feedback_counter[tag] += 1
        if t.response_time_ms is not None:
            rt_samples.append(t.response_time_ms)
        if t.total_tokens:
            total_tokens += t.total_tokens
        if t.cost_credits:
            total_credits += t.cost_credits

    user_msgs = [t.text for t in turns if t.role == "user"]
    asst_msgs = [t.text for t in turns if t.role == "assistant"]

    return HistorySummary(
        id=history_raw["id"],
        title=history_raw.get("name") or history_raw.get("title") or "",
        agent_id=history_raw.get("agent_id"),
        agent_name=history_raw.get("agent_name"),
        external_user_id=history_raw.get("external_user_id"),
        share_type=history_raw.get("share_type"),
        created_at=history_raw.get("created_at"),
        updated_at=history_raw.get("updated_at"),
        n_turns=len(turns),
        n_user=sum(1 for t in turns if t.role == "user"),
        n_assistant=sum(1 for t in turns if t.role == "assistant"),
        n_system=sum(1 for t in turns if t.role == "system"),
        tool_counts=tool_counter,
        primary_sources_seen=len(primary_ids),
        total_tokens=total_tokens,
        total_credits=total_credits,
        feedback_tags=feedback_counter,
        avg_response_time_ms=(sum(rt_samples) / len(rt_samples)) if rt_samples else None,
        first_user_message=(user_msgs[0] if user_msgs else "")[:200],
        last_assistant_message=(asst_msgs[-1] if asst_msgs else "")[:200],
        turns=turns,
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@dataclass
class AgentSummary:
    id: str
    name: str
    description: Optional[str]
    workspace_id: Optional[str]
    publish_state: Optional[str]
    version: Optional[int]
    latest_version_number: Optional[int]
    published_version_number: Optional[int]
    publish_history_id: Optional[str]
    llm_model: Optional[str]
    use_search: bool
    suggested_questions: list[str]

    # Derived from unified_tools
    tools_by_type: dict[str, list[dict]]   # "memory" -> [tool_dict, ...]
    kb_attached_node_ids: list[str]        # union of all KB tools' knowledge_node_ids
    form_field_names: list[str]            # field names from the first request_form tool
    call_agent_targets: list[str]          # agent_ids referenced by call_agent tools
    http_request_endpoints: list[str]      # method+url_template strings

    raw: dict = field(default_factory=dict, repr=False)


def parse_agent(raw: dict) -> AgentSummary:
    tools = raw.get("unified_tools") or []
    by_type: dict[str, list[dict]] = {}
    for t in tools:
        by_type.setdefault(t.get("type") or "?", []).append(t)

    kb_nodes = []
    for t in by_type.get("knowledge_base", []):
        kb_nodes.extend(t.get("knowledge_node_ids") or [])

    form_fields = []
    for t in by_type.get("request_form", []):
        schema = t.get("custom_form_schema") or {}
        form_fields = [f.get("name") for f in schema.get("fields", []) if f.get("name")]
        break

    call_targets = [t.get("agent_id") for t in by_type.get("call_agent", []) if t.get("agent_id")]

    http_eps = []
    for t in by_type.get("http_request", []):
        cfg = t.get("http_request") or {}
        http_eps.append(f"{cfg.get('method','?')} {cfg.get('url_template','?')}")

    return AgentSummary(
        id=str(raw.get("id")),
        name=raw.get("name") or "",
        description=raw.get("description"),
        workspace_id=raw.get("workspace_id"),
        publish_state=raw.get("publish_state"),
        version=raw.get("version"),
        latest_version_number=raw.get("latest_version_number"),
        published_version_number=raw.get("published_version_number"),
        publish_history_id=raw.get("publish_history_id"),
        llm_model=raw.get("llm_model"),
        use_search=bool(raw.get("use_search")),
        suggested_questions=list(raw.get("suggested_questions") or []),
        tools_by_type=by_type,
        kb_attached_node_ids=kb_nodes,
        form_field_names=form_fields,
        call_agent_targets=call_targets,
        http_request_endpoints=http_eps,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# Eval result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvalResultSummary:
    id: str
    case_id: str
    evaluator_id: str
    agent_history_id: Optional[str]
    status: str                        # PENDING/RUNNING/READY/FAILED/etc.
    score: Optional[float]             # 0.0–1.0
    reason: Optional[str]              # judge's explanation
    output: Optional[str]              # the agent response that was scored
    execution_time_s: Optional[float]
    cost_credits: Optional[int]
    tool_calls: list[EvalToolCall] = field(default_factory=list)


def parse_eval_result(raw: dict) -> EvalResultSummary:
    return EvalResultSummary(
        id=str(raw.get("id")),
        case_id=str(raw.get("evaluation_case_id") or raw.get("case_id") or ""),
        evaluator_id=str(raw.get("evaluator_id") or ""),
        agent_history_id=raw.get("agent_history_id"),
        status=str(raw.get("status") or ""),
        score=raw.get("score"),
        reason=raw.get("reason"),
        output=raw.get("output") or raw.get("actual_output"),
        execution_time_s=raw.get("execution_time") or raw.get("execution_time_s"),
        cost_credits=raw.get("cost_credits"),
        tool_calls=parse_eval_tool_calls(raw),
    )


# ---------------------------------------------------------------------------
# Rubric extraction from eval result `reason` text
# ---------------------------------------------------------------------------
#
# The Codeer API has NO GET endpoint for rubrics — they live only as part of
# completed eval result rows, quoted at the head of each judge's `reason`.
# This parser reverses that: given a `reason` string, returns the list of
# rubric rules the judge was checking against.
#
# Patterns covered (verified against real production results in 2026-04):
#   1. Rubric Rule: "<rule>"   ✓ (compliant): ...
#   2. <rule>。✓（符合） - ...
#   3. 規則：「<rule>」✓（遵守）...
#   4. <label>：✓（合規）  ← falls back to label-only
#   5. <rule> → ✓ (compliant) ...
#   6. Content rule: <rule>  ✗ (違規): ...
#
# Limitation: when the rubric was just a label and the full text only appears
# in the analysis after the verdict, you get the label only. This is the price
# of the API not exposing rubrics directly.

_NUMBERED_ITEM_RE = re.compile(
    r"(?:^|\n)\s*(\d+)\.\s+(.+?)(?=(?:\n\s*\d+\.\s+)|\Z)",
    re.DOTALL,
)
_VERDICT_MARKER_RE = re.compile(r"(?:→\s*)?[✓✗]")
_RULE_LABEL_RE = re.compile(
    r"^(?:Rubric\s+Rule|Rubric|Content[\s_-]+(?:Boundary[\s_-]+)?[Rr]ule|Rule|規則|內容規則|Content\s+rule|Content\s+Rule)\s*[:：]\s*",
    re.IGNORECASE,
)


def parse_rubrics_from_reason(reason: str) -> list[str]:
    """Extract per-rule rubric texts from an eval judge's ``reason`` field.

    Returns the cleaned rule texts in order. Returns ``[]`` when no rules can
    be parsed (including the ``"No content boundary rules were provided"``
    case, which means the rubric was empty when the run was triggered).

    KNOWN LIMITATION: when the original rubric was just a short label
    (e.g. ``"安全性與衛教界線"``) and the verbose rule statement only appears
    in the analysis text *after* the verdict marker, the parser returns only
    the label. The Codeer API doesn't persist rubrics as their own field, so
    the verbose text is genuinely unrecoverable from result rows.
    """
    if not reason:
        return []
    out: list[str] = []
    for _num, body in _NUMBERED_ITEM_RE.findall(reason):
        head = _VERDICT_MARKER_RE.split(body, maxsplit=1)[0]
        head = head.rstrip()
        head = _RULE_LABEL_RE.sub("", head)
        # Strip surrounding straight + CJK quotes
        head = head.strip().strip('"\'').strip("「」『』").strip()
        # Trim trailing punctuation that hugs the verdict (sentence-end or
        # the colon-form "<rule>：✓" which leaves a dangling colon)
        head = head.rstrip("。.：:").strip()
        if not head:
            continue
        if "No content boundary rules" in head or "no rules to violate" in head.lower():
            continue
        out.append(head)
    return out


# ---------------------------------------------------------------------------
# KB node — normalize the uppercase enum quirk
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KBNode:
    id: str
    name: str
    node_type: str           # 'folder' or 'file' (lowercased)
    parent_id: Optional[str]
    knowledge_base_id: Optional[str]
    status: Optional[str]    # PENDING/INDEXING/READY/FAILED/None for folders
    size_bytes: Optional[int]
    content_type: Optional[str]


def parse_kb_node(raw: dict) -> KBNode:
    return KBNode(
        id=str(raw.get("id")),
        name=raw.get("name") or "",
        node_type=(raw.get("node_type") or "").lower(),
        parent_id=raw.get("parent_id"),
        knowledge_base_id=raw.get("knowledge_base_id"),
        status=raw.get("status"),
        size_bytes=raw.get("size_bytes"),
        content_type=raw.get("content_type"),
    )


def parse_kb_nodes(raw_list: Iterable[dict]) -> list[KBNode]:
    return [parse_kb_node(n) for n in raw_list]
