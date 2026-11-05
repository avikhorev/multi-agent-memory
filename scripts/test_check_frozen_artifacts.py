"""Regression checks for the read-only checksum verifier."""

import tempfile
import unittest
from pathlib import Path

from scripts import check_frozen_artifacts as checks


class FrozenArtifactChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "data" / "a.json").write_text('{"a":1}\n')
        self.n, self.digest = checks.group_digest(self.root, "data/*.json")
        self.manifest = {"schema": 1, "groups": [
            {"glob": "data/*.json", "files": self.n, "sha256": self.digest},
        ]}

    def test_matching_snapshot_passes(self):
        self.assertEqual(checks.validate(self.root, self.manifest), [])

    def test_content_change_is_detected(self):
        (self.root / "data" / "a.json").write_text('{"a":2}\n')
        self.assertIn("SHA256", checks.validate(self.root, self.manifest)[0])

    def test_extra_file_is_detected(self):
        (self.root / "data" / "b.json").write_text("{}")
        self.assertIn("got 2 files", checks.validate(self.root, self.manifest)[0])

    def test_invalid_group_rejected(self):
        self.manifest["groups"].append({"glob": "../escape", "files": 0, "sha256": ""})
        self.assertIn("invalid glob", checks.validate(self.root, self.manifest)[0])


if __name__ == "__main__":
    unittest.main()
