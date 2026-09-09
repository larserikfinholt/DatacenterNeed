"""Pure calculation functions with explicit energy-accounting boundaries."""

from __future__ import annotations

import calendar
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pint import UnitRegistry

_UNITS = UnitRegistry()


@dataclass(frozen=True)
class EnergyBenchmark:
    """Request-level energy benchmark in kWh at one explicit boundary."""

    id: str
    kwh_per_request: float
    boundary: Literal["cloud_it", "cloud_facility", "local_device"]


@dataclass(frozen=True)
class ModelPlacement:
    """Named model/placement allocation as a fraction of all requests."""

    name: str
    share: float
    benchmark: EnergyBenchmark


@dataclass(frozen=True)
class InferenceEnergy:
    """Energy subtotals in kWh; cloud facility includes PUE exactly once."""

    cloud_it_kwh: float
    cloud_facility_kwh: float
    local_device_kwh: float
    total_kwh: float


@dataclass(frozen=True)
class HostingAllocation:
    """Cloud-facility energy allocation with imports and exports kept distinct."""

    domestic_consumption_mwh: float
    domestically_hosted_mwh: float
    imported_mwh: float
    exported_hosting_mwh: float | None
    allocated_domestic_capacity_mwh: float | None
    residual_capacity_mwh: float | None
    capacity_gap_mwh: float | None


def _finite_nonnegative(name: str, value: float) -> float:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def _fraction(name: str, value: float) -> float:
    _finite_nonnegative(name, value)
    if value > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def hours_in_year(year: int) -> int:
    """Return calendar hours for a Gregorian year."""
    return (366 if calendar.isleap(year) else 365) * 24


def annual_requests(
    workers: float,
    annual_hours: float,
    digital_fraction: float,
    ai_fraction: float,
    requests_per_ai_hour: float,
) -> float:
    """Return requests/year; AI frequency is conditional on AI-active digital hours."""
    return (
        _finite_nonnegative("workers", workers)
        * _finite_nonnegative("annual_hours", annual_hours)
        * _fraction("digital_fraction", digital_fraction)
        * _fraction("ai_fraction", ai_fraction)
        * _finite_nonnegative("requests_per_ai_hour", requests_per_ai_hour)
    )


