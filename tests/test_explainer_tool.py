# Copyright 2026 Barkha Gvalani
# SPDX-License-Identifier: Apache-2.0
"""Tests for skills/explain/scripts/explainer_tool.py.

Run with: python3 -m unittest discover -s tests
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "explain" / "scripts" / "explainer_tool.py"

spec = importlib.util.spec_from_file_location("explainer_tool", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class NormalizeTests(unittest.TestCase):
    def test_line_endings_and_trailing_space_do_not_matter(self):
        self.assertEqual(tool.normalize("a  \r\nb\r\n\r\n"), "a\nb\n")
        self.assertEqual(tool.sha256(tool.normalize("a\nb")), tool.sha256(tool.normalize("a \nb\n\n")))

    def test_known_vector(self):
        # Test vector: sha256 of "hello\n".
        self.assertEqual(
            tool.output_hash("hello"),
            "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
        )


class ClassifyAndStampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "README.md").write_text("# Root\n", encoding="utf-8")
        self.explainer = self.root / "EXPLAINER.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_is_free(self):
        self.assertEqual(tool.classify(self.explainer)["state"], "free")

    def test_file_without_footer_is_human(self):
        self.explainer.write_text("# Written by a person\n", encoding="utf-8")
        self.assertEqual(tool.classify(self.explainer)["state"], "human")

    def test_footer_not_on_last_line_is_unreadable(self):
        self.explainer.write_text(
            "# X\n<!-- readme-explainer v1 broken -->\nmore text\n", encoding="utf-8"
        )
        self.assertEqual(tool.classify(self.explainer)["state"], "unreadable")

    def test_stamp_pending_then_owned(self):
        self.explainer.write_text("# What this does\n\nIt sends emails.\n", encoding="utf-8")
        result = tool.stamp(self.explainer, "README.md", "PENDING")
        self.assertEqual(result["state"], "pending")
        fp = tool.fingerprint(self.root, ["README.md"], [], [])
        result = tool.stamp(self.explainer, "README.md", fp)
        self.assertEqual(result["state"], "owned")
        self.assertEqual(result["fingerprint"], fp)

    def test_hand_edit_is_detected(self):
        self.explainer.write_text("# What this does\n", encoding="utf-8")
        tool.stamp(self.explainer, "README.md", "PENDING")
        text = self.explainer.read_text(encoding="utf-8")
        self.explainer.write_text("Edited by hand.\n" + text, encoding="utf-8")
        self.assertEqual(tool.classify(self.explainer)["state"], "edited")

    def test_restamp_replaces_footer(self):
        self.explainer.write_text("# A\n", encoding="utf-8")
        tool.stamp(self.explainer, "README.md", "PENDING")
        tool.stamp(self.explainer, "README.md", "PENDING")
        text = self.explainer.read_text(encoding="utf-8")
        self.assertEqual(text.count("<!-- readme-explainer"), 1)


class FingerprintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a").mkdir()
        (self.root / "README.md").write_text("# Root\n", encoding="utf-8")
        (self.root / "a" / "README.md").write_text("# A\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_order_does_not_matter(self):
        one = tool.fingerprint(self.root, ["README.md", "a/README.md"], [], [])
        two = tool.fingerprint(self.root, ["a/README.md", "README.md"], [], [])
        self.assertEqual(one, two)

    def test_changed_input_changes_fingerprint(self):
        before = tool.fingerprint(self.root, ["a/README.md"], [], [])
        (self.root / "a" / "README.md").write_text("# A changed\n", encoding="utf-8")
        after = tool.fingerprint(self.root, ["a/README.md"], [], [])
        self.assertNotEqual(before, after)

    def test_formatting_only_change_keeps_fingerprint(self):
        before = tool.fingerprint(self.root, ["a/README.md"], [], [])
        (self.root / "a" / "README.md").write_text("# A   \r\n\r\n", encoding="utf-8")
        after = tool.fingerprint(self.root, ["a/README.md"], [], [])
        self.assertEqual(before, after)

    def test_child_footer_does_not_change_parent_fingerprint(self):
        child = self.root / "a" / "EXPLAINER.md"
        child.write_text("# Child\n", encoding="utf-8")
        tool.stamp(child, "a/README.md", "PENDING")
        before = tool.fingerprint(self.root, [], ["a/EXPLAINER.md"], [])
        fp = tool.fingerprint(self.root, ["a/README.md"], [], [])
        tool.stamp(child, "a/README.md", fp)
        after = tool.fingerprint(self.root, [], ["a/EXPLAINER.md"], [])
        self.assertEqual(before, after)

    def test_missing_input_raises(self):
        with self.assertRaises(FileNotFoundError):
            tool.fingerprint(self.root, ["missing/README.md"], [], [])


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "README.md").write_text("# Root\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        path = self.root / "EXPLAINER.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_good_file_passes(self):
        path = self.write(
            "See [the contract](README.md) and [web](https://example.com).\n\n"
            "```mermaid\nflowchart LR\n  A --> B\n```\n"
        )
        self.assertTrue(tool.check(path)["ok"])

    def test_broken_link_fails(self):
        path = self.write("See [missing](nope/README.md).\n")
        result = tool.check(path)
        self.assertFalse(result["ok"])
        self.assertIn("broken link", result["problems"][0]["problem"])

    def test_disallowed_mermaid_type_fails(self):
        path = self.write("```mermaid\npie title Costs\n  \"a\" : 1\n```\n")
        self.assertFalse(tool.check(path)["ok"])


class CliTests(unittest.TestCase):
    def test_version_runs(self):
        out = subprocess.run(
            [sys.executable, str(SCRIPT), "version"], capture_output=True, text=True, check=True
        )
        self.assertIn("v1", out.stdout)

    def test_classify_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run(
                [sys.executable, str(SCRIPT), "classify", str(Path(tmp) / "EXPLAINER.md")],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(out.stdout)["state"], "free")


if __name__ == "__main__":
    unittest.main()
