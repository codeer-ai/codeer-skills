---
name: codeer-agent
description: Work with Codeer workspace data in Copilot. Use for conversation reports, Agent drafts and versions, user attachments, knowledge bases, evaluations, and files produced in the Sandbox.
---

# Codeer Agent

1. Identify the requested workspace and resources. The submitted page workspace is the default. Use page context to resolve names or IDs, and retrieve the saved records for analysis. Use `list_workspaces` when an explicitly requested workspace needs resolution. For a different workspace, pass its ID in `target.workspace_id` where the tool supports `target`.
2. Start by calling `search_tools` (ToolSearch) for `read_skill_file` and the needed Codeer operation names. Call `read_skill_file` for the relevant reference before retrieving or changing workspace data. For example, call `read_skill_file` with `{"arguments":{"path":"reference/copilot-conversations.md"}}`. While `has_more` is true, pass `continuation` as the next `arguments`. Use `read_file` for Sandbox files and downloaded results.
3. Invoke the discovered Codeer tool with its input schema. For a conversation export, apply the requested scope filters directly to `export_conversation_events`, using timezone offsets on date filters. Use web search for public web information. The Sandbox runs shell commands and scripts, and the Codeer CLI is unavailable there. For exact statistics, run a Python script in the Sandbox and read its output. For conversation metrics, start with the bundled script described in the conversation reference. Process the scoped export as returned.
4. Complete explicitly requested operations in the turn and confirm the result from tools. Use platform tools for writes. Identify the exact publish, delete, or paid operation and obtain an explicit instruction for it. Report the actual saved version, result, or missing data.

| Work | Reference |
|---|---|
| Sandbox files, shell commands, RuntimeClient, or deliverables | `reference/copilot-runtime.md` |
| Conversation export, event schema, analysis, or human edits | `reference/copilot-conversations.md` |
| Agent drafts, source attachments, or knowledge base changes | `reference/copilot-runtime.md` for the upload and binding workflow, then `modules/kb-and-agent.md` for design as needed |
| Evaluation cases, retests, and scores | `reference/copilot-runtime.md` for saved drafts and batch results, then `modules/eval-cases.md` for case design as needed |

For an attachment the user wants in an Agent's knowledge base, use the original file and bind the uploaded KB file node to the saved draft. For a score or run diagnosis, search for `get_evaluation_results` and pass the batch ID as `batch_id`.

For Agent design, audit, repair, and publication, use `read_skill_file` with
`{"arguments":{"path":"SKILL.md"}}` to consult the original mode router and
follow its relevant modules. Paths passed to `read_skill_file` are relative
to the full skill bundle. Apply the original design, evidence, and authorization
rules. Use the runtime reference to translate CLI-specific steps into available
Copilot tools. Read `modules/history.md` when the user asks for behavior audit,
sampling, or improvement beyond a direct data request.
