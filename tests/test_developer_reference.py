import pytest

from datacenter_need.developer_reference import (
    AcceleratorProfile,
    CapacityStatus,
    ModelProfile,
    PowerProfile,
    ServingProfile,
    allocate_workday_energy,
    node_it_power_w,
    power_from_profiles,
    screen_capacity,
    validate_memory_compatibility,
)


def test_node_it_power_baseline() -> None:
    assert node_it_power_w(8, 100, 600, 0.65, 1_000) == pytest.approx(4_400)


@pytest.mark.parametrize(
    ("utilization", "expected"),
    [(0.25, 2_800), (0.65, 4_400), (0.90, 5_400)],
)
def test_node_it_power_fixture_rows(utilization: float, expected: float) -> None:
    assert node_it_power_w(8, 100, 600, utilization, 1_000) == pytest.approx(expected)


def test_power_and_energy_keep_occupancy_and_pue_separate() -> None:
    accelerator = AcceleratorProfile("H100-SXM", "SXM", 8, 80, "NVLink", 8, 1, "engine")
    power = PowerProfile(100, 600, 1_000)
    node_power = power_from_profiles(accelerator, power, 0.65)
    result = allocate_workday_energy(node_power, 20, 8, actual_occupancy=1, pue=1.5)

    assert result.node_it_w == pytest.approx(4_400)
    assert result.watts_per_active_developer == pytest.approx(220)
    assert result.workday_kwh_per_active_developer == pytest.approx(1.76)
    assert result.facility_node_w == pytest.approx(6_600)

    occupied = allocate_workday_energy(node_power, 20, 8, actual_occupancy=0.5, pue=1.5)
    assert occupied.watts_per_active_developer == pytest.approx(220)


def test_zero_users_preserves_idle_energy_and_null_per_user_result() -> None:
    result = allocate_workday_energy(4_400, 0, 8, off_hours_hours=16)

    assert result.watts_per_active_developer is None
    assert result.workday_kwh_per_active_developer is None
    assert result.off_hours_kwh == pytest.approx(70.4)


def test_capacity_unknown_zero_demand_and_overload_are_distinct() -> None:
    unknown = screen_capacity(20, 1, 0.8, 1.25, None, per_stream_output_tokens_per_second=40)
    assert unknown.status is CapacityStatus.UNKNOWN
    assert unknown.supported_developers is None

    no_demand = screen_capacity(
        20, 0, 0.8, 1.25, 0, per_stream_output_tokens_per_second=40
    )
    assert no_demand.status is CapacityStatus.CONDITIONAL_PASS
    assert no_demand.supported_developers is None
    assert no_demand.limiting_constraint == "no inference demand"

    overloaded = screen_capacity(
        20,
        2,
        0.8,
        1.25,
        20,
        aggregate_output_tokens_per_second=800,
        per_stream_output_tokens_per_second=40,
    )
    assert overloaded.status is CapacityStatus.OVERLOAD
    assert overloaded.supported_developers == 10
    assert overloaded.required_output_tokens_per_second == pytest.approx(1_600)


def test_capacity_decode_check_keeps_input_and_output_separate() -> None:
    result = screen_capacity(
        20,
        1,
        0.8,
        1.25,
        20,
        aggregate_output_tokens_per_second=800,
        per_stream_output_tokens_per_second=40,
    )

    assert result.status is CapacityStatus.CONDITIONAL_PASS
    assert result.required_output_tokens_per_second == pytest.approx(800)


def test_memory_limited_serving_rejects_known_overflow() -> None:
    model = ModelProfile("model", "rev", "FP8", 70, "assumption")
    accelerator = AcceleratorProfile("GPU", "form", 1, 80, "link", 1, 1, "engine")
    serving = ServingProfile(None, None, None, 8, 4, True)

    with pytest.raises(ValueError, match="exceed accelerator memory"):
        validate_memory_compatibility(model, accelerator, serving)


@pytest.mark.parametrize(
    "arguments",
    [
        (8, 100, 600, -0.1, 1_000),
        (8, 100, 600, 1.1, 1_000),
        (8, float("nan"), 600, 0.5, 1_000),
    ],
)
def test_power_rejects_invalid_values(arguments: tuple[object, ...]) -> None:
    with pytest.raises(ValueError):
        node_it_power_w(*arguments)  # type: ignore[arg-type]