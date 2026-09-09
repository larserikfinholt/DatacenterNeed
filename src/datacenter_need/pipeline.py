"""Offline input loading, evaluation, and deterministic artifact generation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from datacenter_need.model import (
    EnergyBenchmark,
    ModelPlacement,
    annual_average_load_mw,
    annual_requests,
    facility_energy_mwh,
    inference_energy,
)
from datacenter_need.schemas import InputDataset

UNMODELED_CATEGORIES = {
    "non_ai": "Traditional data-centre workloads are outside this milestone.",
    "consumer_ai": "Consumer AI use is not represented by occupation inputs.",
    "autonomous_background_inference": "Autonomous and background inference is not modeled.",
    "foundation_training": "Foundation-model training is not modeled.",
    "fine_tuning": "Fine-tuning is not modeled.",
    "retrieval_embeddings": "Retrieval and embedding workloads are not modeled.",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_dataset(path: Path) -> tuple[InputDataset, bytes]:
    content = path.read_bytes()
    loaded = yaml.safe_load(content)
    if not isinstance(loaded, dict):
        raise TypeError("input YAML must contain a mapping")
    return InputDataset.model_validate(loaded), content


def evaluate_dataset(dataset: InputDataset) -> dict[str, Any]:
    observations = {item.id: item for item in dataset.observations}
    benchmarks = {item.id: item for item in dataset.energy_benchmarks}
    occupations = {item.id: item for item in dataset.occupations}
    rows: list[dict[str, Any]] = []

    for profile in sorted(dataset.task_profiles, key=lambda item: item.occupation_id):
        occupation = occupations[profile.occupation_id]
        workers = observations[occupation.workers_observation_id]
        hours = observations[occupation.annual_hours_observation_id]
        source_ids = sorted(
            {
                workers.source_id,
                hours.source_id,
                *profile.source_ids,
                *(benchmarks[item.benchmark_id].source_id for item in profile.placements),
                *(
                    dataset.cloud_pue.source_ids
                    if any(
                        benchmarks[item.benchmark_id].boundary.value == "cloud_it"
                        for item in profile.placements
                    )
                    else []
                ),
            }
        )
        missing = [
            reason
            for observation in (workers, hours)
            if observation.value is None
            for reason in [observation.missing_reason]
        ]
        if missing:
            rows.append(
                {
                    "occupation_id": occupation.id,
                    "title": occupation.title,
                    "country_code": occupation.country_code,
                    "year": occupation.year,
                    "workforce_basis": occupation.workforce_basis,
                    "annual_requests": None,
                    "cloud_facility_mwh": None,
                    "local_device_mwh": None,
                    "known_total_mwh": None,
                    "status": "unknown",
                    "missing_reason": "; ".join(missing),
                    "source_ids": source_ids,
                }
            )
            continue

        requests = annual_requests(
            workers.value,
            hours.value,
            profile.digital_fraction,
            profile.ai_fraction,
            profile.requests_per_ai_hour,
        )
        placements = [
            ModelPlacement(
                item.name,
                item.share,
                EnergyBenchmark(
                    benchmarks[item.benchmark_id].id,
                    benchmarks[item.benchmark_id].kwh_per_request,
                    benchmarks[item.benchmark_id].boundary.value,
                ),
            )
            for item in profile.placements
        ]
        energy = inference_energy(requests, placements, dataset.cloud_pue.value)
        rows.append(
            {
                "occupation_id": occupation.id,
                "title": occupation.title,
                "country_code": occupation.country_code,
                "year": occupation.year,
                "workforce_basis": occupation.workforce_basis,
                "annual_requests": requests,
                "cloud_facility_mwh": energy.cloud_facility_kwh / 1_000,
                "local_device_mwh": energy.local_device_kwh / 1_000,
                "known_total_mwh": energy.total_kwh / 1_000,
                "status": "known",
                "missing_reason": None,
                "source_ids": source_ids,
            }
        )

    known_rows = [row for row in rows if row["known_total_mwh"] is not None]
    countries: list[dict[str, Any]] = []
    for country_code, year in sorted({(row["country_code"], row["year"]) for row in rows}):
        country_rows = [
            row for row in known_rows if (row["country_code"], row["year"]) == (country_code, year)
        ]
        all_country_rows = [
            row for row in rows if (row["country_code"], row["year"]) == (country_code, year)
        ]
        countries.append(
            {
                "country_code": country_code,
                "year": year,
                "known_occupational_ai_subtotal_mwh": (
                    sum(row["known_total_mwh"] for row in country_rows) if country_rows else None
                ),
                "calculated_occupation_count": len(country_rows),
                "unknown_occupation_count": len(all_country_rows) - len(country_rows),
                "national_total_mwh": None,
                "scope_status": "incomplete",
            }
        )

    comparators = []
    for observation_id in sorted(dataset.facility_comparator_observation_ids):
        observation = observations[observation_id]
        comparators.append(
            {
                "observation_id": observation.id,
                "country_code": observation.country_code,
                "year": observation.year,
                "capacity_mw": observation.value,
                "load_factor": 1.0,
                "annual_energy_mwh": (
                    None
                    if observation.value is None
                    else facility_energy_mwh(observation.value, 1, observation.year)
                ),
                "annual_average_load_mw": (
                    None
                    if observation.value is None
                    else annual_average_load_mw(
                        facility_energy_mwh(observation.value, 1, observation.year),
                        observation.year,
                    )
                ),
                "interpretation": "Hypothetical full-year operation at load factor 1, not measured use.",
                "evidence_status": observation.evidence_status.value,
                "missing_reason": observation.missing_reason,
                "source_ids": [observation.source_id],
            }
        )

    return {
        "schema_version": dataset.schema_version,
        "model_version": dataset.model_version,
        "scope": {
            "description": "Occupation-linked human-triggered AI inference only.",
            "national_total_mwh": None,
            "scope_status": "incomplete",
            "unmodeled_categories": [
                {"category": category, "energy_mwh": None, "reason": reason}
                for category, reason in UNMODELED_CATEGORIES.items()
            ],
        },
        "countries": countries,
        "occupations": rows,
        "facility_comparators": comparators,
        "input_trace": dataset.model_dump(mode="json"),
        "source_trace": [
            source.model_dump(mode="json") for source in sorted(dataset.sources, key=lambda item: item.id)
        ],
    }


def _csv_text(rows: list[dict[str, Any]]) -> str:
    fields = [
        "occupation_id",
        "title",
        "country_code",
        "year",
        "workforce_basis",
        "annual_requests",
        "cloud_facility_mwh",
        "local_device_mwh",
        "known_total_mwh",
        "status",
        "missing_reason",
        "source_ids",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        csv_row = dict(row)
        csv_row["source_ids"] = ";".join(row["source_ids"])
        writer.writerow(csv_row)
    return output.getvalue()


def _model_hash() -> str:
    package = Path(__file__).parent
    content = b"".join(
        path.name.encode("utf-8") + b"\0" + path.read_bytes()
        for path in sorted(package / name for name in ("model.py", "pipeline.py", "schemas.py"))
    )
    return sha256_bytes(content)


def build_dataset(input_path: Path, output_path: Path, *, offline: bool = True) -> dict[str, Any]:
    """Validate and calculate fully before atomically replacing deterministic output files."""
    if not offline:
        raise ValueError("this milestone supports offline builds only")
    artifact_names = {
        "result.json", "occupation_breakdown.csv", "input.schema.json", "manifest.json"
    }
    if input_path.resolve().is_relative_to(output_path.resolve()):
        raise ValueError("output directory must not contain the input file")
    if output_path.is_symlink():
        raise ValueError("output directory must not be a symbolic link")
    if output_path.exists():
        if not output_path.is_dir():
            raise ValueError("output path must be a directory")
        existing = list(output_path.iterdir())
        if existing and (
            {path.name for path in existing} != artifact_names
            or any(not path.is_file() or path.is_symlink() for path in existing)
        ):
            raise ValueError("output directory contains files other than a previous build")
    backup = output_path.with_name(f".{output_path.name}.backup")
    if backup.exists():
        raise ValueError(f"previous build backup requires manual recovery: {backup}")
    dataset, input_content = load_dataset(input_path)
    result = evaluate_dataset(dataset)
    schema = InputDataset.model_json_schema()
    files = {
        "result.json": canonical_json(result).encode(),
        "occupation_breakdown.csv": _csv_text(result["occupations"]).encode(),
        "input.schema.json": canonical_json(schema).encode(),
    }
    manifest = {
        "hash_algorithm": "sha256",
        "input": {"path": input_path.as_posix(), "sha256": sha256_bytes(input_content)},
        "model": {"version": dataset.model_version, "sha256": _model_hash()},
        "schema": {"version": dataset.schema_version, "sha256": sha256_bytes(files["input.schema.json"])},
        "outputs": {name: sha256_bytes(content) for name, content in sorted(files.items())},
        "offline": True,
    }
    files["manifest.json"] = canonical_json(manifest).encode()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_path.name}-", dir=output_path.parent))
    try:
        for name, content in files.items():
            (temporary / name).write_bytes(content)
        if output_path.exists():
            os.replace(output_path, backup)
        try:
            os.replace(temporary, output_path)
        except BaseException:
            if backup.exists():
                os.replace(backup, output_path)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest
