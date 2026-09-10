"""Offline evaluation and artifacts for the standalone developer reference."""

from __future__ import annotations

import csv
import io
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from datacenter_need.developer_reference import (
    AcceleratorProfile,
    CapacityStatus,
    ModelProfile,
    PowerProfile,
    ServingProfile,
    allocate_workday_energy,
    power_from_profiles,
    screen_capacity,
    validate_profile_compatibility,
)
from datacenter_need.developer_reference_schemas import DeveloperReferenceInput
from datacenter_need.pipeline import canonical_json, sha256_bytes


def load_developer_reference(path: Path) -> tuple[DeveloperReferenceInput, bytes]:
    content = path.read_bytes()
    loaded = yaml.safe_load(content)
    if not isinstance(loaded, dict):
        raise TypeError("input YAML must contain a mapping")
    return DeveloperReferenceInput.model_validate(loaded), content


def _profiles(dataset: DeveloperReferenceInput) -> tuple[ModelProfile, AcceleratorProfile, PowerProfile, ServingProfile]:
    model = ModelProfile(**dataset.model.model_dump(exclude={"source_ids"}))
    accelerator = AcceleratorProfile(**dataset.accelerator.model_dump(exclude={"source_ids"}))
    power = PowerProfile(**dataset.power.model_dump(exclude={"source_ids"}))
    serving = ServingProfile(**dataset.serving.model_dump(exclude={"source_ids"}))
    return model, accelerator, power, serving


def evaluate_developer_reference(dataset: DeveloperReferenceInput) -> dict[str, Any]:
    model, accelerator, power, serving = _profiles(dataset)
    compatibility_reason = validate_profile_compatibility(model, accelerator, serving)
    rows: list[dict[str, Any]] = []
    for scenario in sorted(dataset.scenarios, key=lambda item: item.id):
        workload = scenario.workload
        node_power = power_from_profiles(accelerator, power, scenario.gpu_utilization)
        allocation = allocate_workday_energy(
            node_power,
            workload.concurrent_developers,
            workload.workday_hours,
            actual_occupancy=dataset.operations.actual_occupancy,
            pue=dataset.operations.pue,
            off_hours_hours=dataset.operations.off_hours,
        )
        capacity = screen_capacity(
            workload.concurrent_developers,
            workload.jobs_per_developer,
            workload.inference_duty_cycle,
            dataset.operations.burst_margin,
            serving.practical_concurrency,
            serving.aggregate_output_tokens_per_second,
            serving.per_stream_output_tokens_per_second,
        )
        if compatibility_reason is not None:
            capacity = capacity.__class__(
                CapacityStatus.UNKNOWN,
                capacity.requested_developers,
                capacity.requested_streams,
                None,
                None,
                capacity.required_output_tokens_per_second,
                "profile compatibility",
                compatibility_reason,
            )
        trace_id = f"scenario-{scenario.id}"
        rows.append(
            {
                "id": scenario.id,
                "title": scenario.title,
                "gpu_utilization": scenario.gpu_utilization,
                "workload": workload.model_dump(mode="json"),
                "node_it_w": allocation.node_it_w,
                "node_it_kw": allocation.node_it_w / 1_000,
                "watts_per_active_developer": allocation.watts_per_active_developer,
                "workday_kwh_per_active_developer": allocation.workday_kwh_per_active_developer,
                "facility_node_w": allocation.facility_node_w,
                "off_hours_kwh": allocation.off_hours_kwh,
                "capacity": {
                    "status": capacity.status.value,
                    "requested_developers": capacity.requested_developers,
                    "requested_streams": capacity.requested_streams,
                    "supported_developers": capacity.supported_developers,
                    "supported_streams": capacity.supported_streams,
                    "required_output_tokens_per_second": capacity.required_output_tokens_per_second,
                    "limiting_constraint": capacity.limiting_constraint,
                    "unknown_reason": capacity.unknown_reason,
                },
                "trace_id": trace_id,
                "source_ids": sorted(set(scenario.source_ids)),
            }
        )
    baseline = next((row for row in rows if row["id"] == "baseline"), rows[0])
    baseline_power = baseline["node_it_w"]
    baseline_developers = baseline["workload"]["concurrent_developers"]
    sweeps = {
        "mode": "fixed_power_allocation",
        "developers": [
            {
                "concurrent_developers": developers,
                "node_it_kw": baseline_power / 1_000,
                "watts_per_active_developer": baseline_power / developers,
                "trace_id": "sweep-developers-fixed-power",
            }
            for developers in (5, 10, 20, 40)
        ],
        "jobs": [
            {
                "jobs_per_developer": jobs,
                "watts_per_active_developer": baseline_power / baseline_developers,
                "trace_id": "sweep-jobs-fixed-power",
            }
            for jobs in (1, 2)
        ],
    }
    return {
        "contract_version": dataset.schema_version,
        "model_version": dataset.model_version,
        "reference_id": dataset.reference_id,
        "profiles": {
            "model": dataset.model.model_dump(mode="json"),
            "accelerator": dataset.accelerator.model_dump(mode="json"),
            "power": dataset.power.model_dump(mode="json"),
            "serving": dataset.serving.model_dump(mode="json"),
            "operations": dataset.operations.model_dump(mode="json"),
        },
        "evidence_gaps": sorted(
            item.unknown_reason for item in dataset.evidence if item.unknown_reason is not None
        ),
        "sweeps": sweeps,
        "scenarios": rows,
    }


