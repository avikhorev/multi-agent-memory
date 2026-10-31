"""Spec section 9 and 12.7: offline token counter against measured samples.

mam.tokens is written later by someone else; these tests must fail until it exists.
"""
import json
from collections import defaultdict
from pathlib import Path

import pytest

pytestmark = pytest.mark.memory

SAMPLES = Path(__file__).resolve().parents[2] / "results" / "pilot" / "calibration_samples.jsonl"


def counter():
    from mam.tokens import count
    return count


def samples():
    return [json.loads(line) for line in SAMPLES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_every_long_sample_within_15_percent():
    count = counter()
    bad = []
    for r in samples():
        err = abs(count(r["text"]) - r["delta_tokens"]) / r["delta_tokens"]
        if err > 0.15:
            bad.append((r["kind"], r["chars"], round(err, 3)))
    assert bad == []


def test_mean_error_per_type_within_5_percent():
    count = counter()
    errors = defaultdict(list)
    for r in samples():
        errors[r["kind"]].append(abs(count(r["text"]) - r["delta_tokens"]) / r["delta_tokens"])
    assert set(errors) == {"facts", "prose", "json", "mixed"}
    for kind, errs in errors.items():
        assert sum(errs) / len(errs) <= 0.05, kind


def test_count_is_an_int_deterministic_and_zero_for_empty():
    count = counter()
    text = samples()[0]["text"]
    assert isinstance(count(text), int) and count(text) == count(text)
    assert count("") == 0


def test_count_grows_with_text():
    count = counter()
    text = samples()[2]["text"]
    assert count(text) > count(text[: len(text) // 2]) > 0
    assert count(text + text) > count(text)
