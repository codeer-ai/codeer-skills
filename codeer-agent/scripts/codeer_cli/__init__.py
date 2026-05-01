"""Thin Python client for the Codeer internal API.

Import pattern for scripts::

    from codeer_cli import CodeerClient, agents, kb, eval_, histories, chats

    c = CodeerClient.from_env()
    agent = agents.create(c, workspace_id=..., name="My Agent", system_prompt="...", unified_tools=[])

Per-project env convention: set CODEER_WORKSPACE_ID, CODEER_ORGANIZATION_ID
and CODEER_AGENT_ID in ``.claude/settings.json`` (env block) so scripts in a
customer's directory don't have to re-pass these args. The global
``~/.codeer/session.env`` should hold only auth (CODEER_API_BASE,
CODEER_SESSION_ID, CODEER_CSRF_TOKEN). See ``API_CHEATSHEET.md`` → "Session
config" for the rationale.
"""

from ._validate import ToolValidationError
from .client import AuthError, CodeerClient, CodeerError
from .parse import (
    AgentSummary,
    ConversationTurn,
    EvalResultSummary,
    EvalToolCall,
    HistorySummary,
    KBNode,
    ToolCall,
    parse_agent,
    parse_conversation_turn,
    parse_conversations,
    parse_eval_result,
    parse_eval_tool_calls,
    parse_kb_node,
    parse_kb_nodes,
    parse_rubrics_from_reason,
    parse_tool_calls,
    strip_tool_markers,
    summarize_eval_tool_calls,
    summarize_history,
)

__all__ = [
    "CodeerClient", "CodeerError", "AuthError", "ToolValidationError",
    # parsers
    "AgentSummary", "ConversationTurn", "EvalResultSummary", "HistorySummary",
    "KBNode", "ToolCall", "EvalToolCall",
    "parse_agent", "parse_conversation_turn", "parse_conversations",
    "parse_eval_result", "parse_eval_tool_calls", "parse_kb_node", "parse_kb_nodes",
    "parse_rubrics_from_reason",
    "parse_tool_calls", "strip_tool_markers", "summarize_eval_tool_calls", "summarize_history",
]
