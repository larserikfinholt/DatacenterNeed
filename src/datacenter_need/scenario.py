"""Scenario evaluation with explicit categories, boundaries, and assumption provenance."""

from __future__ import annotations

from typing import Any

from datacenter_need.model import (
    allocate_hosting,
    inverse_activity_per_denominator,
    matched_value_resource_ratio,
)
from datacenter_need.schemas import (
    AdoptionPreset,
    InputDataset,
    PlacementPreset,
    ScenarioCategory,
    ScenarioConfiguration,
    SourceKind,
)


def _provenance(dataset: InputDataset, source_ids: set[str]) -> dict[str, list[str]]:
    kinds = {item.id: item.source_kind for item in dataset.sources}
    return {
        "assumption_source_ids": sorted(
            source_id
            for source_id in source_ids
            if kinds[source_id] == SourceKind.ASSUMPTION
        ),
        "observed_source_ids": sorted(
            source_id for source_id in source_ids if kinds[source_id] == SourceKind.OBSERVED
        ),
        "reported_source_ids": sorted(
            source_id for source_id in source_ids if kinds[source_id] == SourceKind.REPORTED
        ),
        "synthetic_source_ids": sorted(
            source_id for source_id in source_ids if kinds[source_id] == SourceKind.SYNTHETIC
        ),
    }


