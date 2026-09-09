from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from datacenter_need.pipeline import evaluate_dataset
from datacenter_need.schemas import InputDataset

EXAMPLE = Path("data/examples/synthetic.yaml")


def inventory_data() -> dict:
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["observations"].extend(
        [
            {
                "id": "no-project-connection",
                "country_code": "NO",
                "year": 2025,
                "metric": "connection_capacity",
                "unit": "MW",
                "value": 100,
                "source_id": "synthetic-capacity",
                "definition": "Synthetic connection quantity",
                "boundary": "grid_connection",
                "evidence_status": "synthetic",
                "locator": "synthetic project phase",
            },
            {
                "id": "no-project-connection-unknown",
                "country_code": "NO",
                "year": 2025,
                "metric": "connection_capacity",
                "unit": "MW",
                "value": None,
                "missing_reason": "Not disclosed",
                "source_id": "synthetic-capacity",
                "definition": "Synthetic missing connection quantity",
                "boundary": "grid_connection",
                "evidence_status": "synthetic",
                "locator": "synthetic project phase",
            },
        ]
    )
    data["projects"] = [
        {
            "id": "project-a",
            "title": "Project A",
            "country_code": "NO",
            "aliases": ["Site Alpha"],
            "completeness_limitations": "Synthetic fixture, not an inventory.",
            "phases": [
                {
                    "id": "project-a-phase-1",
                    "title": "Phase 1",
                    "aliases": ["First build"],
                    "observation_ids": [
                        "no-project-connection",
                        "no-project-connection-unknown",
                    ],
                    "construction_status": [
                        {
                            "status": "planning",
                            "as_of_date": "2025-01-01",
                            "source_id": "synthetic-capacity",
                            "locator": "synthetic construction status",
                        }
                    ],
                    "grid_status": [
                        {
                            "status": "reserved",
                            "as_of_date": "2025-02-01",
                            "source_id": "synthetic-capacity",
                            "locator": "synthetic grid status",
                        }
                    ],
                }
            ],
        }
    ]
    return data


def test_project_aliases_do_not_duplicate_phase_totals_and_unknowns_stay_unknown() -> None:
    result = evaluate_dataset(InputDataset.model_validate(inventory_data()))

    assert result["projects"][0]["aliases"] == ["Site Alpha"]
    assert result["projects"][0]["phases"][0]["construction_status"][0]["status"] == "planning"
    assert result["projects"][0]["phases"][0]["grid_status"][0]["status"] == "reserved"
    assert result["project_totals"] == [
        {
            "country_code": "NO",
            "year": 2025,
            "metric": "connection_capacity",
            "unit": "MW",
            "boundary": "grid_connection",
            "known_subtotal": 100.0,
            "complete_total": None,
            "known_observation_count": 1,
            "unknown_observation_count": 1,
        }
    ]


def test_project_observation_cannot_be_attached_twice() -> None:
    data = inventory_data()
    duplicate_phase = deepcopy(data["projects"][0]["phases"][0])
    duplicate_phase["id"] = "project-a-phase-2"
    duplicate_phase["observation_ids"] = ["no-project-connection"]
    data["projects"][0]["phases"].append(duplicate_phase)

    with pytest.raises(ValidationError, match="only one phase"):
        InputDataset.model_validate(data)


def test_capacity_boundary_contract_rejects_mismatch() -> None:
    data = inventory_data()
    observation = next(
        item for item in data["observations"] if item["id"] == "no-project-connection"
    )
    observation["boundary"] = "cloud_facility"

    with pytest.raises(ValidationError, match="incompatible"):
        InputDataset.model_validate(data)