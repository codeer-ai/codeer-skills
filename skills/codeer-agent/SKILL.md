---
name: codeer-agent
description: Work with Codeer workspace data in Copilot. Use for conversation reports, Agent drafts and versions, user attachments, knowledge bases, evaluations, and files produced in the Sandbox.
---

# Codeer Agent

1. Identify the requested workspace and resources. The submitted page workspace is the default. Use page context to resolve names or IDs, and retrieve the saved records for analysis. Use `list_workspaces` when an explicitly requested workspace needs resolution. For a different workspace, pass its ID in `target.workspace_id` where the tool supports `target`.
2. Discover Codeer operations with `search_tools` (ToolSearch), using the exact tool name when known. Invoke the discovered tool with its input schema. Use web search for public web information. In the Sandbox, run shell commands and scripts. Codeer operation names are tool names, and the Codeer CLI is unavailable there.
3. Read the relevant reference below with `read_skill_file`, for example `{"arguments":{"path":"references/conversations.md"}}`. If the result has `has_more: true`, pass its `continuation` object as `arguments` until you have the entire reference. Search for `read_skill_file` if it is not yet available.
4. Complete explicitly requested operations in the turn and confirm the result from tools. Use platform tools for writes. Identify the exact publish, delete, or paid operation and obtain an explicit instruction for it. Report the actual saved version, result, or missing data.

| Work | Reference |
|---|---|
| Sandbox files, shell commands, RuntimeClient, or deliverables | `references/sandbox.md` |
| Conversation export, event schema, analysis, or human edits | `references/conversations.md` |
| Agent drafts, source attachments, or knowledge base changes | `references/agents-and-knowledge.md` |
| Evaluation cases, retests, and scores | `references/evaluations.md` |
