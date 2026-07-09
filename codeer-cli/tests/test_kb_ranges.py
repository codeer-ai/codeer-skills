from __future__ import annotations

import argparse
import unittest

from codeer_cli.commands.kb import _parse_faq_range


class FaqRangeTests(unittest.TestCase):
    def test_parse_column_range(self) -> None:
        self.assertEqual(
            _parse_faq_range("47:2-48:9"),
            {
                "start_line": 47,
                "start_column": 2,
                "end_line": 48,
                "end_column": 9,
            },
        )

    def test_rejects_single_line_range(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_faq_range("47")

    def test_rejects_legacy_line_range(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_faq_range("47:48")

    def test_rejects_reversed_column_range(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            _parse_faq_range("48:1-47:1")


if __name__ == "__main__":
    unittest.main()
