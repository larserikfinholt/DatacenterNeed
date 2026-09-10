"""Export deterministic browser scenario parity vectors from the Python model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from datacenter_need.pipeline import evaluate_dataset, load_dataset
from datacenter_need.scenario import _evaluate_combination

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPOSITORY_ROOT / "data" / "examples" / "synthetic.yaml"
OUTPUT_PATH = (
    REPOSITORY_ROOT / "web" / "public" / "artifacts" / "v1" / "scenario-golden.json"
)


def selection(
    adoption: str,
    placement: str,
    *,
    demand_multiplier: float,
    cloud_share: float,
    domestic_hosting_share: float,
    cloud_pue: float,
) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "datasetId": "synthetic",
        "adoption": adoption,
        "placement": placement,
        "overrides": {
            "demandMultiplier": demand_multiplier,
            "cloudShare": cloud_share,
            "domesticHostingShare": domestic_hosting_share,
            "cloudPue": cloud_pue,
        },
    }


def export_vectors() -> None:
    dataset, _ = load_dataset(DATASET_PATH)
    evaluated = evaluate_dataset(dataset)
    scenario = dataset.scenario
    if scenario is None:
        raise ValueError("synthetic dataset must define a scenario")

    occupation_rows = evaluated["occupations"]
    adoptions = {item.name.value: item for item in scenario.adoption_presets}
    placements = {item.name.value: item for item in scenario.placement_presets}
    vectors: list[dict[str, Any]] = []

    def append_vector(
        vector_id: str,
        adoption_name: str,
        placement_name: str,
        *,
        demand_multiplier: float,
        cloud_share: float,
        domestic_hosting_share: float,
        cloud_pue: float,
    ) -> None:
        scenario_selection = selection(
            adoption_name,
            placement_name,
            demand_multiplier=demand_multiplier,
            cloud_share=cloud_share,
            domestic_hosting_share=domestic_hosting_share,
            cloud_pue=cloud_pue,
        )
        expected = _evaluate_combination(
            dataset,
            scenario,
            adoptions[adoption_name],
            placements[placement_name],
            occupation_rows,
            demand_multiplier=demand_multiplier,
            cloud_share=cloud_share,
            domestic_hosting_share=domestic_hosting_share,
            cloud_pue=cloud_pue,
        )
        vectors.append({"id": vector_id, "selection": scenario_selection, "expected": expected})

    for adoption_name in sorted(adoptions):
        for placement_name in sorted(placements):
            placement = placements[placement_name]
            append_vector(
                f"preset__{adoption_name}__{placement_name}",
                adoption_name,
                placement_name,
                demand_multiplier=1,
                cloud_share=placement.cloud_share,
                domestic_hosting_share=placement.domestic_hosting_share,
                cloud_pue=dataset.cloud_pue.value,
            )

    sensitivity = scenario.sensitivity
    reference_adoption = sensitivity.adoption.value
    reference_placement = sensitivity.placement.value
    reference = placements[reference_placement]
    bases = {
        "demand_multiplier": 1,
        "cloud_share": reference.cloud_share,
        "domestic_hosting_share": reference.domestic_hosting_share,
        "cloud_pue": dataset.cloud_pue.value,
    }
    for item in sorted(sensitivity.named_ranges, key=lambda value: value.id):
        for position in ("low", "base", "high"):
            parameters = dict(bases)
            parameters[item.parameter] = getattr(item, position)
            append_vector(
                f"sensitivity__{item.id}__{position}",
                reference_adoption,
                reference_placement,
                **parameters,
            )

    for item in sorted(sensitivity.joint_stress_cases, key=lambda value: value.id):
        append_vector(
            f"stress__{item.id}",
            reference_adoption,
            reference_placement,
            demand_multiplier=item.demand_multiplier,
            cloud_share=item.cloud_share,
            domestic_hosting_share=item.domestic_hosting_share,
            cloud_pue=item.cloud_pue,
        )

    append_vector(
        "override__all_parameters",
        "high",
        "hybrid",
        demand_multiplier=1.25,
        cloud_share=0.35,
        domestic_hosting_share=0.65,
        cloud_pue=1.1,
    )

    output = {
        "schemaVersion": "1.0",
        "datasetId": "synthetic",
        "vectors": vectors,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    export_vectors()