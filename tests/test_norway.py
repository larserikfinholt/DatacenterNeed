from pathlib import Path

from datacenter_need.pipeline import evaluate_dataset, load_dataset

NORWAY = Path("data/norway/norway-2025.yaml")


def test_norway_coverage_reconciles_without_invented_demand_or_capacity() -> None:
    dataset, _ = load_dataset(NORWAY)
    result = evaluate_dataset(dataset)
    country = result["countries"][0]
    coverage = country["occupation_coverage"]

    assert len(result["occupations"]) == 9
    assert all(item["status"] == "unknown" for item in result["occupations"])
    assert coverage["known_modeled_workers"] == 2_830_506
    assert coverage["complete_declared_workers"] == 2_839_036
    assert coverage["uncovered_cell_ids"] == ["0b"]
    assert country["known_occupational_ai_subtotal_mwh"] is None
    assert country["national_total_mwh"] is None
    assert {(item["metric"], item["value"], item["unit"]) for item in result["national_electricity"]} == {
        ("electricity_production", 161_793.0, "GWh"),
        ("electricity_consumption", 130_125.0, "GWh"),
    }
    assert {item["id"] for item in result["projects"]} == {
        "no-lefdal-mine",
        "no-svg-rennesoy",
    }
    assert result["project_totals"] == []