# Codeer Copilot runtime

The operating modes and product workflows in this skill also apply in Copilot.
The table below translates common CLI operations into the tools available in
this environment. Use `search_tools` with the exact names, then call the
discovered tool using its input schema. Use saved platform data as evidence.
The submitted workspace is the default. Use `list_workspaces` and a supported
`target.workspace_id` to resolve an explicitly requested different workspace.
Use platform tools for writes and retain the existing scope and authorization
rules. Report when a workflow requires an operation unavailable in the tool
catalog.

| CLI workflow | Copilot tools |
|---|---|
| Locate an Agent or inspect a saved version | `external_list_agents` supports exact-name lookup. Use `external_get_agent`, `list_agent_versions`, and `external_get_agent_version` for saved state. |
| Create or update a draft | Use `external_create_agent` or `external_update_agent`. For updates use the draft's top-level `updated_at` as `expected_updated_at`; submit changed fields. `tool_types` gives tool configuration fields. When changing `unified_tools`, include the complete intended list. Read the draft back and keep its `draft_version_id`. |
| Review impact or publish an exact saved version | `list_agent_dependents`, `list_agent_versions`, and, when explicitly instructed, `publish_agent_version`. |
| Inspect, upload, and bind knowledge | Use `external_kb_list_nodes` for folder and file IDs, `get_kb_file_text` for saved text, `external_kb_upload_files` with the target folder's `parent_id` and original `file_ref_ids`, and `external_kb_file_status` for indexing. Bind the returned FILE node IDs in `knowledge_node_ids` and read back the Agent. |
| Read case, evaluator, rubric, or pairing state | Discover `external_eval_list_cases`, `external_eval_list_evaluators`, `external_eval_rubrics_batch` and `external_eval_get_case_evaluator_infos`. Read back new or changed pairings before reporting readiness. |
| Trigger and read a run | Call `start_evaluation_batch` with exact `case_evaluator_pairs` and `agent_history_id` (the saved `draft_version_id` for a retest). Read `get_evaluation_results` by `batch_id` or exact result IDs, then open its file. Check status and version before interpreting scores. |
| List, export, or analyze conversations | Follow [Copilot conversation export](copilot-conversations.md) for `list_conversations`, `export_conversation_events`, and `external_history_ai_drafts`. |

## Sandbox and files

- The working directory is `/workspace`. Use the returned paths and download
  again if that Sandbox has been replaced. A local draft file is separate from
  a saved Agent or KB resource.
- For current-message attachments, use `get_attachment_text` with
  `arguments.attachment_id` and a Sandbox destination, omitting `target`.
  Read the returned JSON file's `text`. For an upload, future reuse, or when
  conversion is insufficient, use `download_current_message_attachment` to
  fetch the original. Freeze originals for upload or reuse before replying.
- Use `write_file` for multiline Python, then call `run_command` with
  `python3 <script-path>`. Check the exit code and read bounded ranges from
  its `stdout_path` and `stderr_path`. For long commands, use `start_command`
  and track its `command_id` with `check_command` until terminal. Use
  `stop_command` for cancellation.
- Use `read_skill_file` with `arguments.path` to read a bundled reference.
  To copy a bundled script into the VM, use `skill_file` with `arguments.path`
  and `destination`.
- Validate output files, freeze each with `freeze_sandbox_file`, and use
  `deliver_file_ref` for each file the user should receive.

## RuntimeClient

Use the platform tool for ordinary calls. ToolSearch exposes its input schema
and description. For `export_conversation_events`, use the conversation
reference for the return envelope and JSONL rows.

For a script that needs to fetch Codeer data itself, import `RuntimeClient`
from `runtime_client`. The Sandbox configures the client's connection and
turn-scoped credentials. `read_json("list_operations", {})` returns the
read-only catalog, and `read_json("operation_schema", {"name": operation})`
returns its argument `schema` and `mode`. Use
`read_json(operation, arguments)` for JSON and
`query(operation, arguments, destination=...)` for file results. Pass the
inner arguments object. To select a different workspace, pass an optional
`target={"workspace_id": "..."}` where supported.

A successful `query` returns `path` (a `Path`), `size_bytes` (an integer),
and optional `coverage`. An incomplete download raises an error before the
file is published at its destination.

### Example — inventory event kinds for one conversation

Save as `event_inventory.py`, then run `python3 event_inventory.py <history-id>`
with a resolved History ID. Read stdout for the event inventory.

```python
import argparse
import json
from collections import Counter

from runtime_client import RuntimeClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("history_id", type=int)
    args = parser.parse_args()
    export = RuntimeClient().query(
        "export_conversation_events",
        {"sources": [{"history_id": args.history_id}]},
        destination="exports/event-inventory.jsonl",
    )
    with export.path.open(encoding="utf-8") as source:
        counts = Counter(json.loads(line)["part_kind"] for line in source)
    print(json.dumps({"export": str(export.path), "coverage": export.coverage,
                      "event_kinds": dict(counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
```