def _scenario_csv_text(rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    fieldnames = [
        "id", "title", "gpu_utilization", "concurrent_developers", "jobs_per_developer",
        "duty_cycle", "node_it_kw", "watts_per_active_developer",
        "workday_kwh_per_active_developer", "capacity_status", "supported_developers",
        "supported_streams", "limiting_constraint", "trace_id", "source_ids",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        workload = row["workload"]
        capacity = row["capacity"]
        writer.writerow({
            "id": row["id"], "title": row["title"], "gpu_utilization": row["gpu_utilization"],
            "concurrent_developers": workload["concurrent_developers"],
            "jobs_per_developer": workload["jobs_per_developer"],
            "duty_cycle": workload["inference_duty_cycle"], "node_it_kw": row["node_it_kw"],
            "watts_per_active_developer": row["watts_per_active_developer"],
            "workday_kwh_per_active_developer": row["workday_kwh_per_active_developer"],
            "capacity_status": capacity["status"], "supported_developers": capacity["supported_developers"],
            "supported_streams": capacity["supported_streams"],
            "limiting_constraint": capacity["limiting_constraint"], "trace_id": row["trace_id"],
            "source_ids": ",".join(row["source_ids"]),
        })
    return output.getvalue().encode("utf-8")


def _reference_model_hash() -> str:
    package = Path(__file__).parent
    names = ("developer_reference.py", "developer_reference_schemas.py", "developer_reference_pipeline.py")
    content = b"".join(name.encode() + b"\0" + (package / name).read_bytes() for name in names)
    return sha256_bytes(content)


def build_developer_reference(input_path: Path, output_path: Path, *, offline: bool = True) -> dict[str, Any]:
    if not offline:
        raise ValueError("developer reference builds support offline inputs only")
    artifact_names = {"result.json", "scenarios.csv", "trace.json", "input.schema.json", "manifest.json"}
    if input_path.resolve().is_relative_to(output_path.resolve()):
        raise ValueError("output directory must not contain the input file")
    if output_path.is_symlink():
        raise ValueError("output directory must not be a symbolic link")
    if output_path.exists():
        if not output_path.is_dir():
            raise ValueError("output path must be a directory")
        existing = list(output_path.iterdir())
        if existing and ({path.name for path in existing} != artifact_names or any(not path.is_file() or path.is_symlink() for path in existing)):
            raise ValueError("output directory contains files other than a previous build")
    backup = output_path.with_name(f".{output_path.name}.backup")
    if backup.exists():
        raise ValueError(f"previous build backup requires manual recovery: {backup}")
    dataset, input_content = load_developer_reference(input_path)
    result = evaluate_developer_reference(dataset)
    trace = {
        "input": dataset.model_dump(mode="json"),
        "formula_ids": ["node_it_power_linear", "workday_energy_allocation", "capacity_screen"],
        "scenarios": result["scenarios"],
    }
    files = {
        "result.json": canonical_json(result).encode("utf-8"),
        "scenarios.csv": _scenario_csv_text(result["scenarios"]),
        "trace.json": canonical_json(trace).encode("utf-8"),
        "input.schema.json": canonical_json(DeveloperReferenceInput.model_json_schema()).encode("utf-8"),
    }
    manifest = {
        "namespace": "developer-reference/v1",
        "hash_algorithm": "sha256",
        "input": {"path": input_path.as_posix(), "sha256": sha256_bytes(input_content)},
        "model": {"version": dataset.model_version, "sha256": _reference_model_hash()},
        "schema": {"version": dataset.schema_version, "sha256": sha256_bytes(files["input.schema.json"])},
        "outputs": {name: sha256_bytes(content) for name, content in sorted(files.items())},
        "offline": True,
    }
    files["manifest.json"] = canonical_json(manifest).encode("utf-8")
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