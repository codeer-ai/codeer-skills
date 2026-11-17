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
| Inspect knowledge | Use `external_kb_list_nodes` for folder and file IDs and `get_kb_file_text` for saved text. To attach sources, follow [the upload and binding workflow](#attach-files-to-an-agents-knowledge-base). |
| Read case, evaluator, rubric, or pairing state | Discover `external_eval_list_cases`, `external_eval_list_evaluators`, `external_eval_rubrics_batch` and `external_eval_get_case_evaluator_infos`. Read back new or changed pairings before reporting readiness. |
| Trigger and read a run | Follow [the evaluation workflow](#run-evaluations-and-read-scores). |
| List, export, or analyze conversations | Follow [Copilot conversation export](copilot-conversations.md) for `list_conversations`, `export_conversation_events`, and `external_history_ai_drafts`. |

## Attach files to an Agent's knowledge base

1. For a chat attachment, call `download_current_message_attachment` with the
   current message's `attachment_id` and a `destination` that keeps the original
   filename. Pass the returned Sandbox path to `freeze_sandbox_file` and keep
   its `file_ref_id`. `get_attachment_text` produces converted JSON for reading.
   If the user will want to attach the original in a later turn, freeze it
   while the source is still on the current message and reuse that FileRef.
   If the earlier original is unavailable, ask the user to attach it again.
2. Resolve the target folder with `external_kb_list_nodes` in the Agent's
   workspace. Use the chosen KB root or subfolder node's `id` as `parent_id`.
   Use `external_create_kb_node` to create a needed folder within the requested
   KB scope.
   Call `external_kb_upload_files` with `parent_id` and the original
   `file_ref_ids`. Read each entry in `nodes`. Keep successful `node_id`
   values and check any `error_message` before retrying a failed file.
   For a source already in the KB, use its existing file node from the list.
3. Use `tool_types` with `tool_type: "knowledge_base"`, then set the draft's
   `unified_tools` to include the KB tool. A tool entry has this shape:

   ```json
   {"id":"<tool-id>","type":"knowledge_base","knowledge_node_ids":["<kb-file-node-id>"]}
   ```

   Use FILE node IDs from upload or listing in `knowledge_node_ids`.
   `parent_id` selects a folder for upload, `file_ref_ids` identify the
   frozen Sandbox input, and `attachment_ids` configures Agent attachments.
   For an existing draft, read it first, preserve the IDs and settings of
   existing tools, and send the complete intended tool list.
4. Read back the saved draft or exact saved version and confirm the expected
   file node IDs in the KB tool. Check those IDs with `external_kb_file_status`.
   Binding and indexing complete independently. Report the attachment as
   bound only after readback and as ready for retrieval only when indexing is
   `READY`. A file written or frozen in the Sandbox is still an upload input.

## Run evaluations and read scores

- If the user provides a `batch_id` or asks how a run scored, discover
  `get_evaluation_results` and call it with
  `{"arguments":{"batch_id":"<batch-id>"},"destination":"eval/results.json"}`.
  Open the returned path with `read_file`. Use `result_ids` for individual
  result IDs. A case ID addresses the case definition, while a batch ID
  addresses the recorded run. Use `get_evaluation_results` for the recorded
  evaluator score, reason, and answer.
- For an authorized prompt-only retest, read the draft with
  `external_get_agent`. Call `external_update_agent` with `agent_id`,
  `expected_updated_at` from the draft and the full revised `system_prompt`.
  Confirm the change in `external_get_agent_version` with the returned
  `draft_version_id` as `version_id`. Pass that same ID as `agent_history_id`
  to `start_evaluation_batch` with the requested assigned
  `case_evaluator_pairs`. Check `skipped_pairs` and fetch the returned
  `batch_id` with `get_evaluation_results`.
- Check each result's `agent_history_id`, `status`, `score` and `reason` before
  reporting scores. Check the same batch again when results are pending or
  running. For a failure diagnosis, compare `answer__output` and
  `answer__reasoning_steps` with the evaluator's reason.

## Sandbox and files

- The working directory is `/workspace`. Use the returned paths and download
  again if that Sandbox has been replaced. A local draft file is separate from
  a saved Agent or KB resource.
- For current-message attachments, use `get_attachment_text` with
  `arguments.attachment_id` and a Sandbox destination, omitting `target`.
  Read the returned JSON file's `text`. For an upload, future reuse, or when
  conversion is insufficient, use `download_current_message_attachment` to
  fetch the original. Follow the knowledge base workflow above to retain and
  upload original bytes.
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
