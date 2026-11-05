"""Stdlib regression checks for the static visual replay's evidence."""

import unittest

from scripts.build_visual_demo import CASES, DEST, ROOT, build_bundle, render_js


class VisualDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build_bundle(ROOT)
        cls.cases = {case["id"]: case for case in cls.bundle["cases"]}

    def test_three_pinned_cases_and_two_systems(self):
        self.assertEqual(set(self.cases), {"c1-update", "c6-document", "c6-status"})
        for case in self.cases.values():
            self.assertEqual(set(case["systems"]), {"ours", "full_history"})
            self.assertIn(case["checkpoint"], {c["checkpoint"] for c in CASES})

    def test_c1_uses_recorded_update_and_real_resolution(self):
        c1 = self.cases["c1-update"]
        ours, baseline = (c1["systems"][key] for key in ("ours", "full_history"))
        for key in ("e-0017", "x-0001"):
            self.assertTrue(ours["sources"][key]["written"])
            self.assertTrue(baseline["sources"][key]["written"])
        self.assertEqual(ours["sources"]["x-0001"]["facts"][0]["value"], "153000")
        self.assertIn({"winner": "153000", "loser": "727000", "rule": "later_event"}, ours["resolution"])
        self.assertEqual((ours["checkpoint"]["passed"], baseline["checkpoint"]["passed"]), (True, False))
        self.assertEqual((ours["context"]["tokens"], baseline["context"]["tokens"]), (276, 1709))
        self.assertEqual(baseline["checkpoint"]["label"], "memory")

    def test_c6_source_missed_by_ours_not_full_history(self):
        for case_id, entry_id, expected in (("c6-document", "e-0002", "2026-05-07"),
                                            ("c6-status", "e-0086", "343000")):
            case = self.cases[case_id]
            self.assertEqual(case["question"]["expected"], expected)
            ours, baseline = (case["systems"][key] for key in ("ours", "full_history"))
            self.assertFalse(ours["sources"][entry_id]["written"])
            self.assertFalse(ours["sources"][entry_id]["context_ids"])
            self.assertTrue(baseline["sources"][entry_id]["written"])
            self.assertTrue(baseline["sources"][entry_id]["context_ids"])
            self.assertEqual((ours["checkpoint"]["label"], baseline["checkpoint"]["label"]), ("agent", "ok"))
            self.assertEqual((ours["checkpoint"]["passed"], baseline["checkpoint"]["passed"]), (False, True))

    def test_worker_actions_are_real_tools(self):
        document = self.cases["c6-document"]
        ours = document["systems"]["ours"]["worker_actions"]
        baseline = document["systems"]["full_history"]["worker_actions"]
        self.assertEqual(ours[0]["tool"], "update_record")
        self.assertEqual(baseline[0]["tool"], "read_document")
        self.assertEqual(baseline[0]["args"]["doc_id"], "D-011")
        status = self.cases["c6-status"]
        self.assertEqual(status["systems"]["full_history"]["worker_actions"][0]["tool"], "read_status")

    def test_static_snapshot_matches_frozen_raw_data(self):
        self.assertEqual(DEST.read_text(encoding="utf-8"), render_js(self.bundle))

    def test_demo_is_offline_and_has_accessible_controls(self):
        html = (ROOT / "docs/demo/index.html").read_text(encoding="utf-8")
        js = (ROOT / "docs/demo/demo.js").read_text(encoding="utf-8")
        for name in ("style.css", "data.js", "demo.js"):
            self.assertIn(name, html)
        for element_id in ('id="case-select"', 'id="play"', 'id="step-body"'):
            self.assertIn(element_id, html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('aria-pressed', html)
        self.assertNotIn("fetch(", js)
        self.assertNotIn("innerHTML", js)  # raw trace text must never become HTML
        self.assertIn("textContent", js)


if __name__ == "__main__":
    unittest.main()
