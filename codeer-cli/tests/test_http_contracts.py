from __future__ import annotations

import copy
import io
import itertools
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from codeer_cli import agents
from codeer_cli._http_contracts import validate_http_input_contracts
from codeer_cli._validate import ToolValidationError, validate_unified_tools
from codeer_cli.cli import main
from codeer_cli.client import CodeerClient
from codeer_cli.commands import agent as agent_cmd
from codeer_cli.commands._util import NOISY_KEYS


PLACEHOLDER = "{{agent[Provide the requested value]}}"


def tool(body):
    return {
        "id": "submit",
        "type": "http_request",
        "http_request": {
            "method": "POST",
            "url_template": "https://example.com",
            "body": body,
        },
    }


def payload(tools):
    return {
        "name": "Agent",
        "system_prompt": "Help.",
        "use_search": False,
        "unified_tools": tools,
    }


class HttpContractValidationTests(unittest.TestCase):
    def test_all_type_format_root_combinations(self):
        for kind, fmt, root in itertools.product(
            ("string", "number", "integer", "boolean", "object", "array"),
            ("text", "json"),
            ("any", "object", "array"),
        ):
            contract = {"type": kind, "format": fmt, "json_type": root}
            body = {"template": PLACEHOLDER, "input_contracts": {"body": contract}}
            with self.subTest(contract=contract):
                valid = (fmt != "json" or kind == "string") and (
                    fmt == "json" or root == "any"
                )
                if valid:
                    before = copy.deepcopy(body)
                    self.assertEqual(
                        validate_http_input_contracts(body),
                        [
                            {"key": "body", **contract, "configured": True},
                        ],
                    )
                    self.assertEqual(body, before)
                else:
                    with self.assertRaises(ToolValidationError):
                        validate_unified_tools([tool(body)])

    def test_defaults_legacy_strings_and_static_values_remain_unchanged(self):
        for template in (
            None,
            {},
            [],
            False,
            5,
            "",
            "{not JSON",
            {"static": [None, 1, True]},
        ):
            with self.subTest(template=template):
                body = {"template": template}
                self.assertEqual(validate_http_input_contracts(body), [])
        for contracts in ({}, {"message": {}}, {"message": {"type": "string"}}):
            body = {
                "template": {"message": "prefix {{user.id}} " + PLACEHOLDER},
                "input_contracts": contracts,
            }
            self.assertEqual(
                validate_http_input_contracts(body)[0],
                {
                    "key": "message",
                    "type": "string",
                    "format": "text",
                    "json_type": "any",
                    "configured": bool(contracts),
                },
            )
        no_body = tool({})
        del no_body["http_request"]["body"]
        self.assertEqual(validate_unified_tools([no_body]), [no_body])

    def test_generated_keys_follow_backend_traversal_and_collision_order(self):
        template = {
            "order": {"Count": PLACEHOLDER},
            "order-count": PLACEHOLDER,
            "order_count_2": PLACEHOLDER,
            "items": [{"id": PLACEHOLDER}],
            "中文": PLACEHOLDER,
            "pair": PLACEHOLDER + "/" + PLACEHOLDER,
            "a.b": PLACEHOLDER,
            "a": {"b": PLACEHOLDER},
        }
        expected = [
            "order_count",
            "order_count_2",
            "order_count_2_2",
            "items_0_id",
            "body",
            "pair_1",
            "pair_2",
            "a_b",
            "a_b_2",
        ]
        body = {"template": template, "input_contracts": {key: {} for key in expected}}
        self.assertEqual(
            [row["key"] for row in validate_http_input_contracts(body)], expected
        )
        self.assertEqual(
            validate_http_input_contracts({"template": [PLACEHOLDER]})[0]["key"], "0"
        )
        # Instructions do not determine input keys; placeholder-looking object keys are static.
        self.assertEqual(
            validate_http_input_contracts({"template": {PLACEHOLDER: "static"}}), []
        )

    def test_typed_and_json_text_require_exact_whole_value(self):
        for contract in ({"type": "object"}, {"type": "integer"}, {"format": "json"}):
            for template, key in (
                (" " + PLACEHOLDER, "body"),
                (PLACEHOLDER + "\n", "body"),
                ("{{user.id}}" + PLACEHOLDER, "body"),
                (PLACEHOLDER + PLACEHOLDER, "body_1"),
            ):
                with self.subTest(contract=contract, template=template):
                    with self.assertRaisesRegex(ValueError, "entire template value"):
                        validate_http_input_contracts(
                            {"template": template, "input_contracts": {key: contract}}
                        )
        self.assertEqual(
            validate_http_input_contracts(
                {
                    "template": "{{ agent[ value ] }}",
                    "input_contracts": {"body": {"type": "array"}},
                }
            )[0]["type"],
            "array",
        )

    def test_invalid_configuration_shapes_and_fields(self):
        invalid_bodies = [
            None,
            [],
            "text",
            {"input_contracts": None},
            {"input_contracts": []},
            {"input_contracts": {1: {}}},
            {"inputContracts": {}},
            {"input_contracts": {}, "inputContracts": {}},
            {"template": "{{agent[ ]}}"},
            {"template": None, "input_contracts": {"body": {}}},
            {"template": PLACEHOLDER, "input_contracts": {"stale": {}}},
        ]
        invalid_contracts = [
            None,
            [],
            "string",
            {"type": "unsupported"},
            {"type": None},
            {"type": []},
            {"format": "JSON"},
            {"format": False},
            {"json_type": "number"},
            {"json_type": None},
            {"jsonType": "object"},
            {"allow_empty": True},
            {"properties": {}},
        ]
        invalid_bodies += [
            {"template": PLACEHOLDER, "input_contracts": {"body": c}}
            for c in invalid_contracts
        ]
        for body in invalid_bodies:
            for operation in ("create", "update"):
                with self.subTest(body=body, operation=operation):
                    # A bare object has no network methods; validation must fail first.
                    kwargs = payload([tool(body)])
                    with self.assertRaises(ToolValidationError):
                        if operation == "create":
                            agents.create(object(), workspace_id="ws", **kwargs)
                        else:
                            agents.update(object(), "agent-1", **kwargs)

    def test_outer_unknown_fields_follow_backend_but_contracts_are_strict(self):
        body = {"template": PLACEHOLDER, "future_body_field": {"owner": "keep"}}
        self.assertEqual(
            validate_unified_tools([tool(body)])[0]["http_request"]["body"], body
        )
        for method in ("GET", "HEAD"):
            value = tool({"template": PLACEHOLDER, "input_contracts": {"stale": {}}})
            value["http_request"]["method"] = method
            with self.assertRaises(ToolValidationError):
                validate_unified_tools([value])


