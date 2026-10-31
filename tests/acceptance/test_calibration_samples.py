"""The measured samples that the token counter is checked against (spec section 9) are usable."""
import json
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "results" / "pilot" / "calibration_samples.jsonl"


def samples():
    return [json.loads(line) for line in SAMPLES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_samples_file_is_usable():
    rows = samples()
    assert len(rows) == 64 and all(r["delta_tokens"] > 0 and len(r["text"]) >= 600 for r in rows)


def test_chars_div_4_would_not_pass_so_the_test_is_meaningful():
    # the rejected estimate of decision D4 misses the 15 percent tolerance on facts and json
    bad = [r for r in samples() if r["kind"] in ("facts", "json")
           and abs(len(r["text"]) / 4 - r["delta_tokens"]) / r["delta_tokens"] > 0.15]
    assert len(bad) >= 16
