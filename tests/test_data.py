from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from datacenter_need.pipeline import evaluate_dataset, load_dataset
from datacenter_need.schemas import InputDataset

EXAMPLE = Path("data/examples/synthetic.yaml")
NORWAY_SLICE = Path("data/norway/software-developers-2025.yaml")


def example_data() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def test_synthetic_two_country_dataset_has_no_norway_special_case() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    result = evaluate_dataset(dataset)
    assert {(item["country_code"], item["year"]) for item in result["countries"]} == {
        ("NO", 2025),
        ("SE", 2025),
    }
    assert all(item["national_total_mwh"] is None for item in result["countries"])
    assert result["facility_comparators"][0]["annual_energy_mwh"] == pytest.approx(17_520_000)
    assert all(item["energy_mwh"] is None for item in result["scope"]["unmodeled_categories"])
    assert len(result["scope"]["unmodeled_categories"]) == 6


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda data: data["sources"].append(deepcopy(data["sources"][0])), "unique"),
        (lambda data: data["observations"][0].update(source_id="missing"), "source"),
        (lambda data: data["task_profiles"][0]["placements"][0].update(share=0.8), "sum"),
        (lambda data: data["observations"][0].update(value=-1), "greater than or equal"),
        (lambda data: data["observations"][0].update(value="NaN"), "finite"),
        (lambda data: data["observations"][0].update(unit="MW"), "incompatible"),
        (lambda data: data["observations"][0].update(country_code="SE"), "country/year"),
        (lambda data: data["observations"][0].update(year=2024), "country/year"),
        (lambda data: data["occupations"][0].update(workforce_basis="fte"), "workforce_basis"),
        (lambda data: data["cloud_pue"].update(value=0.99), "greater than or equal"),
    ],
)
def test_collection_rejects_invalid_contracts(mutation, message: str) -> None:
    data = example_data()
    mutation(data)
    with pytest.raises(ValidationError, match=message):
        InputDataset.model_validate(data)


def test_null_is_unknown_not_zero() -> None:
    data = example_data()
    data["observations"][0]["value"] = None
    data["observations"][0]["missing_reason"] = "Suppressed synthetic cell"
    result = evaluate_dataset(InputDataset.model_validate(data))
    row = next(item for item in result["occupations"] if item["country_code"] == "NO")
    assert row["annual_requests"] is None
    assert row["known_total_mwh"] is None
    assert row["status"] == "unknown"
    country = next(item for item in result["countries"] if item["country_code"] == "NO")
    assert country["known_occupational_ai_subtotal_mwh"] is None
    assert country["calculated_occupation_count"] == 0
    assert country["unknown_occupation_count"] == 1


def test_occupation_coverage_rejects_overlapping_cells() -> None:
    data = example_data()
    occupation_id = data["occupations"][0]["id"]
    duplicate = deepcopy(data["occupations"][0])
    duplicate["id"] = "no-second-occupation"
    data["occupations"].append(duplicate)
    profile = deepcopy(data["task_profiles"][0])
    profile["id"] = "no-second-profile"
    profile["occupation_id"] = duplicate["id"]
    data["task_profiles"].append(profile)
    data["occupation_coverage"] = [
        {
            "id": "no-2025-coverage",
            "country_code": "NO",
            "year": 2025,
            "classification": {"id": "7", "name": "STYRK-08", "code": "all"},
            "declared_cell_ids": ["cell-a", "cell-b"],
            "cell_observation_ids": {"cell-a": "no-workers", "cell-b": "no-workers"},
            "occupation_cell_assignments": {
                occupation_id: ["cell-a"],
                duplicate["id"]: ["cell-a"],
            },
            "uncovered_cell_ids": ["cell-b"],
        }
    ]

    with pytest.raises(ValidationError, match="must not overlap"):
        InputDataset.model_validate(data)


def test_occupation_coverage_reports_explicit_uncovered_cells() -> None:
    data = example_data()
    occupation_id = data["occupations"][0]["id"]
    data["observations"][0]["classification"] = {
        "id": "7",
        "name": "STYRK-08",
        "code": "cell-a",
    }
    uncovered = deepcopy(data["observations"][0])
    uncovered["id"] = "no-uncovered-workers"
    uncovered["value"] = 25
    uncovered["classification"]["code"] = "cell-b"
    data["observations"].append(uncovered)
    data["occupation_coverage"] = [
        {
            "id": "no-2025-coverage",
            "country_code": "NO",
            "year": 2025,
            "classification": {"id": "7", "name": "STYRK-08", "code": "all"},
            "declared_cell_ids": ["cell-a", "cell-b"],
            "cell_observation_ids": {
                "cell-a": "no-workers",
                "cell-b": "no-uncovered-workers",
            },
            "occupation_cell_assignments": {occupation_id: ["cell-a"]},
            "uncovered_cell_ids": ["cell-b"],
        }
    ]

    result = evaluate_dataset(InputDataset.model_validate(data))
    country = next(item for item in result["countries"] if item["country_code"] == "NO")
    assert country["occupation_coverage"] == {
        "frame_id": "no-2025-coverage",
        "classification": {
            "id": "7",
            "name": "STYRK-08",
            "code": "all",
            "valid_from": None,
            "based_on": None,
        },
        "declared_cell_count": 2,
        "modeled_cell_count": 1,
        "uncovered_cell_count": 1,
        "uncovered_cell_ids": ["cell-b"],
        "known_modeled_workers": 1000.0,
        "known_declared_workers": 1025.0,
        "complete_declared_workers": 1025.0,
        "scope_status": "incomplete",
    }


def test_result_contains_replayable_input_trace() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    result = evaluate_dataset(dataset)
    reconstructed = InputDataset.model_validate(result["input_trace"])
    assert evaluate_dataset(reconstructed) == result


def test_verified_norway_slice_separates_observation_from_assumptions() -> None:
    dataset, _ = load_dataset(NORWAY_SLICE)
    result = evaluate_dataset(dataset)
    row = result["occupations"][0]
    worker_observation = next(item for item in dataset.observations if item.metric == "workers")

    assert worker_observation.value == 8224
    assert worker_observation.evidence_status == "observed"
    assert worker_observation.classification.code == "2512"
    assert row["annual_requests"] == pytest.approx(7_105_536)
    assert row["cloud_facility_mwh"] == pytest.approx(1.70532864)
    assert "assumption-pue-unused" not in row["source_ids"]
    assert result["countries"][0]["national_total_mwh"] is None