class HttpContractRoundTripTests(unittest.TestCase):
    def setUp(self):
        keys = sorted(NOISY_KEYS | {"workspace"})
        self.tools = [
            tool(
                {
                    "template": {
                        "a.b": PLACEHOLDER,
                        "a": {"b": PLACEHOLDER},
                        **{key: PLACEHOLDER for key in keys},
                        "static": {key: [None, {"value": key}] for key in keys},
                    },
                    "input_contracts": {
                        "a_b": {"type": "integer"},
                        "a_b_2": {"type": "boolean"},
                        **{
                            key: {"format": "json", "json_type": "object"}
                            for key in keys
                        },
                    },
                }
            ),
            {
                "id": "other",
                "type": "request_form",
                "custom_form_schema": {
                    "title": "Details",
                    "fields": [
                        {
                            "id": "name",
                            "name": "name",
                            "label": "Name",
                            "type": "shortText",
                            "question": "Your name?",
                            "required": True,
                        }
                    ],
                    "properties": {
                        key: {"type": "string", "default": key} for key in keys
                    },
                },
            },
        ]
        self.record = {
            "id": "agent-1",
            **payload(self.tools),
            "owner": {"email": "metadata"},
            "profile": {"metadata": True},
            "workspace": {"id": "ws", "name": "Workspace", "owner": "metadata"},
        }
        self.calls = []

        def handler(request):
            self.calls.append(request)
            if request.method in ("POST", "PATCH"):
                self.record.update(json.loads(request.content))
                data = self.record
            elif request.url.path.endswith("/versions"):
                data = [{"id": "history-1", "version_number": 1, "status": "draft"}]
            elif request.url.path.endswith("/versions/history-1"):
                data = {
                    **self.record,
                    "id": "history-1",
                    "agent_id": "agent-1",
                    "version_number": 1,
                    "status": "draft",
                }
            else:
                data = self.record
            return httpx.Response(200, json={"data": data, "error_code": 0})

        self.client = CodeerClient(
            base_url="https://api.example.com", api_key="test-key"
        )
        self.client._client.close()
        self.client._client = httpx.Client(
            base_url=self.client.base_url, transport=httpx.MockTransport(handler)
        )
        self.addCleanup(self.client.close)

    def test_sdk_create_update_preserve_complete_tools_and_contracts(self):
        for operation in ("create", "update"):
            before = copy.deepcopy(self.tools)
            if operation == "create":
                result = agents.create(
                    self.client, workspace_id="ws", **payload(self.tools)
                )
            else:
                result = agents.update(self.client, "agent-1", **payload(self.tools))
            self.assertEqual(
                json.loads(self.calls[-1].content)["unified_tools"], before
            )
            self.assertEqual(result["unified_tools"], before)
            self.assertEqual(self.tools, before)

    def test_get_full_export_apply_and_exact_version_preserve_colliding_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            exported = Path(tmp) / "agent.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                self.assertEqual(
                    agent_cmd.run_get(
                        SimpleNamespace(
                            agent_id="agent-1", full=True, out=str(exported)
                        ),
                        self.client,
                    ),
                    0,
                )
            artifact = json.loads(exported.read_text())
            self.assertEqual(json.loads(stdout.getvalue()), artifact)
            self.assertNotIn("owner", artifact)
            self.assertNotIn("profile", artifact)
            self.assertEqual(artifact["workspace"], {"id": "ws", "name": "Workspace"})
            self.assertEqual(artifact["unified_tools"], self.tools)
            expected_keys = list(self.tools[0]["http_request"]["body"]["template"])
            self.assertEqual(
                list(artifact["unified_tools"][0]["http_request"]["body"]["template"]),
                expected_keys,
            )
            for agent_id in ("agent-1", None):
                artifact["workspace_id"] = "ws"
                exported.write_text(json.dumps(artifact))
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(
                        agent_cmd.run_apply(
                            SimpleNamespace(
                                payload=str(exported),
                                agent_id=agent_id,
                                dry_run=False,
                                note="contracts",
                                out=None,
                            ),
                            self.client,
                        ),
                        0,
                    )
                writes = [r for r in self.calls if r.method in ("POST", "PATCH")]
                self.assertEqual(
                    json.loads(writes[-1].content)["unified_tools"], self.tools
                )
                self.assertEqual(
                    list(
                        json.loads(writes[-1].content)["unified_tools"][0][
                            "http_request"
                        ]["body"]["template"]
                    ),
                    expected_keys,
                )
                self.assertEqual(
                    agents.get(self.client, "agent-1")["unified_tools"], self.tools
                )
            with (
                patch("codeer_cli.cli.CodeerClient.from_env", return_value=self.client),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(
                    main(
                        [
                            "agent",
                            "get",
                            "agent-1",
                            "--history",
                            "history-1",
                            "--full",
                            "--out",
                            str(exported),
                        ]
                    ),
                    0,
                )
            snapshot = json.loads(exported.read_text())
            self.assertEqual(snapshot["unified_tools"], self.tools)
            self.assertEqual(
                list(snapshot["unified_tools"][0]["http_request"]["body"]["template"]),
                expected_keys,
            )
            self.assertEqual(snapshot["id"], "history-1")
            self.assertEqual(
                self.calls[-1].url.path,
                "/api/v1/external/agents/agent-1/versions/history-1",
            )
            self.assertEqual([r.method for r in writes], ["PATCH", "POST"])

    def test_history_summary_identifies_snapshot_and_list_does_not_invent_sizes(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            agent_cmd.run_get(
                SimpleNamespace(
                    agent_id="agent-1", history="history-1", full=False, out=None
                ),
                self.client,
            )
        summary = json.loads(stdout.getvalue())
        self.assertEqual(
            {
                key: summary[key]
                for key in ("id", "agent_id", "version_number", "status")
            },
            {
                "id": "history-1",
                "agent_id": "agent-1",
                "version_number": 1,
                "status": "draft",
            },
        )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            agent_cmd.run_versions(
                SimpleNamespace(agent="agent-1", full=True, out=None), self.client
            )
        summary = json.loads(stdout.getvalue())[0]
        self.assertNotIn("tool_count", summary)
        self.assertNotIn("system_prompt_chars", summary)

    def test_version_diff_exposes_order_changes_that_rebind_contracts(self):
        before = tool(
            {
                "template": {
                    "a.b": "{{agent[First]}}",
                    "a": {"b": "{{agent[Second]}}"},
                },
                "input_contracts": {"a_b": {"type": "integer"}, "a_b_2": {}},
            }
        )
        after = copy.deepcopy(before)
        after["http_request"]["body"]["template"] = {
            "a": {"b": "{{agent[Second]}}"},
            "a.b": "{{agent[First]}}",
        }
        stdout = io.StringIO()
        with (
            patch.object(
                agent_cmd.agents_mod,
                "get_version",
                side_effect=[
                    {"version_number": 1, "unified_tools": [before]},
                    {"version_number": 2, "unified_tools": [after]},
                ],
            ),
            redirect_stdout(stdout),
        ):
            self.assertEqual(
                agent_cmd.run_diff(
                    SimpleNamespace(
                        agent="agent-1",
                        frm="h1",
                        to="h2",
                        from_version=None,
                        to_version=None,
                        field="tools",
                    ),
                    object(),
                ),
                0,
            )
        self.assertNotIn("tools unchanged", stdout.getvalue())
        self.assertRegex(stdout.getvalue(), r'(?m)^-\s+"a\.b":')
        self.assertRegex(stdout.getvalue(), r'(?m)^\+\s+"a\.b":')

    def test_cli_dry_run_is_read_only_and_summary_never_prints_http_values(self):
        value = tool(
            {
                "template": {
                    "payload": PLACEHOLDER,
                    "legacy": "prefix " + PLACEHOLDER,
                    "static": "template-secret",
                },
                "input_contracts": {
                    "payload": {"format": "json", "json_type": "array"}
                },
            }
        )
        value["http_request"].update(
            url_template="https://url-user:url-password@example.com/url-secret?key=query-secret",
            auth={"type": "bearer", "token": "auth-secret"},
            headers=[{"key": "Authorization", "value": "header-secret"}],
            query_params=[{"key": "token", "value": "param-secret"}],
        )
        value["invocation_instruction"] = "instruction-secret"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "agent.json"
            path.write_text(json.dumps(payload([value])))
            for extra in ([], ["--agent-id", "agent-1"]):
                stdout, stderr = io.StringIO(), io.StringIO()
                with (
                    patch(
                        "codeer_cli.cli.CodeerClient.from_env", return_value=self.client
                    ),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    self.assertEqual(
                        main(
                            [
                                "agent",
                                "apply",
                                "--payload",
                                str(path),
                                "--dry-run",
                                *extra,
                            ]
                        ),
                        0,
                    )
                result = json.loads(stdout.getvalue())
                self.assertEqual(
                    result["http_inputs"],
                    [
                        {
                            "tool_index": 0,
                            "body_inputs_used": True,
                            "inputs": [
                                {
                                    "key": "payload",
                                    "type": "string",
                                    "format": "json",
                                    "json_type": "array",
                                    "configured": True,
                                },
                                {
                                    "key": "legacy",
                                    "type": "string",
                                    "format": "text",
                                    "json_type": "any",
                                    "configured": False,
                                },
                            ],
                        }
                    ],
                )
                for secret in (
                    "url-user",
                    "url-password",
                    "url-secret",
                    "query-secret",
                    "auth-secret",
                    "header-secret",
                    "param-secret",
                    "instruction-secret",
                    "template-secret",
                    PLACEHOLDER,
                ):
                    self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())
            value["http_request"]["body"]["input_contracts"]["payload"]["type"] = (
                "unsupported-secret"
            )
            path.write_text(json.dumps(payload([value])))
            for dry_run in ([], ["--dry-run"]):
                stdout, stderr = io.StringIO(), io.StringIO()
                with (
                    patch(
                        "codeer_cli.cli.CodeerClient.from_env", return_value=self.client
                    ),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    self.assertEqual(
                        main(["agent", "apply", "--payload", str(path), *dry_run]), 2
                    )
                self.assertNotIn("unsupported-secret", stderr.getvalue())
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
