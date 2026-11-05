"""Small regression tests for the standalone docs checker (stdlib only)."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import check_docs, evidence_summary


class MarkdownChecks(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        (self.root / "docs").mkdir()
        (self.root / "Makefile").write_text("test:\n\t@echo ok\n", encoding="utf-8")
        (self.root / "README.md").write_text("# Проект\n", encoding="utf-8")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_valid_link_and_cyrillic_slug_and_explicit_anchor(self):
        self.write("docs/details.md", "# Одна сессия\n\n<a id=\"d7\"></a>\n")
        self.write("README.md", "[раздел](docs/details.md#одна-сессия) [id](docs/details.md#d7)\n")
        self.assertEqual(check_docs.validate(self.root), [])

    def test_missing_file_and_heading_are_reported(self):
        self.write("README.md", "[bad](docs/missing.md) [anchor](docs/details.md#nope)\n")
        self.write("docs/details.md", "# Good heading\n")
        errors = check_docs.validate(self.root)
        self.assertEqual(len(errors), 2)
        self.assertIn("missing target", errors[0])
        self.assertIn("unknown Markdown anchor", errors[1])

    def test_fenced_markdown_is_not_a_link_but_commands_are_checked(self):
        self.write("README.md", "```bash\nmake test\n[not a real link](bad.md)\n```\n")
        self.assertEqual(check_docs.validate(self.root), [])
        self.write("README.md", "```bash\nmake typo-test\n```\n")
        self.assertIn("unknown make target", check_docs.validate(self.root)[0])

    def test_local_line_range(self):
        self.write("src/example.py", "a = 1\nb = 2\n")
        self.write("README.md", "[good](src/example.py#L1-L2)\n")
        self.assertEqual(check_docs.validate(self.root), [])
        self.write("README.md", "[bad](src/example.py#L2-L3)\n")
        self.assertIn("outside", check_docs.validate(self.root)[0])

    def test_duplicate_heading_slugs(self):
        anchors = check_docs.anchors_in("# Раздел\n\n# Раздел\n\n```md\n# Fake\n```\n")
        self.assertIn("раздел", anchors)
        self.assertIn("раздел-1", anchors)
        self.assertNotIn("fake", anchors)

    def test_pinned_snapshot_line_range(self):
        self.write("src/example.py", "a = 1\nb = 2\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Docs",
                        "-c", "user.email=docs@example.invalid", "commit", "-qm", "test"], check=True)
        sha = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        url = f"https://github.com/avikhorev/multi-agent-memory/blob/{sha}/src/example.py"
        self.assertIsNone(check_docs.check_pinned(url + "#L1-L2", self.root, {}))
        self.assertIn("outside", check_docs.check_pinned(url + "#L3", self.root, {}))
        self.assertIn("missing pinned", check_docs.check_pinned(url.replace("example.py", "no.py"), self.root, {}))

    def test_frozen_data_check_detects_drift(self):
        mem = {key: (value, 780) for key, value in evidence_summary.EXPECTED_MEMORY.items()}
        live = {key: (value, 156, 42) for key, value in evidence_summary.EXPECTED_LIVE.items()}
        self.assertEqual(evidence_summary.verify(mem, live), [])
        live["ours"] = (123, 156, 42)
        self.assertIn("live ours", evidence_summary.verify(mem, live)[0])


class PublishedExamples(unittest.TestCase):
    """Keep the denominators and C6 walkthrough aligned with frozen unit files."""

    def test_live_all_vs_selected_denominators(self):
        import json

        root = Path(__file__).resolve().parents[1]
        files = sorted((root / "results/live/main/units").glob("ours__*.json"))
        self.assertEqual(len(files), 42)
        total, passed, selected, selected_passed = 0, 0, 0, 0
        for file in files:
            unit = json.loads(file.read_text(encoding="utf-8"))
            category = unit["scenario"].split("-")[0]
            for cp in unit["checkpoints"]:
                total += 1
                passed += bool(cp["passed"])
                if category in ("C0", "C6") or cp["factor"]:
                    selected += 1
                    selected_passed += bool(cp["passed"])
        self.assertEqual((passed, total), (124, 156))
        self.assertEqual((selected_passed, selected), (55, 66))

    def test_c6_source_writes_and_failure_labels(self):
        import json

        root = Path(__file__).resolve().parents[1] / "results/live/main"
        for system in ("ours", "full_history"):
            for repeat in (0, 1):
                name = f"{system}__C6-eval-0002__r{repeat}"
                unit = json.loads((root / "units" / f"{name}.json").read_text(encoding="utf-8"))
                trace = [json.loads(line) for line in
                         (root / "traces" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
                written = {row.get("entry_id") for row in trace if row.get("op") == "write"}
                checkpoints = {row["checkpoint"]: row for row in unit["checkpoints"]}
                if system == "ours":
                    self.assertNotIn("e-0002", written)
                    self.assertNotIn("e-0086", written)
                    for key in ("cp-1", "cp-3"):
                        self.assertEqual(checkpoints[key]["label"], "agent")
                        self.assertFalse(checkpoints[key]["context_passed"])
                        self.assertTrue(checkpoints[key]["reachable"])
                else:
                    self.assertIn("e-0002", written)
                    self.assertIn("e-0086", written)
                    for key in ("cp-1", "cp-3"):
                        self.assertEqual(checkpoints[key]["label"], "ok")


if __name__ == "__main__":
    unittest.main()
