"""Text evidence references shared by cleanup and receipt preservation."""
import json
from pathlib import Path
import re
from urllib.parse import unquote

TEXT = {".json", ".jsonl", ".md", ".toml", ".txt", ".yaml", ".yml", ".csv", ".log"}


def reference_text(content):
    text = content.decode("utf-8", errors="replace").replace("\\/", "/")
    try:
        text += "\n" + json.dumps(json.loads(content), ensure_ascii=False)
    except (ValueError, UnicodeError):
        pass
    return unquote(text)


def relative_references(content, path, root, candidates):
    """Find project/absolute/relative paths, directory citations and SHA-256."""
    text = reference_text(content)
    lower = text.lower()
    found = set()
    for name, row in candidates.items():
        if name in text or row["absolute"] in text or any(digest.lower() in lower for digest in row["hashes"]):
            found.add(name)
            continue
        parts = Path(name).parts
        if any(re.search(re.escape("/".join(parts[:length])) + r"/?(?=$|[\s\"'<>`)\]}])", text)
               for length in range(4, len(parts))):
            found.add(name)
    for value in re.findall(r"(?:\.\.?/|\.codeer/)[^\s\"'<>`)\]}]+", text):
        resolved = (path.parent / value).resolve()
        if resolved.is_relative_to(root):
            name = str(resolved.relative_to(root))
            found.update(key for key in candidates if key == name or key.startswith(name.rstrip("/") + "/"))
    return found