def _evaluate_combination(
    dataset: InputDataset,
    scenario: ScenarioConfiguration,
    adoption: AdoptionPreset,
    placement: PlacementPreset,
    occupation_rows: list[dict[str, Any]],
    *,
    demand_multiplier: float = 1,
    cloud_share: float | None = None,
    domestic_hosting_share: float | None = None,
    cloud_pue: float | None = None,
) -> dict[str, Any]:
    selected_cloud_share = placement.cloud_share if cloud_share is None else cloud_share
    selected_hosting_share = (
        placement.domestic_hosting_share
        if domestic_hosting_share is None
        else domestic_hosting_share
    )
    selected_pue = dataset.cloud_pue.value if cloud_pue is None else cloud_pue
    intensities = {item.category: item for item in scenario.energy_intensities}
    activities = {item.category: item for item in adoption.category_activities}
    country_rows = [
        row
        for row in occupation_rows
        if (row["country_code"], row["year"]) == (scenario.country_code, scenario.year)
    ]
    coverage_frame = next(
        (
            frame
            for frame in dataset.occupation_coverage
            if (frame.country_code, frame.year) == (scenario.country_code, scenario.year)
        ),
        None,
    )
    assigned_occupation_ids = (
        None if coverage_frame is None else set(coverage_frame.occupation_cell_assignments)
    )
    relevant_rows = (
        country_rows
        if assigned_occupation_ids is None
        else [row for row in country_rows if row["occupation_id"] in assigned_occupation_ids]
    )
    rows_by_occupation = {row["occupation_id"]: row for row in relevant_rows}
    observations = {item.id: item for item in dataset.observations}
    coverage_complete = coverage_frame is not None
    if coverage_frame is not None:
        coverage_complete = (
            not coverage_frame.uncovered_cell_ids
            and all(
                observations[observation_id].value is not None
                for observation_id in coverage_frame.cell_observation_ids.values()
            )
            and all(
                occupation_id in rows_by_occupation
                and rows_by_occupation[occupation_id]["annual_requests"] is not None
                for occupation_id in coverage_frame.occupation_cell_assignments
            )
        )
    human_activity = (
        None
        if not relevant_rows or any(row["annual_requests"] is None for row in relevant_rows)
        else sum(row["annual_requests"] for row in relevant_rows)
        * adoption.occupation_activity_multiplier
    )
    human_sources = {source_id for row in relevant_rows for source_id in row["source_ids"]}
    category_rows: list[dict[str, Any]] = []
    cloud_category_source_ids: set[str] = set()
    for category in ScenarioCategory:
        intensity = intensities[category]
        common_source_ids = {*adoption.source_ids, *placement.source_ids, *intensity.source_ids}
        if selected_cloud_share > 0 and intensity.cloud_boundary.value == "cloud_it":
            common_source_ids.update(dataset.cloud_pue.source_ids)
        if category == ScenarioCategory.OCCUPATION_HUMAN_INFERENCE:
            pre_rebound_activity_units = human_activity
            missing_reason = (
                None
                if pre_rebound_activity_units is not None
                else "Occupation-linked annual requests are incomplete for the scenario country/year."
            )
            source_ids = {*human_sources, *common_source_ids}
            rebound_activity_units = 0.0
        else:
            activity = activities[category]
            pre_rebound_activity_units = activity.pre_rebound_activity_units
            missing_reason = activity.missing_reason
            source_ids = {*activity.source_ids, *common_source_ids}
            rebound_activity_units = 0.0
            if adoption.rebound is not None and adoption.rebound.category == category:
                rebound_activity_units = (
                    adoption.rebound.baseline_activity_units
                    * adoption.rebound.additional_activity_fraction
                )
                source_ids.update(adoption.rebound.source_ids)
        activity_units = (
            None
            if pre_rebound_activity_units is None
            else pre_rebound_activity_units + rebound_activity_units
        )

        if activity_units is None:
            category_rows.append(
                {
                    "category": category.value,
                    "pre_rebound_activity_units": None,
                    "activity_units": None,
                    "rebound_activity_units": rebound_activity_units,
                    "cloud_it_mwh": None,
                    "cloud_facility_mwh": None,
                    "local_device_mwh": None,
                    "known_total_mwh": None,
                    "status": "unknown",
                    "missing_reason": missing_reason,
                    "provenance": _provenance(dataset, source_ids),
                }
            )
            continue

        scaled_activity = activity_units * demand_multiplier
        cloud_used = selected_cloud_share > 0
        local_used = selected_cloud_share < 1
        missing_reasons = []
        if cloud_used and intensity.cloud_kwh_per_activity_unit is None:
            cloud_kwh = None
            missing_reasons.append(intensity.cloud_missing_reason)
        else:
            cloud_kwh = (
                scaled_activity
                * selected_cloud_share
                * (intensity.cloud_kwh_per_activity_unit or 0)
            )
        if local_used and intensity.local_device_kwh_per_activity_unit is None:
            local_kwh = None
            missing_reasons.append(intensity.local_device_missing_reason)
        else:
            local_kwh = (
                scaled_activity
                * (1 - selected_cloud_share)
                * (intensity.local_device_kwh_per_activity_unit or 0)
            )
        if cloud_kwh is None:
            cloud_it_mwh = cloud_facility_mwh = None
        elif intensity.cloud_boundary.value == "cloud_it":
            cloud_it_mwh = cloud_kwh / 1_000
            cloud_facility_mwh = cloud_it_mwh * selected_pue
        else:
            cloud_it_mwh = None
            cloud_facility_mwh = cloud_kwh / 1_000
        local_device_mwh = None if local_kwh is None else local_kwh / 1_000
        known_total_mwh = (
            None
            if cloud_facility_mwh is None or local_device_mwh is None
            else cloud_facility_mwh + local_device_mwh
        )
        if cloud_used and cloud_facility_mwh is not None:
            cloud_category_source_ids.update(source_ids)
        category_rows.append(
            {
                "category": category.value,
                "pre_rebound_activity_units": pre_rebound_activity_units * demand_multiplier,
                "activity_units": scaled_activity,
                "rebound_activity_units": rebound_activity_units * demand_multiplier,
                "cloud_it_mwh": cloud_it_mwh,
                "cloud_facility_mwh": cloud_facility_mwh,
                "local_device_mwh": local_device_mwh,
                "known_total_mwh": known_total_mwh,
                "status": "known" if known_total_mwh is not None else "unknown",
                "missing_reason": "; ".join(missing_reasons) if missing_reasons else None,
                "provenance": _provenance(dataset, source_ids),
            }
        )

    known_rows = [item for item in category_rows if item["known_total_mwh"] is not None]
    complete = len(known_rows) == len(ScenarioCategory) and coverage_complete
    known_cloud_values = [
        item["cloud_facility_mwh"]
        for item in category_rows
        if item["cloud_facility_mwh"] is not None
    ]
    known_local_values = [
        item["local_device_mwh"]
        for item in category_rows
        if item["local_device_mwh"] is not None
    ]
    known_cloud = sum(known_cloud_values)
    known_local = sum(known_local_values)
    hosting = None
    if complete:
        allocation = allocate_hosting(
            known_cloud,
            selected_hosting_share,
            scenario.hosting.exported_hosting_mwh,
            scenario.hosting.available_domestic_capacity_mwh,
        )
        hosting = {
            **allocation.__dict__,
            "boundary": "cloud_facility",
            "residual_interpretation": "Unallocated capacity; not inferred export or waste.",
            "exported_hosting_missing_reason": scenario.hosting.exported_hosting_missing_reason,
            "available_domestic_capacity_missing_reason": (
                scenario.hosting.available_domestic_capacity_missing_reason
            ),
            "provenance": _provenance(
                dataset,
                {
                    *scenario.hosting.source_ids,
                    *placement.source_ids,
                    *cloud_category_source_ids,
                },
            ),
        }
    return {
        "id": f"{adoption.name.value}__{placement.name.value}",
        "adoption": adoption.name.value,
        "placement": placement.name.value,
        "parameters": {
            "demand_multiplier": demand_multiplier,
            "cloud_share": selected_cloud_share,
            "domestic_hosting_share": selected_hosting_share,
            "cloud_pue": selected_pue,
        },
        "categories": category_rows,
        "known_cloud_facility_subtotal_mwh": known_cloud if known_cloud_values else None,
        "known_local_device_subtotal_mwh": known_local if known_local_values else None,
        "known_national_subtotal_mwh": (
            known_cloud + known_local if known_cloud_values or known_local_values else None
        ),
        "national_total_mwh": known_cloud + known_local if complete else None,
        "scope_status": "complete" if complete else "incomplete",
        "hosting": hosting,
    }


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in (
            "known_cloud_facility_subtotal_mwh",
            "known_local_device_subtotal_mwh",
            "known_national_subtotal_mwh",
            "national_total_mwh",
            "scope_status",
            "hosting",
        )
    }


