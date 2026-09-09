import math

import pytest

from datacenter_need.model import (
    EnergyBenchmark,
    ModelPlacement,
    allocate_hosting,
    annual_average_load_mw,
    annual_requests,
    equivalent_capacity_mw,
    facility_energy_mwh,
    inference_energy,
    inverse_activity_per_denominator,
    inverse_requests_per_worker,
    matched_value_resource_ratio,
)


def test_calendar_year_energy_conversions() -> None:
    assert facility_energy_mwh(1, 1, 2025) == pytest.approx(8_760)
    assert facility_energy_mwh(2_000, 1, 2025) == pytest.approx(17_520_000)
    assert facility_energy_mwh(2_000, 1, 2024) == pytest.approx(17_568_000)
    assert annual_average_load_mw(8_760, 2025) == pytest.approx(1)
    assert equivalent_capacity_mw(8_760, 1, 2025) == pytest.approx(1)


def test_requests_zero_scaling_and_invalid_values() -> None:
    assert annual_requests(0, 1_700, 0.8, 0.2, 5) == 0
    baseline = annual_requests(100, 1_700, 0.8, 0.2, 5)
    assert annual_requests(100, 1_700, 0.8, 0.2, 10) == pytest.approx(2 * baseline)
    for invalid in (-0.1, math.nan, math.inf):
        with pytest.raises(ValueError):
            annual_requests(100, 1_700, invalid, 0.2, 5)
    with pytest.raises(ValueError):
        annual_requests(100, 1_700, 1.1, 0.2, 5)


def test_placement_conservation_and_pue_applied_once() -> None:
    placements = [
        ModelPlacement("cloud-it", 0.4, EnergyBenchmark("cloud-it", 1, "cloud_it")),
        ModelPlacement(
            "cloud-facility", 0.3, EnergyBenchmark("cloud-facility", 2, "cloud_facility")
        ),
        ModelPlacement("local", 0.3, EnergyBenchmark("local", 3, "local_device")),
    ]
    result = inference_energy(100, placements, cloud_pue=1.5)
    assert result.cloud_it_kwh == pytest.approx(40)
    assert result.cloud_facility_kwh == pytest.approx(120)
    assert result.local_device_kwh == pytest.approx(90)
    assert result.total_kwh == pytest.approx(210)

    with pytest.raises(ValueError, match="sum to 1"):
        inference_energy(100, placements[:-1], cloud_pue=1.5)
    invalid_boundary = ModelPlacement(
        "ambiguous", 1, EnergyBenchmark("gpu-only", 1, "gpu_only")  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="unknown energy boundary"):
        inference_energy(100, [invalid_boundary], cloud_pue=1.5)


def test_inverse_round_trip_and_zero_denominators() -> None:
    requests_per_worker = 1_000
    workers = 100
    cloud_share = 0.8
    energy_per_request = 0.002
    pue = 1.25
    facility_mwh = requests_per_worker * workers * cloud_share * energy_per_request * pue / 1_000
    capacity_mw = equivalent_capacity_mw(facility_mwh, 0.9, 2025)

    assert inverse_requests_per_worker(
        capacity_mw, 0.9, pue, energy_per_request, cloud_share, workers, 2025
    ) == pytest.approx(requests_per_worker)

    for kwargs in (
        {"workers": 0},
        {"cloud_share": 0},
        {"cloud_it_kwh_per_request": 0},
    ):
        values = {
            "facility_capacity_mw": 1,
            "load_factor": 1,
            "cloud_pue": 1.2,
            "cloud_it_kwh_per_request": 0.002,
            "cloud_share": 0.8,
            "workers": 100,
            "year": 2025,
        }
        values.update(kwargs)
        with pytest.raises(ValueError, match="denominator"):
            inverse_requests_per_worker(**values)

    with pytest.raises(ValueError, match="greater than 0"):
        equivalent_capacity_mw(100, 0, 2025)


def test_hosting_conservation_and_residual_capacity_is_unallocated() -> None:
    result = allocate_hosting(100, 0.7, 20, available_domestic_capacity_mwh=120)
    assert result.domestically_hosted_mwh + result.imported_mwh == pytest.approx(100)
    assert result.exported_hosting_mwh == 20
    assert result.allocated_domestic_capacity_mwh == pytest.approx(90)
    assert result.residual_capacity_mwh == pytest.approx(30)
    assert result.capacity_gap_mwh == 0

    constrained = allocate_hosting(100, 0.9, 40, available_domestic_capacity_mwh=100)
    assert constrained.residual_capacity_mwh == 0
    assert constrained.capacity_gap_mwh == pytest.approx(30)


def test_inverse_allocation_applies_pue_only_to_it_boundary() -> None:
    facility = inverse_activity_per_denominator(
        1,
        1,
        0.5,
        1,
        100,
        2025,
        energy_boundary="cloud_facility",
        cloud_pue=1.5,
    )
    cloud_it = inverse_activity_per_denominator(
        1,
        1,
        0.5,
        1,
        100,
        2025,
        energy_boundary="cloud_it",
        cloud_pue=1.5,
    )
    assert facility == pytest.approx(43_800)
    assert cloud_it == pytest.approx(facility / 1.5)


def test_value_resource_ratio_requires_matched_scope() -> None:
    assert matched_value_resource_ratio(
        50,
        10,
        value_country_code="NO",
        resource_country_code="NO",
        value_year=2025,
        resource_year=2025,
        value_boundary="project-a",
        resource_boundary="project-a",
    ) == pytest.approx(5)
    with pytest.raises(ValueError, match="boundaries must match"):
        matched_value_resource_ratio(
            50,
            10,
            value_country_code="NO",
            resource_country_code="NO",
            value_year=2025,
            resource_year=2025,
            value_boundary="project-a",
            resource_boundary="national",
        )