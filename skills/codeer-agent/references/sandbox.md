# Sandbox and RuntimeClient

The Sandbox provides a shell, Python 3, and a working filesystem rooted at `/workspace`. Relative paths resolve there. Files can carry over between turns of the same Copilot conversation while the Sandbox exists. Download necessary inputs again when a Sandbox has been replaced. Codeer workspace selection still comes from the current request and tool arguments. A Sandbox file is separate from a saved Agent or knowledge base record.

- Use `write_file` to create a multiline Python script and `run_command` with `python3 script.py ...` to run it. Use the exact output path returned by file tools. Keep bulk inputs and intermediate files in the Sandbox. Preview bounded ranges with `read_file` and print a small summary for the answer.
- `run_command` returns `status`, and when the command finishes, `exit_code`, `stdout_path` and `stderr_path`. A finished command can fail. Check the exit code, read needed output from the returned paths, and correct errors before drawing conclusions.
- Use `start_command` for longer work. Keep its `command_id` and stream paths. Check it with `check_command` until it reaches a terminal state and verify the exit code. Use `stop_command` when cancellation is needed. Inspect the original log paths after completion.
- Use `skill_file` with `arguments.path` and `destination` when you need a copy of a bundled file in the Sandbox. Use `read_skill_file` to read a bundled reference into context.
- Validate output files before handing them off. Use `freeze_sandbox_file(path=...)` to make a FileRef, then `deliver_file_ref(file_ref_id=...)` for each requested download. For an input you intend to upload to Codeer, freeze the original and use the FileRef with the platform write tool.

## Discover and call Codeer operations

ToolSearch (`search_tools`) exposes the selected tool's input JSON Schema and description to the model. It does not provide a separate machine-readable return schema for `export_conversation_events`. Its description and `references/conversations.md` describe the return values and exported rows. Call the discovered tool for ordinary Codeer requests. A file tool with `destination` writes the response to the Sandbox and returns metadata.

Use `RuntimeClient` when a script itself needs to fetch Codeer data. The provider configures the client for the current turn. Instantiate it without credentials or a base URL. Call `read_json("list_operations", {})` for available read operations and `read_json("operation_schema", {"name": name})` for one operation's argument schema. The latter returns `name`, `mode` and `schema`. Use `read_json(name, arguments)` for JSON operations and `query(name, arguments, destination=...)` for file operations. The client accepts an optional `target={"workspace_id": "..."}` for explicit workspace selection. Pass the inner `arguments` object, without nesting it again. A successful `query` returns a `RuntimeFile` with `path` (a `Path`), `size_bytes` (an integer), and `coverage` (a list for conversation exports, otherwise nullable). A failed or incomplete download raises an error. Process the returned file only after the call succeeds.

## Example — inventory event kinds for one conversation

Resolve the intended History ID first. Save this as `event_inventory.py` with `write_file`, then call `run_command` with `python3 event_inventory.py <history-id>` using the actual ID. Read the returned stdout path for the inventory.

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