def evaluate_scenario(
    dataset: InputDataset, occupation_rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Evaluate all preset combinations and deterministic sensitivity cases."""
    scenario = dataset.scenario
    if scenario is None:
        return None
    adoptions = {item.name: item for item in scenario.adoption_presets}
    placements = {item.name: item for item in scenario.placement_presets}
    combinations = [
        _evaluate_combination(dataset, scenario, adoption, placement, occupation_rows)
        for adoption in sorted(scenario.adoption_presets, key=lambda item: item.name.value)
        for placement in sorted(scenario.placement_presets, key=lambda item: item.name.value)
    ]

    sensitivity = scenario.sensitivity
    reference_adoption = adoptions[sensitivity.adoption]
    reference_placement = placements[sensitivity.placement]
    expected_bases = {
        "demand_multiplier": 1,
        "cloud_share": reference_placement.cloud_share,
        "domestic_hosting_share": reference_placement.domestic_hosting_share,
        "cloud_pue": dataset.cloud_pue.value,
    }
    one_at_a_time = []
    for item in sorted(sensitivity.named_ranges, key=lambda value: value.id):
        if item.base != expected_bases[item.parameter]:
            raise ValueError(f"sensitivity base does not match referenced {item.parameter}")
        points = []
        for label in ("low", "base", "high"):
            value = getattr(item, label)
            overrides = {item.parameter: value}
            result = _evaluate_combination(
                dataset,
                scenario,
                reference_adoption,
                reference_placement,
                occupation_rows,
                **overrides,
            )
            points.append({"position": label, "value": value, **_summary(result)})
        one_at_a_time.append(
            {
                "id": item.id,
                "parameter": item.parameter,
                "definition": item.definition,
                "points": points,
                "provenance": _provenance(dataset, set(item.source_ids)),
            }
        )

    joint_stress_cases = []
    for item in sorted(sensitivity.joint_stress_cases, key=lambda value: value.id):
        result = _evaluate_combination(
            dataset,
            scenario,
            reference_adoption,
            reference_placement,
            occupation_rows,
            demand_multiplier=item.demand_multiplier,
            cloud_share=item.cloud_share,
            domestic_hosting_share=item.domestic_hosting_share,
            cloud_pue=item.cloud_pue,
        )
        joint_stress_cases.append(
            {
                "id": item.id,
                "definition": item.definition,
                "parameters": {
                    "demand_multiplier": item.demand_multiplier,
                    "cloud_share": item.cloud_share,
                    "domestic_hosting_share": item.domestic_hosting_share,
                    "cloud_pue": item.cloud_pue,
                },
                **_summary(result),
                "provenance": _provenance(dataset, set(item.source_ids)),
            }
        )

    inverse_allocations = []
    for item in sorted(scenario.inverse_allocations, key=lambda value: value.id):
        inverse_allocations.append(
            {
                "id": item.id,
                "country_code": item.country_code,
                "year": item.year,
                "activity_units_per_denominator": inverse_activity_per_denominator(
                    item.facility_capacity_mw,
                    item.load_factor,
                    item.allocation_share,
                    item.kwh_per_activity_unit,
                    item.denominator_value,
                    item.year,
                    energy_boundary=item.energy_boundary.value,
                    cloud_pue=dataset.cloud_pue.value,
                ),
                "facility_capacity_mw": item.facility_capacity_mw,
                "load_factor": item.load_factor,
                "allocation_share": item.allocation_share,
                "kwh_per_activity_unit": item.kwh_per_activity_unit,
                "activity_unit": item.activity_unit,
                "denominator_value": item.denominator_value,
                "denominator_unit": item.denominator_unit,
                "denominator_definition": item.denominator_definition,
                "energy_boundary": item.energy_boundary.value,
                "cloud_pue_applied": (
                    dataset.cloud_pue.value
                    if item.energy_boundary.value == "cloud_it"
                    else None
                ),
                "workload_scope": item.workload_scope,
                "provenance": _provenance(dataset, set(item.source_ids)),
            }
        )

    value_resource_ratios = []
    for item in sorted(scenario.value_resource_ratios, key=lambda value: value.id):
        value_resource_ratios.append(
            {
                "id": item.id,
                "ratio": matched_value_resource_ratio(
                    item.value.value,
                    item.resource.value,
                    value_country_code=item.value.country_code,
                    resource_country_code=item.resource.country_code,
                    value_year=item.value.year,
                    resource_year=item.resource.year,
                    value_boundary=item.value.boundary,
                    resource_boundary=item.resource.boundary,
                ),
                "ratio_unit": f"{item.value.unit}/{item.resource.unit}",
                "country_code": item.value.country_code,
                "year": item.value.year,
                "boundary": item.value.boundary,
                "value_definition": item.value.definition,
                "resource_definition": item.resource.definition,
                "provenance": _provenance(
                    dataset, {*item.value.source_ids, *item.resource.source_ids}
                ),
            }
        )

    return {
        "country_code": scenario.country_code,
        "year": scenario.year,
        "combinations": combinations,
        "sensitivity": {
            "reference_adoption": sensitivity.adoption.value,
            "reference_placement": sensitivity.placement.value,
            "one_at_a_time": one_at_a_time,
            "joint_stress_cases": joint_stress_cases,
        },
        "inverse_allocations": inverse_allocations,
        "value_resource_ratios": value_resource_ratios,
    }