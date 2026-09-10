import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from datacenter_need.developer_reference_pipeline import (
    build_developer_reference,
    load_developer_reference,
)

EXAMPLE = Path("data/examples/developer-reference.yaml")


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


def test_reference_build_is_deterministic_and_traceable(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_developer_reference(EXAMPLE, first)
    build_developer_reference(EXAMPLE, second)

    assert snapshot(first) == snapshot(second)
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    result = json.loads((first / "result.json").read_text(encoding="utf-8"))
    trace = json.loads((first / "trace.json").read_text(encoding="utf-8"))
    assert manifest["namespace"] == "developer-reference/v1"
    assert manifest["offline"] is True
    assert [row["id"] for row in result["scenarios"]] == ["baseline", "heavy", "low-load"]
    assert trace["formula_ids"]
    assert {row["trace_id"] for row in result["scenarios"]} == {
        f"scenario-{row['id']}" for row in trace["scenarios"]
    }


def test_reference_build_preserves_output_on_invalid_input(tmp_path: Path) -> None:
    output = tmp_path / "output"
    build_developer_reference(EXAMPLE, output)
    before = snapshot(output)
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("schema_version: '1.0'\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        build_developer_reference(invalid, output)
    assert snapshot(output) == before


def test_reference_build_rejects_input_inside_output(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    input_path.write_bytes(EXAMPLE.read_bytes())
    with pytest.raises(ValueError, match="contain the input"):
        build_developer_reference(input_path, tmp_path)


def test_reference_build_preserves_unrelated_files(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "notes.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="other than a previous build"):
        build_developer_reference(EXAMPLE, output)
    assert (output / "notes.txt").read_text(encoding="utf-8") == "keep"


def test_reference_input_loads_and_keeps_unknowns_null() -> None:
    dataset, _ = load_developer_reference(EXAMPLE)
    assert dataset.model.weight_memory_gib is None
    assert dataset.serving.kv_memory_gib is None