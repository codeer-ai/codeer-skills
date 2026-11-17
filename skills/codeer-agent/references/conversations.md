# Conversation data and analysis

1. Confirm the requested Agent ID if the user names a specific Agent. Resolve an exact name with `external_list_agents` in the requested workspace. For all workspace conversations, omit `agent_id`. Treat Agent, History and turn IDs as different identifiers.
2. Resolve the time window from the user's wording, the current date when needed, and the user's timezone. For conversations created in a period, set `history_created_from` and `history_created_until`. For turns started in a period, set `turn_created_from` and `turn_created_until`. A turn window selects each matching user prompt and its group of events. Starts are inclusive and ends are exclusive. For a calendar period, use local midnight at the start and at the first day after the period.
3. Use `search_tools` for `export_conversation_events` and call it directly. Use `list_conversations` for History IDs, previews, or coverage checks. It returns `histories` and `next_offset`; when a complete list is needed, follow each `next_offset` until null. Send broad filters directly to export rather than narrowing the export to a list page. When comparing History cohorts, use the same History creation boundaries for listing and exporting.
4. Verify the export's returned coverage and open the returned file path. Where events exist, inspect a small sample before parsing. A successful zero-part export describes the queried scope. For a missing file, tool error, mismatched coverage, or incomplete export, diagnose the retrieval before making a claim. Report matching Histories with missing usable text separately if applicable.

## Export tool input

The tool takes `arguments.sources` (one to twenty sources), `destination` (Sandbox path), and optional `target.workspace_id`. Each source can specify these filters. Omit a filter to leave it unrestricted.

| Source field | Type and meaning |
|---|---|
| `workspace_id` | UUID for this source. Otherwise use the outer target or the current workspace. |
| `history_id` | Positive integer for one History. |
| `agent_id`, `agent_version_id` | UUIDs for Agent or exact-version attribution. |
| `history_created_from`, `history_created_until` | ISO 8601 timestamps with offsets for History creation. |
| `turn_created_from`, `turn_created_until` | ISO 8601 timestamps with offsets for user turn creation. |

For example, export all turns that began on April 6, 2026 in Taipei for an audit of tool usage. Discover `export_conversation_events` and invoke it with:

```json
{
  "arguments": {
    "sources": [{
      "turn_created_from": "2026-04-06T00:00:00+08:00",
      "turn_created_until": "2026-04-07T00:00:00+08:00"
    }]
  },
  "destination": "exports/april-06-tool-audit.jsonl"
}
```

## Export result and JSONL row schema

| Result field | Shape |
|---|---|
| `path` | String, the Sandbox file path. |
| `size_bytes` | Integer, the size of the completed export. |
| `coverage` | Array, one entry per source with `workspace_id` (UUID string), `cutoff` (integer part ID watermark), and `part_count` (integer count of all exported event rows). |

Read the file as UTF-8 with one JSON object per line. An example row:

```json
{"workspace_id":"e391d173-b892-4b5d-802f-137db71afe35","history_id":102,"group_id":"48bdc0fc-4590-4c7d-9a47-87f293a59570","part_id":299,"sequence":0,"part_kind":"user-prompt","created_at":"2026-04-06T02:10:00Z","content":{"part_kind":"user-prompt","content":"Can I reschedule my delivery?"}}
```

- `workspace_id` and `history_id` identify the conversation. `group_id` groups events from one turn within a History. `part_id` identifies the event and `sequence` orders it within the turn. `created_at` is the event timestamp.
- For message-body analysis, look for `part_kind` equal to `user-prompt` or `text` and a string at `row["content"]["content"]`. Measure the original string when the metric calls for it. Keep missing and empty bodies visible where they affect the denominator. Other kinds include tool events and carry different payloads. `part_count` is an event count.
- Group or deduplicate according to the requested unit. Use History keys for conversations, group keys for turns, and part IDs for events. For overlapping export sources, deduplicate by workspace and part ID before calculating metrics. Keep user prompts and assistant text separate if the question asks for either population.
- For human edits, discover `external_history_ai_drafts` and compare `items[].content` (original AI draft) with `items[].delivery.actual_content` (actual sent text). Count verified differences and identify missing originals or deliveries separately.
- Generate requested formats in the Sandbox. For a CSV, write headers and validate the transformed rows. For a Markdown report, include scope, denominators and source identifiers where useful. Freeze and deliver each requested file.
