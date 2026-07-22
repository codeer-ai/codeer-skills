from __future__ import annotations

import contextlib
import io
import json
import unittest
from types import SimpleNamespace

from codeer_cli import models
from codeer_cli.commands import model as model_cmd


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get(self, path: str, **kwargs):
        self.calls.append((path, kwargs))
        return [{"display_name": "Qwen", "model_id": "provider/qwen"}]


class ModelDiscoveryTests(unittest.TestCase):
    def test_lists_text_models_with_api_filter(self) -> None:
        client = FakeClient()

        result = models.list_available(client, model_type="text")  # type: ignore[arg-type]

        self.assertEqual(result[0]["model_id"], "provider/qwen")
        self.assertEqual(client.calls, [("/llm/models", {"params": {"model_type": "text"}})])

    def test_lists_all_models_without_query_params(self) -> None:
        client = FakeClient()

        models.list_available(client)  # type: ignore[arg-type]

        self.assertEqual(client.calls, [("/llm/models", {"params": None})])

    def test_command_full_output_includes_model_metadata(self) -> None:
        class FullFakeClient(FakeClient):
            def get(self, path: str, **kwargs):
                self.calls.append((path, kwargs))
                return [{
                    "display_name": "Qwen",
                    "model_id": "provider/qwen",
                    "provider": "Provider",
                    "model_type": "text",
                    "input_modalities": ["text"],
                    "input_credits_per_million_tokens": 1,
                    "output_credits_per_million_tokens": 2,
                    "created_at": "2026-07-22T00:00:00Z",
                }]

        client = FullFakeClient()
        args = SimpleNamespace(type="text", full=True, out=None)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            status = model_cmd.run_list(args, client)  # type: ignore[arg-type]

        result = json.loads(stdout.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(result[0]["model_id"], "provider/qwen")
        self.assertEqual(result[0]["input_modalities"], ["text"])
        self.assertEqual(client.calls, [("/llm/models", {"params": {"model_type": "text"}})])


if __name__ == "__main__":
    unittest.main()
