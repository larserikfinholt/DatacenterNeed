from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from datacenter_need.pipeline import evaluate_dataset, load_dataset
from datacenter_need.schemas import InputDataset

EXAMPLE = Path("data/examples/synthetic.yaml")


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


def test_result_contains_replayable_input_trace() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    result = evaluate_dataset(dataset)
    reconstructed = InputDataset.model_validate(result["input_trace"])
    assert evaluate_dataset(reconstructed) == result
