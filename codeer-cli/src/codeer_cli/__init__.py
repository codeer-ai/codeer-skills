"""Thin Python client for the Codeer internal API.

Import pattern for scripts::

    from codeer_cli import CodeerClient, agents, kb, eval_, histories, chats

    c = CodeerClient.from_env()
    agent = agents.create(c, workspace_id=..., name="My Agent", system_prompt="...", unified_tools=[])

Per-project env convention: set CODEER_AGENT_ID as an environment variable so
scripts in a customer's directory don't have to re-pass it.

The workspace and organization come from the workspace API-key virtual user's
profile, not from CLI flags or environment overrides.

Auth uses CODEER_API_KEY from process env only. CODEER_API_BASE defaults to
production and can be overridden from process env. The CLI does not read
workspace-local dotenv files or credential files.
"""

from ._validate import ToolValidationError
from .client import AuthError, CodeerClient, CodeerError
from .session_client import CodeerSessionClient, SessionConfig
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
    "CodeerClient", "CodeerSessionClient", "SessionConfig",
    "CodeerError", "AuthError", "ToolValidationError",
    # parsers
    "AgentSummary", "ConversationTurn", "EvalResultSummary", "HistorySummary",
    "KBNode", "ToolCall", "EvalToolCall",
    "parse_agent", "parse_conversation_turn", "parse_conversations",
    "parse_eval_result", "parse_eval_tool_calls", "parse_kb_node", "parse_kb_nodes",
    "parse_rubrics_from_reason",
    "parse_tool_calls", "strip_tool_markers", "summarize_eval_tool_calls", "summarize_history",
]
