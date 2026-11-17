# Agent drafts, attachments, and knowledge bases

## Read source material

- For an attachment on the current message, find `get_attachment_text` and call it with `arguments.attachment_id` and a Sandbox `destination`. Omit `target` for that attachment. Read the returned JSON path and use its `text`. If conversion cannot supply the needed material, try `download_current_message_attachment` and read the original. A page snapshot gives screen context. Use the attachment's actual content for an SOP-based draft.
- To upload or reuse a current-message attachment, download its original with `download_current_message_attachment` and freeze the downloaded path before replying. Keep the returned `file_ref_id` even if business rules still need clarification. Use the original FileRef for upload.
- Read the relevant saved Agent, tool configuration, or source content before editing. Preserve user decisions and fields outside the request.

## Create or edit a draft

Discover `external_create_agent` to create an unpublished draft. Supply `arguments.name` and either `arguments.system_prompt` or the FileRef at `arguments.file_inputs.system_prompt`. `tool_types` provides the configuration schema for a specific Agent tool.

To edit an existing Agent, resolve its ID with `external_list_agents`. Call `external_get_agent` with `arguments.agent_id` and a `destination` such as `agents/draft.json`. Read its top-level `system_prompt` and `updated_at`. Call `external_update_agent` with `agent_id`, `expected_updated_at` set to that saved `updated_at`, and only the fields you intend to change. When sending `unified_tools`, include the complete desired list so other tools are preserved. Keep the returned `draft_version_id` for evaluation. Read back the draft to verify the saved change.

For example, to add a delivery cutoff to a fulfillment Agent's prompt, retrieve the saved draft, add the verified cutoff to its existing text, then send the complete revised prompt with the saved `updated_at`. Create or publish a version only to the extent explicitly requested.

## Attach knowledge

1. Locate the target workspace's FOLDER node with `external_kb_list_nodes`, following its folder hierarchy if needed.
2. Discover `external_kb_upload_files` and supply the folder's ID as `arguments.parent_id` and the frozen originals as `arguments.file_ref_ids`.
3. Use `external_kb_file_status` to check indexing for the returned FILE nodes. Use the FILE node IDs in `knowledge_base` tool configuration under `knowledge_node_ids`. Discover `tool_types` for the exact configuration schema.
4. When the user asks to bind the sources to the Agent, update the draft via `external_update_agent`, preserving its other tools. Read back the Agent and report which source bindings and indexing states were verified.
