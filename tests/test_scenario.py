import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from datacenter_need.pipeline import build_dataset, evaluate_dataset, load_dataset
from datacenter_need.schemas import InputDataset

EXAMPLE = Path("data/examples/synthetic.yaml")
NORWAY = Path("data/norway/norway-2025.yaml")


def example_data() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def test_all_nine_scenarios_keep_categories_and_hosting_conservation() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    scenario = evaluate_dataset(dataset)["scenario"]

    assert len(scenario["combinations"]) == 9
    assert {item["id"] for item in scenario["combinations"]} == {
        f"{adoption}__{placement}"
        for adoption in ("conservative", "moderate", "high")
        for placement in ("cloud-heavy", "hybrid", "local-heavy")
    }
    moderate = next(item for item in scenario["combinations"] if item["id"] == "moderate__hybrid")
    assert len(moderate["categories"]) == 7
    assert moderate["national_total_mwh"] is not None
    hosting = moderate["hosting"]
    assert hosting["domestically_hosted_mwh"] + hosting["imported_mwh"] == pytest.approx(
        hosting["domestic_consumption_mwh"]
    )
    assert hosting["exported_hosting_mwh"] == 100
    assert hosting["residual_interpretation"].startswith("Unallocated capacity")


def test_background_rebound_is_additive_against_documented_baseline() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    scenario = evaluate_dataset(dataset)["scenario"]
    high = next(item for item in scenario["combinations"] if item["id"] == "high__hybrid")
    background = next(
        item
        for item in high["categories"]
        if item["category"] == "autonomous_background_inference"
    )

    assert background["activity_units"] == pytest.approx(7_000_000)
    assert background["pre_rebound_activity_units"] == pytest.approx(5_000_000)
    assert background["rebound_activity_units"] == pytest.approx(2_000_000)
    assert background["provenance"]["observed_source_ids"] == []
    assert background["provenance"]["reported_source_ids"] == []
    assert background["provenance"]["assumption_source_ids"] == [
        "assumption-energy",
        "assumption-scenario",
    ]


def test_scenario_applies_pue_once_and_not_to_facility_metered_energy() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    scenario = evaluate_dataset(dataset)["scenario"]
    moderate = next(item for item in scenario["combinations"] if item["id"] == "moderate__hybrid")
    categories = {item["category"]: item for item in moderate["categories"]}

    human = categories["occupation_human_inference"]
    assert human["cloud_it_mwh"] == pytest.approx(0.384)
    assert human["cloud_facility_mwh"] == pytest.approx(0.4608)
    training = categories["foundation_training"]
    assert training["cloud_it_mwh"] is None
    assert training["cloud_facility_mwh"] == pytest.approx(600)


def test_sensitivity_stress_inverse_and_matched_ratio_outputs() -> None:
    dataset, _ = load_dataset(EXAMPLE)
    scenario = evaluate_dataset(dataset)["scenario"]

    assert len(scenario["sensitivity"]["one_at_a_time"]) == 4
    demand = next(
        item
        for item in scenario["sensitivity"]["one_at_a_time"]
        if item["parameter"] == "demand_multiplier"
    )
    assert [point["position"] for point in demand["points"]] == ["low", "base", "high"]
    assert demand["points"][2]["national_total_mwh"] > demand["points"][1]["national_total_mwh"]
    assert scenario["sensitivity"]["joint_stress_cases"][0]["parameters"]["cloud_share"] == 0.95
    inverse = scenario["inverse_allocations"][0]
    assert inverse["activity_units_per_denominator"] > 0
    assert inverse["facility_capacity_mw"] == 1
    assert inverse["load_factor"] == 1
    assert inverse["allocation_share"] == 0.5
    assert inverse["kwh_per_activity_unit"] == 0.002
    assert inverse["denominator_value"] == 1000
    assert inverse["denominator_unit"] == "synthetic_workers"
    assert inverse["denominator_definition"] == "Explicit synthetic worker denominator"
    assert inverse["cloud_pue_applied"] == 1.2
    assert inverse["workload_scope"] == "ai_only"
    assert scenario["value_resource_ratios"][0]["ratio"] == pytest.approx(10)
    assert scenario["value_resource_ratios"][0]["ratio_unit"] == "permanent_jobs/facility_MW"


def test_unknown_category_prevents_complete_national_total_and_hosting_allocation() -> None:
    data = example_data()
    activity = data["scenario"]["adoption_presets"][0]["category_activities"][0]
    activity["pre_rebound_activity_units"] = None
    activity["missing_reason"] = "Synthetic gap"
    result = evaluate_dataset(InputDataset.model_validate(data))["scenario"]
    conservative = next(
        item for item in result["combinations"] if item["id"] == "conservative__cloud-heavy"
    )

    assert conservative["known_national_subtotal_mwh"] is not None
    assert conservative["national_total_mwh"] is None
    assert conservative["scope_status"] == "incomplete"
    assert conservative["hosting"] is None


def test_incomplete_or_unknown_occupation_coverage_blocks_complete_scenario() -> None:
    missing_frame = example_data()
    missing_frame["occupation_coverage"] = []
    result = evaluate_dataset(InputDataset.model_validate(missing_frame))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")

    assert moderate["known_national_subtotal_mwh"] is not None
    assert moderate["national_total_mwh"] is None
    assert moderate["scope_status"] == "incomplete"
    assert moderate["hosting"] is None

    uncovered = example_data()
    frame = uncovered["occupation_coverage"][0]
    frame["occupation_cell_assignments"] = {}
    frame["uncovered_cell_ids"] = ["synthetic-all"]
    result = evaluate_dataset(InputDataset.model_validate(uncovered))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")

    assert moderate["known_national_subtotal_mwh"] is not None
    assert moderate["national_total_mwh"] is None
    assert moderate["scope_status"] == "incomplete"
    assert moderate["hosting"] is None

    unknown_request = example_data()
    profile = unknown_request["task_profiles"][0]
    profile.update(
        digital_fraction=None,
        ai_fraction=None,
        requests_per_ai_hour=None,
        placements=[],
        missing_reason="Synthetic request evidence gap",
    )
    result = evaluate_dataset(InputDataset.model_validate(unknown_request))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")

    assert moderate["known_national_subtotal_mwh"] is not None
    assert moderate["national_total_mwh"] is None
    assert moderate["hosting"] is None


