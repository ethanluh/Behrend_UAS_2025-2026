from pathlib import Path

import pytest
import yaml

import od_lib

FILES = [f"img_{i:04d}.png" for i in range(100)]


def test_counts():
    plan = od_lib.plan_split(FILES, val_ratio=0.1, test_ratio=0.1, seed=42)
    assert len(plan["val"]) == 10
    assert len(plan["test"]) == 10
    assert len(plan["train"]) == 80


def test_no_leakage_and_full_coverage():
    plan = od_lib.plan_split(FILES, 0.1, 0.1, seed=42)
    train, val, test = set(plan["train"]), set(plan["val"]), set(plan["test"])
    # Disjoint.
    assert train & val == set()
    assert train & test == set()
    assert val & test == set()
    # Full coverage, no duplicates.
    assert train | val | test == set(FILES)
    assert len(plan["train"]) + len(plan["val"]) + len(plan["test"]) == len(FILES)


def test_deterministic_for_seed():
    a = od_lib.plan_split(FILES, 0.1, 0.1, seed=7)
    b = od_lib.plan_split(FILES, 0.1, 0.1, seed=7)
    assert a == b


def test_different_seeds_differ():
    a = od_lib.plan_split(FILES, 0.1, 0.1, seed=1)
    b = od_lib.plan_split(FILES, 0.1, 0.1, seed=2)
    assert a["val"] != b["val"]


def test_tiny_input():
    plan = od_lib.plan_split(["a.png", "b.png"], 0.1, 0.1, seed=0)
    assert plan["val"] == [] and plan["test"] == []
    assert sorted(plan["train"]) == ["a.png", "b.png"]


def test_ratios_too_large_rejected():
    with pytest.raises(ValueError):
        od_lib.plan_split(FILES, 0.6, 0.6, seed=0)


def test_dataset_yaml_schema():
    yaml_path = Path(__file__).resolve().parent.parent \
        / "ObjectDetection" / "training" / "dataset.yaml"
    cfg = yaml.safe_load(yaml_path.read_text())
    assert cfg["nc"] == 2
    assert cfg["names"] == ["mannequin", "tent"]
    for key in ("train", "val", "test"):
        assert key in cfg
