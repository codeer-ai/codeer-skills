---
name: codeer-agent
description: Work with Codeer workspace data in Copilot. Use for conversation reports, Agent drafts and versions, user attachments, knowledge bases, evaluations, and files produced in the Sandbox.
---

# Codeer Agent

1. Identify the requested workspace and resources. The submitted page workspace is the default. Use page context to resolve names or IDs, and retrieve the saved records for analysis. Use `list_workspaces` when an explicitly requested workspace needs resolution. For a different workspace, pass its ID in `target.workspace_id` where the tool supports `target`.
2. Start by calling `search_tools` (ToolSearch) for `read_skill_file` and the needed Codeer operation names. Call `read_skill_file` for the relevant reference before retrieving or changing workspace data. For example, call it with `{"arguments":{"path":"references/conversations.md"}}`. While `has_more` is true, pass `continuation` as the next `arguments`.
3. Invoke the discovered Codeer tool with its input schema. For a conversation export, apply the requested scope filters directly to `export_conversation_events`, using timezone offsets on date filters. Use web search for public web information. The Sandbox runs shell commands and scripts, and the Codeer CLI is unavailable there. For exact statistics, run a Python script in the Sandbox and read its output. For conversation metrics, start with the bundled script described in the conversation reference. Process the scoped export as returned.
4. Complete explicitly requested operations in the turn and confirm the result from tools. Use platform tools for writes. Identify the exact publish, delete, or paid operation and obtain an explicit instruction for it. Report the actual saved version, result, or missing data.

| Work | Reference |
|---|---|
| Sandbox files, shell commands, RuntimeClient, or deliverables | `references/sandbox.md` |
| Conversation export, event schema, analysis, or human edits | `references/conversations.md` |
| Agent drafts, source attachments, or knowledge base changes | `references/agents-and-knowledge.md` |
| Evaluation cases, retests, and scores | `references/evaluations.md` |
