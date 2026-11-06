"""Standalone eval polling honors terminal API states and preserves failures."""

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

from codeer_cli.commands.eval_cmd import run_run


class EvalRunTerminalTests(unittest.TestCase):
    def run_eval(self, snapshots, *, cases="audio", timeout=30):
        client = Mock()
        client.resolve_scope.return_value = ("workspace", None)
        client.get.side_effect = lambda path: {
            "id": path.rsplit("/", 1)[-1],
            "input": "Input",
            "name": "Judge",
        }
        polls = []

        def post(path, **kwargs):
            if path == "/external/eval/runs":
                return {"ok": True}
            self.assertEqual(path, "/external/eval/results:batch")
            polls.append(kwargs["json"])
            return snapshots[min(len(polls) - 1, len(snapshots) - 1)]

        client.post.side_effect = post
        args = SimpleNamespace(
            project=None,
            latest=False,
            history="version",
            agent="agent",
            cases=cases,
            evaluator="judge",
            evaluators=None,
            poll_timeout=timeout,
            full=False,
            out=None,
        )
        clock = [0]

        def sleep(seconds):
            clock[0] += seconds

        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            patch(
                "codeer_cli.commands.eval_cmd.time.time", side_effect=lambda: clock[0]
            ),
            patch(
                "codeer_cli.commands.eval_cmd.time.sleep", side_effect=sleep
            ) as sleeper,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = run_run(args, client)
        return code, json.loads(stdout.getvalue()), polls, sleeper.call_count

    def test_failed_without_score_finishes_immediately_and_preserves_error(self):
        for status in ("failed", "FAILED"):
            with self.subTest(status=status):
                code, output, polls, sleeps = self.run_eval(
                    [
                        [
                            {
                                "case_id": "audio",
                                "status": status,
                                "score": None,
                                "reason": "Judge model does not support audio input",
                            }
                        ]
                    ]
                )
                self.assertEqual(code, 1)
                self.assertFalse(output["all_perfect"])
                self.assertEqual(output["scored_pair_count"], 0)
                self.assertEqual(output["results"][0]["status"], status)
                self.assertIsNone(output["results"][0]["score"])
                self.assertIn(
                    "does not support audio", output["results"][0]["reason_preview"]
                )
                self.assertEqual((len(polls), sleeps), (1, 0))

    def test_failed_pair_does_not_stop_other_pending_pairs(self):
        failed = {"case_id": "audio", "status": "failed", "score": None}
        code, output, polls, sleeps = self.run_eval(
            [
                [failed, {"case_id": "image", "status": "running", "score": None}],
                [failed, {"case_id": "image", "status": "finished", "score": 1}],
            ],
            cases="audio,image",
        )
        self.assertEqual(code, 1)
        self.assertEqual(output["result_count"], 2)
        self.assertEqual(output["scored_pair_count"], 1)
        self.assertEqual((len(polls), sleeps), (2, 1))

    def test_finished_without_score_stops_but_does_not_pass(self):
        code, output, polls, sleeps = self.run_eval(
            [[{"case_id": "audio", "status": "finished", "score": None}]]
        )
        self.assertEqual(code, 1)
        self.assertFalse(output["all_perfect"])
        self.assertEqual((len(polls), sleeps), (1, 0))

    def test_failed_with_stale_perfect_score_cannot_pass(self):
        code, output, polls, sleeps = self.run_eval(
            [[{"case_id": "audio", "status": "failed", "score": 1}]]
        )
        self.assertEqual(code, 1)
        self.assertFalse(output["all_perfect"])
        self.assertEqual(output["non_perfect_count"], 1)
        self.assertEqual((len(polls), sleeps), (1, 0))

    def test_running_with_stale_score_keeps_polling(self):
        code, output, polls, sleeps = self.run_eval(
            [
                [{"case_id": "audio", "status": "running", "score": 1}],
                [{"case_id": "audio", "status": "finished", "score": 1}],
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(output["all_perfect"])
        self.assertEqual((len(polls), sleeps), (2, 1))

    def test_pending_missing_and_unknown_results_reach_timeout(self):
        for rows in (
            [],
            [{"case_id": "audio", "status": "pending", "score": None}],
            [{"case_id": "audio", "status": "unknown", "score": 1}],
        ):
            with self.subTest(rows=rows):
                code, output, polls, sleeps = self.run_eval([rows], timeout=6)
                self.assertEqual(code, 1)
                self.assertFalse(output["all_perfect"])
                self.assertGreater(sleeps, 0)

    def test_legacy_scored_response_without_status_and_zero_score(self):
        for score, expected in ((1, 0), (0, 1)):
            with self.subTest(score=score):
                code, _, polls, sleeps = self.run_eval(
                    [[{"case_id": "audio", "score": score}]]
                )
                self.assertEqual(code, expected)
                self.assertEqual((len(polls), sleeps), (1, 0))

    def test_unrequested_result_cannot_finish_requested_pair(self):
        code, _, polls, sleeps = self.run_eval(
            [[{"case_id": "other", "status": "finished", "score": 1}]], timeout=6
        )
        self.assertEqual(code, 1)
        self.assertGreater(sleeps, 0)


if __name__ == "__main__":
    unittest.main()