def inference_energy(
    requests: float,
    placements: Sequence[ModelPlacement],
    cloud_pue: float,
) -> InferenceEnergy:
    """Allocate requests and return kWh by cloud IT, cloud facility, and local boundary."""
    _finite_nonnegative("requests", requests)
    if not math.isfinite(cloud_pue) or cloud_pue < 1:
        raise ValueError("cloud_pue must be finite and at least 1")
    if not placements:
        raise ValueError("placements must not be empty")

    share_total = 0.0
    cloud_it_kwh = 0.0
    cloud_facility_kwh = 0.0
    local_device_kwh = 0.0
    for placement in placements:
        share_total += _fraction(f"share for {placement.name}", placement.share)
        energy = requests * placement.share * _finite_nonnegative(
            f"kwh_per_request for {placement.name}", placement.benchmark.kwh_per_request
        )
        if placement.benchmark.boundary == "cloud_it":
            cloud_it_kwh += energy
            cloud_facility_kwh += energy * cloud_pue
        elif placement.benchmark.boundary == "cloud_facility":
            cloud_facility_kwh += energy
        elif placement.benchmark.boundary == "local_device":
            local_device_kwh += energy
        else:
            raise ValueError(f"unknown energy boundary: {placement.benchmark.boundary}")

    if not math.isclose(share_total, 1.0, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("placement shares must sum to 1")
    return InferenceEnergy(
        cloud_it_kwh=cloud_it_kwh,
        cloud_facility_kwh=cloud_facility_kwh,
        local_device_kwh=local_device_kwh,
        total_kwh=cloud_facility_kwh + local_device_kwh,
    )


def annual_average_load_mw(energy_mwh: float, year: int) -> float:
    """Convert annual energy in MWh to calendar-year average load in MW."""
    energy = _finite_nonnegative("energy_mwh", energy_mwh) * _UNITS.megawatt_hour
    return (energy / (hours_in_year(year) * _UNITS.hour)).to(_UNITS.megawatt).magnitude


def facility_energy_mwh(capacity_mw: float, load_factor: float, year: int) -> float:
    """Convert facility capacity in MW and load factor to annual energy in MWh."""
    capacity = _finite_nonnegative("capacity_mw", capacity_mw) * _UNITS.megawatt
    factor = _fraction("load_factor", load_factor)
    return (capacity * factor * hours_in_year(year) * _UNITS.hour).to(
        _UNITS.megawatt_hour
    ).magnitude


def equivalent_capacity_mw(energy_mwh: float, load_factor: float, year: int) -> float:
    """Return equivalent facility MW; load factor is required and must be positive."""
    if load_factor == 0:
        raise ValueError("load_factor must be greater than 0")
    return annual_average_load_mw(energy_mwh, year) / _fraction("load_factor", load_factor)


def inverse_requests_per_worker(
    facility_capacity_mw: float,
    load_factor: float,
    cloud_pue: float,
    cloud_it_kwh_per_request: float,
    cloud_share: float,
    workers: float,
    year: int,
) -> float:
    """Return hypothetical AI-only annual requests/worker from cloud facility capacity."""
    if cloud_pue < 1 or not math.isfinite(cloud_pue):
        raise ValueError("cloud_pue must be finite and at least 1")
    denominator = (
        _finite_nonnegative("cloud_it_kwh_per_request", cloud_it_kwh_per_request)
        * _fraction("cloud_share", cloud_share)
        * _finite_nonnegative("workers", workers)
        * cloud_pue
    )
    if denominator == 0:
        raise ValueError("inverse denominator must be greater than 0")
    facility_kwh = facility_energy_mwh(facility_capacity_mw, load_factor, year) * 1_000
    return facility_kwh / denominator


def allocate_hosting(
    domestic_consumption_mwh: float,
    domestic_hosting_share: float,
    exported_hosting_mwh: float | None,
    available_domestic_capacity_mwh: float | None = None,
) -> HostingAllocation:
    """Allocate consumption and capacity without treating residual capacity as exports."""
    consumption = _finite_nonnegative("domestic_consumption_mwh", domestic_consumption_mwh)
    share = _fraction("domestic_hosting_share", domestic_hosting_share)
    exports = (
        None
        if exported_hosting_mwh is None
        else _finite_nonnegative("exported_hosting_mwh", exported_hosting_mwh)
    )
    domestically_hosted = consumption * share
    imported = consumption - domestically_hosted
    if available_domestic_capacity_mwh is None or exports is None:
        allocated_capacity = residual = gap = None
    else:
        available = _finite_nonnegative(
            "available_domestic_capacity_mwh", available_domestic_capacity_mwh
        )
        allocated_capacity = domestically_hosted + exports
        residual = max(available - allocated_capacity, 0)
        gap = max(allocated_capacity - available, 0)
    return HostingAllocation(
        domestic_consumption_mwh=consumption,
        domestically_hosted_mwh=domestically_hosted,
        imported_mwh=imported,
        exported_hosting_mwh=exports,
        allocated_domestic_capacity_mwh=allocated_capacity,
        residual_capacity_mwh=residual,
        capacity_gap_mwh=gap,
    )


def inverse_activity_per_denominator(
    facility_capacity_mw: float,
    load_factor: float,
    allocation_share: float,
    kwh_per_activity_unit: float,
    denominator: float,
    year: int,
    *,
    energy_boundary: Literal["cloud_it", "cloud_facility"],
    cloud_pue: float,
) -> float:
    """Return allocated activity units per explicit denominator at a stated boundary."""
    pue_multiplier = 1.0
    if energy_boundary == "cloud_it":
        if not math.isfinite(cloud_pue) or cloud_pue < 1:
            raise ValueError("cloud_pue must be finite and at least 1")
        pue_multiplier = cloud_pue
    elif energy_boundary != "cloud_facility":
        raise ValueError("inverse energy boundary must be cloud_it or cloud_facility")
    divisor = (
        _finite_nonnegative("kwh_per_activity_unit", kwh_per_activity_unit)
        * _finite_nonnegative("denominator", denominator)
        * pue_multiplier
    )
    if divisor == 0:
        raise ValueError("inverse denominator must be greater than 0")
    allocated_kwh = (
        facility_energy_mwh(facility_capacity_mw, load_factor, year)
        * 1_000
        * _fraction("allocation_share", allocation_share)
    )
    return allocated_kwh / divisor


def matched_value_resource_ratio(
    value: float,
    resource: float,
    *,
    value_country_code: str,
    resource_country_code: str,
    value_year: int,
    resource_year: int,
    value_boundary: str,
    resource_boundary: str,
) -> float:
    """Return one value/resource ratio only when country, year, and boundary match."""
    if value_country_code != resource_country_code or value_year != resource_year:
        raise ValueError("value and resource country/year must match")
    if value_boundary != resource_boundary:
        raise ValueError("value and resource boundaries must match")
    denominator = _finite_nonnegative("resource", resource)
    if denominator == 0:
        raise ValueError("resource denominator must be greater than 0")
    return _finite_nonnegative("value", value) / denominator
