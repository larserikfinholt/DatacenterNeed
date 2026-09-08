from pathlib import Path

import pytest
from pydantic import ValidationError

from datacenter_need.pipeline import build_dataset

EXAMPLE = Path("data/examples/synthetic.yaml")


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


def test_repeat_offline_builds_are_identical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*args, **kwargs):
        raise AssertionError("offline build attempted network access")

    monkeypatch.setattr("socket.create_connection", no_network)
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_dataset(EXAMPLE, first, offline=True)
    build_dataset(EXAMPLE, second, offline=True)
    assert snapshot(first) == snapshot(second)


def test_invalid_input_does_not_replace_last_good_output(tmp_path: Path) -> None:
    output = tmp_path / "output"
    build_dataset(EXAMPLE, output, offline=True)
    before = snapshot(output)
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("schema_version: '1.0'\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        build_dataset(invalid, output, offline=True)
    assert snapshot(output) == before


def test_output_directory_cannot_contain_input(tmp_path: Path) -> None:
    input_path = tmp_path / "input.yaml"
    input_path.write_bytes(EXAMPLE.read_bytes())
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="contain the input"):
        build_dataset(input_path, tmp_path)
    assert snapshot(tmp_path) == before


def test_output_directory_preserves_unrelated_files(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "notes.txt").write_text("User research notes", encoding="utf-8")
    before = snapshot(output)
    with pytest.raises(ValueError, match="other than a previous build"):
        build_dataset(EXAMPLE, output)
    assert snapshot(output) == before


def test_existing_backup_is_not_deleted(tmp_path: Path) -> None:
    output = tmp_path / "output"
    backup = tmp_path / ".output.backup"
    backup.mkdir()
    (backup / "notes.txt").write_text("Recover this", encoding="utf-8")
    before = snapshot(backup)
    with pytest.raises(ValueError, match="manual recovery"):
        build_dataset(EXAMPLE, output)
    assert snapshot(backup) == before