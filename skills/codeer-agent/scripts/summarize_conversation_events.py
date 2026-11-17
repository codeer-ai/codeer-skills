"""Summarize the events and message bodies in a scoped Codeer JSONL export."""

import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(source):
    seen = set()
    event_histories = set()
    message_histories = set()
    event_kinds = Counter()
    message_counts = Counter()
    character_counts = Counter()
    roles = {"user-prompt": "user", "text": "assistant"}

    for line in source:
        row = json.loads(line)
        workspace = row["workspace_id"]
        event_key = (workspace, row["part_id"])
        if event_key in seen:
            continue
        seen.add(event_key)
        history_key = (workspace, row["history_id"])
        event_histories.add(history_key)
        kind = row["part_kind"]
        event_kinds[kind] += 1
        role = roles.get(kind)
        content = row["content"]
        text = content.get("content") if isinstance(content, dict) else None
        if role and isinstance(text, str) and text != "":
            message_histories.add(history_key)
            message_counts[role] += 1
            character_counts[role] += len(text)

    message_counts["all"] = sum(message_counts.values())
    character_counts["all"] = sum(character_counts.values())
    return {
        "unique_events": len(seen),
        "event_kinds": dict(event_kinds),
        "histories_with_events": len(event_histories),
        "histories_with_messages": len(message_histories),
        "messages": {
            population: {
                "count": message_counts[population],
                "characters": character_counts[population],
                "mean_characters": (
                    character_counts[population] / message_counts[population]
                    if message_counts[population]
                    else None
                ),
            }
            for population in ("all", "user", "assistant")
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_path", type=Path)
    args = parser.parse_args()
    with args.export_path.open(encoding="utf-8") as source:
        print(json.dumps(summarize(source), ensure_ascii=False))


if __name__ == "__main__":
    main()
