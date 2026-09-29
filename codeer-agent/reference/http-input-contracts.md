# HTTP input contracts

Read this when configuring HTTP tool body input types or JSON text. The target
backend must have HTTP input-contract support deployed (codeer-copilot #1495).
An updated CLI or successful local dry-run does not prove deployment. Use the
configured environment and normal skill mutation/diff/publish guardrails.

## Choose the wire value

Configure `unified_tools[].http_request.body.input_contracts` by generated input
key. Use API snake_case `input_contracts` and `json_type`; `inputContracts` and
`jsonType` are frontend names and are rejected by the CLI.

| Intended HTTP body field | Contract |
| --- | --- |
| Ordinary text, including empty or malformed JSON | `{}` (default string/text/any) |
| Native numeric / integer / boolean value | `{"type":"number"}` / `{"type":"integer"}` / `{"type":"boolean"}` |
| Native object / array | `{"type":"object"}` / `{"type":"array"}` |
| String containing any JSON value | `{"type":"string","format":"json","json_type":"any"}` |
| String containing a JSON object / array | `{"format":"json","json_type":"object"}` / `{"format":"json","json_type":"array"}` |

`type` defaults to `string`; `format` defaults to `text`; `json_type` defaults to
`any`. Only string supports `format: json`; only JSON format permits a
`json_type` other than `any`. Each contract accepts only these three properties,
not nested JSON Schema, empty-value policies, or guessed defaults.

For example, this body config sends `payload` as a native object and `changes`
as a string containing an array:

```json
{
  "template": {
    "payload": "{{agent[Order details]}}",
    "changes": "{{agent[Serialized change list]}}"
  },
  "input_contracts": {
    "payload": {"type": "object"},
    "changes": {"format": "json", "json_type": "array"}
  }
}
```

The backend converts supported representations before validation: serialized
JSON may become a native object/array, while a native JSON value supplied to a
string input is serialized once. Already valid JSON text stays byte-for-byte
unchanged as a string. Empty string also stays unchanged for JSON-text inputs;
non-empty strings (including whitespace-only text) must parse and satisfy the
requested root type. No automatic `{}`/`[]` substitution occurs. Every placeholder
is required; top-level input null is invalid. Nested JSON null is allowed in
native objects/arrays; numbers must be finite. CLI validation manages configuration
only; it does not duplicate runtime conversion or invoke the configured API.

## Bind contracts to generated keys

Walk template object values in insertion order and array items by index. Paths
join object names with dots and array indexes with brackets. Replace each run
of non-ASCII-alphanumeric characters with `_`, trim edge underscores, then
lowercase; fall back to `body` for an empty normalized name or a root string.
For example `order.count` → `order_count`, `items[0].id` → `items_0_id`.
Multiple placeholders in one string append `_1`, `_2`, etc. Global collisions
append `_2`, `_3`, etc. Instruction text does not determine the key.

Preserve object insertion order: sorting or moving colliding paths can change
which field receives each contract. Review the dry-run's generated keys after
path/order changes. Unknown or stale contract keys fail validation. Omitted
contract entries use ordinary strings; send the full desired map, not a delta.
Non-string and JSON-text inputs require one placeholder occupying the entire
value, with no surrounding literal/context text. Ordinary strings can be
embedded or repeated. Static JSON values remain untouched. Omit `body` for no
body, or use `template: null`; `body: null` and `input_contracts: null` are invalid.
GET/HEAD still validate configuration, but their runtime ignores body inputs.

## Read, preserve, apply, verify, then publish separately

1. Run `codeer check` before server work, then export the current editable Agent:
   `codeer agent get <agent-id> --out .codeer/current/agent.json`.
   This preserves nested payload/schema/template/contract keys, including
   `owner`, `profile`, and `workspace`. Full exports retain HTTP credentials;
   inspect them locally without pasting secrets into chat or a review.
2. Build `.codeer/current/local_draft_agent.json` from current **writable**
   settings. External PATCH is not a nested partial update: supply `name`,
   `system_prompt`, `use_search`, the complete `unified_tools` list, and all
   desired contracts. Preserve unrelated tools, auth, headers, query parameters,
   template values and `draft_policy`; preserve description, suggested questions,
   model settings, human handoff, attachments and other writable settings.
   Never submit only a new `type`, the contract fragment above, or one changed tool.
3. GET is evidence, not a universal ready-to-apply payload. Check current version
   metadata with `codeer agent versions --agent <agent-id>`, then read the needed
   snapshot with `codeer agent get <agent-id> --history <history-id> --out
   .codeer/current/agent-version.json`. Reconstruct writable `attachment_ids`
   from the snapshot's `attachments[].id` and any other absent writable fields
   from current evidence. The CLI's supported top-level fields are name, prompt,
   tools, search, description, model/model settings, questions, primary object IDs,
   attachment IDs and handoff. If other existing writable settings need to be
   sent to preserve behavior (for example a non-default `response_mode`, which
   apply does not forward), stop before apply and report the unsupported setting.
4. Run `codeer agent apply --agent-id <agent-id> --payload
   .codeer/current/local_draft_agent.json --dry-run`. `http_inputs` shows each
   tool index and generated input key with effective type/format/root restriction
   and whether it was configured. It excludes HTTP values and instructions.
   Review the complete local payload diff as well; the summary is not a full diff.
   After approval, rerun without `--dry-run`. Create uses the same payload without
   `--agent-id`; apply saves a DRAFT and returns its `history_id`.
5. Refresh current GET, then read that exact `history_id` using `agent get
   --history`. Compare complete tools, templates, contract bindings and unrelated
   settings against the intended payload. Server output may include explicit
   defaults for omitted contract properties. The version list is metadata only;
   `versions --out` does not fetch snapshots. If another edit raced with apply,
   do not assume the latest ID returned by the CLI belongs to this change;
   resolve and verify the intended snapshot before proceeding.
6. Validate the draft according to the owning lifecycle module. Local validation
   does not establish runtime execution or external API business-rule success.
   Publish only the verified version after separate approval, with
   `codeer agent publish --agent <agent-id> --history <history-id> --dry-run`
   followed by the separately authorized publish operation.
