import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPOSITORY_ROOT / "web" / "public" / "artifacts" / "v1"
DATASETS = (
    {
        "id": "synthetic",
        "title": "Synthetic example",
        "kind": "synthetic",
        "country": "NO",
        "year": 2025,
        "source": REPOSITORY_ROOT / "build" / "example",
    },
    {
        "id": "norway-2025",
        "title": "Norway 2025 observed baseline",
        "kind": "observed-baseline",
        "country": "NO",
        "year": 2025,
        "source": REPOSITORY_ROOT / "build" / "norway-2025",
    },
)
FILES = ("result.json", "manifest.json", "occupation_breakdown.csv")
REFERENCE_FILES = ("result.json", "manifest.json", "scenarios.csv", "trace.json", "input.schema.json")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_manifest_version(manifest: dict[str, Any], group: str) -> str:
    metadata = manifest.get(group)
    if not isinstance(metadata, dict) or not isinstance(metadata.get("version"), str):
        raise TypeError(f"manifest {group}.version must be a string")
    return metadata["version"]


def refresh() -> None:
    index: dict[str, list[dict[str, object]]] = {"datasets": []}

    for dataset in DATASETS:
        source = dataset["source"]
        if not isinstance(source, Path):
            raise TypeError("dataset source must be a path")
        manifest = load_json(source / "manifest.json")
        outputs = manifest.get("outputs")
        if not isinstance(outputs, dict) or not isinstance(outputs.get("result.json"), str):
            raise TypeError(f"{source / 'manifest.json'} has no result.json hash")

        actual_hash = sha256(source / "result.json")
        if actual_hash != outputs["result.json"]:
            raise ValueError(
                f"result hash mismatch for {dataset['id']}: "
                f"expected {outputs['result.json']}, got {actual_hash}"
            )

        dataset_id = str(dataset["id"])
        destination = ARTIFACT_ROOT / dataset_id
        destination.mkdir(parents=True, exist_ok=True)
        for filename in FILES:
            shutil.copyfile(source / filename, destination / filename)

        base_path = f"/artifacts/v1/{dataset_id}"
        index["datasets"].append(
            {
                "id": dataset_id,
                "title": dataset["title"],
                "kind": dataset["kind"],
                "country": dataset["country"],
                "year": dataset["year"],
                "schemaVersion": require_manifest_version(manifest, "schema"),
                "modelVersion": require_manifest_version(manifest, "model"),
                "paths": {
                    "result": f"{base_path}/result.json",
                    "manifest": f"{base_path}/manifest.json",
                    "occupationBreakdown": f"{base_path}/occupation_breakdown.csv",
                },
            }
        )

    reference_source = REPOSITORY_ROOT / "build" / "developer-reference" / "v1"
    reference_manifest = load_json(reference_source / "manifest.json")
    reference_outputs = reference_manifest.get("outputs")
    if not isinstance(reference_outputs, dict):
        raise TypeError(f"{reference_source / 'manifest.json'} has no outputs hashes")
    reference_destination = ARTIFACT_ROOT / "developer-reference"
    reference_destination.mkdir(parents=True, exist_ok=True)
    for filename in REFERENCE_FILES:
        if filename == "manifest.json":
            shutil.copyfile(reference_source / filename, reference_destination / filename)
            continue
        expected = reference_outputs.get(filename)
        if not isinstance(expected, str) or sha256(reference_source / filename) != expected:
            raise ValueError(f"reference artifact hash mismatch for {filename}")
        shutil.copyfile(reference_source / filename, reference_destination / filename)

    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_ROOT / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    refresh()