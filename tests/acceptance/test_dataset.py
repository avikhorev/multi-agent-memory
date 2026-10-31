"""Spec sections 10 and 12.9: sizes and layout of the splits; byte-for-byte reproducible generation."""
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from mam.generate import generate_split
from mam.scenario import dumps, load
from mam.validate import validate

ROOT = Path(__file__).resolve().parents[2]
DEV_COUNTS = {"C0": 20, "C1": 20, "C2": 20, "C3": 20, "C4": 20, "C5": 20, "C6": 21}
EVAL_COUNTS = {f"C{i}": 30 for i in range(7)}


def run_cli(split, out):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    subprocess.run([sys.executable, "-m", "mam.generate", "--split", split, "--out", str(out)],
                   check=True, env=env, capture_output=True)


def read_dir(path):
    return {p.name: p.read_bytes() for p in sorted(Path(path).glob("*.json")) if p.name != "manifest.json"}


@pytest.fixture(scope="module")
def dev():
    return generate_split("dev")


@pytest.fixture(scope="module")
def evals():
    return generate_split("eval")


def test_dev_layout(dev):
    assert Counter(s.category for s in dev) == DEV_COUNTS
    assert len(dev) == 141
    assert all(s.split == "dev" for s in dev)
    ids = [s.id for s in dev]
    assert len(set(ids)) == 141 and "C1-dev-0003" in ids and "C6-dev-0020" in ids
    expected_seeds = {100 * c + i for c in range(7) for i in range(DEV_COUNTS[f"C{c}"])}
    assert {s.seed for s in dev} == expected_seeds and len({s.seed for s in dev}) == 141


def test_eval_layout(evals):
    assert Counter(s.category for s in evals) == EVAL_COUNTS
    assert len(evals) == 210 and all(s.split == "eval" for s in evals)
    expected_seeds = {1000 + 100 * c + i for c in range(7) for i in range(30)}
    assert {s.seed for s in evals} == expected_seeds
    assert "C1-eval-0003" in {s.id for s in evals}


def test_splits_do_not_share_seeds(dev, evals):
    assert not {s.seed for s in dev} & {s.seed for s in evals}


@pytest.mark.parametrize("fixture,n", [("dev", 20), ("evals", 30)])
def test_variants_one_explicit_to_two_implicit(request, fixture, n):
    scenarios = request.getfixturevalue(fixture)
    for category in ("C1", "C3"):
        sel = sorted((s for s in scenarios if s.category == category), key=lambda s: s.id)
        assert [s.variant for s in sel] == ["explicit" if i % 3 == 0 else "implicit" for i in range(n)]
    for s in scenarios:
        if s.category not in ("C1", "C3"):
            assert s.variant == "none"


def test_c3_resolution_cycle(dev, evals):
    cycle = ["later_event", "later_event", "authority", "disputed", "later_event"]
    for scenarios, n in ((dev, 20), (evals, 30)):
        sel = sorted((s for s in scenarios if s.category == "C3"), key=lambda s: s.id)
        assert [s.resolution for s in sel] == [cycle[i % 5] for i in range(n)]
        assert Counter(s.resolution for s in sel)["later_event"] == n * 6 // 10
    assert all(s.resolution == "none" for s in dev if s.category != "C3")


def test_c6_lengths(dev, evals):
    for scenarios, per in ((dev, 7), (evals, 10)):
        sel = [s for s in scenarios if s.category == "C6"]
        assert Counter(s.n_sessions for s in sel) == {10: per, 20: per, 30: per}
        for i, s in enumerate(sorted(sel, key=lambda x: x.id)):
            assert s.n_sessions == (10, 20, 30)[i % 3]
    assert all(s.n_sessions == 10 for s in dev if s.category != "C6")


def test_every_dev_and_eval_scenario_validates(dev, evals):
    for s in dev + evals:
        assert validate(s) == [], s.id


def test_all_scenarios_unique_and_ids_match_files(dev):
    assert len({dumps(s) for s in dev}) == len(dev)


def test_cli_is_reproducible_and_writes_manifest(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    run_cli("dev", a)
    run_cli("dev", b)
    files_a, files_b = read_dir(a), read_dir(b)
    assert files_a == files_b and len(files_a) == 141
    manifest = json.loads((a / "manifest.json").read_text())
    assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()
    assert manifest["split"] == "dev" and len(manifest["scenarios"]) == 141
    row = next(r for r in manifest["scenarios"] if r["id"] == "C3-dev-0003")
    assert set(row) == {"id", "category", "seed", "variant", "resolution", "n_sessions", "sha256"}
    assert (row["category"], row["seed"], row["variant"], row["resolution"], row["n_sessions"]) == (
        "C3", 303, "explicit", "disputed", 10)
    for r in manifest["scenarios"]:
        assert r["sha256"] == hashlib.sha256(files_a[r["id"] + ".json"]).hexdigest()
    assert load(a / "C1-dev-0003.json").id == "C1-dev-0003"


@pytest.mark.parametrize("split", ["dev", "eval", "holdout"])
def test_committed_data_is_the_current_generator_output(split, tmp_path):
    committed = ROOT / ("holdout" if split == "holdout" else f"data/{split}")
    assert (committed / "manifest.json").exists(), f"{committed} is not generated"
    run_cli(split, tmp_path / "fresh")
    fresh = tmp_path / "fresh"
    assert read_dir(committed) == read_dir(fresh)
    assert (committed / "manifest.json").read_bytes() == (fresh / "manifest.json").read_bytes()


def test_holdout_layout_and_validity():
    hold = generate_split("holdout")
    assert 8 <= len(hold) <= 12
    assert [s.id for s in hold] == [f"H-{i:04d}" for i in range(1, len(hold) + 1)]
    assert all(s.split == "holdout" for s in hold)
    assert len({s.category for s in hold}) >= 5
    used = {100 * c + i for c in range(7) for i in range(30)} | {1000 + 100 * c + i for c in range(7) for i in range(30)}
    assert not {s.seed for s in hold} & used
    for s in hold:
        assert validate(s) == [], s.id