def test_unknown_used_intensity_propagates_while_preserving_known_component() -> None:
    data = example_data()
    intensity = data["scenario"]["energy_intensities"][0]
    intensity["cloud_kwh_per_activity_unit"] = None
    intensity["cloud_missing_reason"] = "No cloud coefficient"
    result = evaluate_dataset(InputDataset.model_validate(data))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")
    human = next(
        item
        for item in moderate["categories"]
        if item["category"] == "occupation_human_inference"
    )

    assert human["cloud_facility_mwh"] is None
    assert human["local_device_mwh"] is not None
    assert human["known_total_mwh"] is None
    assert human["missing_reason"] == "No cloud coefficient"
    assert moderate["known_local_device_subtotal_mwh"] is not None
    assert moderate["national_total_mwh"] is None
    assert moderate["hosting"] is None


def test_unknown_export_or_capacity_preserves_consumption_allocation() -> None:
    data = example_data()
    hosting_input = data["scenario"]["hosting"]
    hosting_input["exported_hosting_mwh"] = None
    hosting_input["exported_hosting_missing_reason"] = "No export evidence"
    result = evaluate_dataset(InputDataset.model_validate(data))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")
    hosting = moderate["hosting"]

    assert hosting["domestically_hosted_mwh"] + hosting["imported_mwh"] == pytest.approx(
        hosting["domestic_consumption_mwh"]
    )
    assert hosting["exported_hosting_mwh"] is None
    assert hosting["allocated_domestic_capacity_mwh"] is None
    assert hosting["residual_capacity_mwh"] is None
    assert hosting["capacity_gap_mwh"] is None
    assert hosting["exported_hosting_missing_reason"] == "No export evidence"

    data = example_data()
    hosting_input = data["scenario"]["hosting"]
    hosting_input["available_domestic_capacity_mwh"] = None
    hosting_input["available_domestic_capacity_missing_reason"] = "No capacity evidence"
    result = evaluate_dataset(InputDataset.model_validate(data))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")

    assert moderate["hosting"]["domestically_hosted_mwh"] is not None
    assert moderate["hosting"]["residual_capacity_mwh"] is None
    assert moderate["hosting"]["capacity_gap_mwh"] is None


def test_provenance_separates_observed_reported_and_cloud_contributors() -> None:
    data = example_data()
    reported = deepcopy(data["sources"][2])
    reported.update(id="reported-energy", source_kind="reported")
    observed = deepcopy(data["sources"][3])
    observed.update(id="observed-hosting", source_kind="observed")
    data["sources"].extend([reported, observed])
    data["scenario"]["energy_intensities"][0]["source_ids"] = ["reported-energy"]
    data["scenario"]["hosting"]["source_ids"] = ["observed-hosting"]
    result = evaluate_dataset(InputDataset.model_validate(data))["scenario"]
    moderate = next(item for item in result["combinations"] if item["id"] == "moderate__hybrid")
    provenance = moderate["hosting"]["provenance"]

    assert provenance["observed_source_ids"] == ["observed-hosting"]
    assert provenance["reported_source_ids"] == ["reported-energy"]
    assert "observation_source_ids" not in provenance


def test_scenario_contract_rejects_invalid_shares_references_and_boundaries() -> None:
    invalid_share = example_data()
    invalid_share["scenario"]["placement_presets"][0]["cloud_share"] = 1.1
    with pytest.raises(ValidationError, match="less than or equal"):
        InputDataset.model_validate(invalid_share)

    invalid_source = example_data()
    source = next(item for item in invalid_source["sources"] if item["id"] == "assumption-scenario")
    source["source_kind"] = "observed"
    with pytest.raises(ValidationError, match="assumption or synthetic"):
        InputDataset.model_validate(invalid_source)

    mismatched_boundary = example_data()
    ratio = mismatched_boundary["scenario"]["value_resource_ratios"][0]
    ratio["resource"]["boundary"] = "national"
    with pytest.raises(ValidationError, match="boundaries must match"):
        InputDataset.model_validate(mismatched_boundary)


def test_sensitivity_base_must_match_named_reference() -> None:
    data = example_data()
    data["scenario"]["sensitivity"]["named_ranges"][0]["base"] = 2
    dataset = InputDataset.model_validate(data)
    with pytest.raises(ValueError, match="base does not match"):
        evaluate_dataset(dataset)


def test_norway_dataset_has_no_invented_scenario() -> None:
    dataset, _ = load_dataset(NORWAY)
    assert evaluate_dataset(dataset)["scenario"] is None


def test_build_emits_scenario_output_and_replayable_trace(tmp_path: Path) -> None:
    output = tmp_path / "build"
    build_dataset(EXAMPLE, output)
    result = json.loads((output / "result.json").read_text(encoding="utf-8"))

    assert len(result["scenario"]["combinations"]) == 9
    reconstructed = InputDataset.model_validate(result["input_trace"])
    assert evaluate_dataset(reconstructed)["scenario"] == result["scenario"]