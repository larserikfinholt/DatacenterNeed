"""Validated input contracts for transparent, provenance-linked calculations."""

from __future__ import annotations

import math
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
FiniteNonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
FinitePositive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceKind(StrEnum):
    OBSERVED = "observed"
    REPORTED = "reported"
    ASSUMPTION = "assumption"
    SYNTHETIC = "synthetic"


class EvidenceStatus(StrEnum):
    OBSERVED = "observed"
    REPORTED = "reported"
    ASSUMED = "assumed"
    SYNTHETIC = "synthetic"


class Metric(StrEnum):
    WORKERS = "workers"
    ANNUAL_HOURS = "annual_hours"
    CONNECTION_CAPACITY = "connection_capacity"
    INSTALLED_IT_CAPACITY = "installed_it_capacity"
    FACILITY_CAPACITY = "facility_capacity"
    AVERAGE_LOAD = "average_load"
    PEAK_DEMAND = "peak_demand"
    ELECTRICITY_PRODUCTION = "electricity_production"
    ELECTRICITY_CONSUMPTION = "electricity_consumption"


class Unit(StrEnum):
    PEOPLE = "people"
    FTE = "fte"
    HOURS_PER_WORKER_YEAR = "hour_per_worker_year"
    HOURS_PER_FTE_YEAR = "hour_per_fte_year"
    MW = "MW"
    MWH = "MWh"
    GWH = "GWh"


class Boundary(StrEnum):
    EMPLOYMENT_HEADCOUNT = "employment_headcount"
    EMPLOYMENT_FTE = "employment_fte"
    HOURS_PER_WORKER = "annual_hours_per_worker"
    HOURS_PER_FTE = "annual_hours_per_fte"
    GRID_CONNECTION = "grid_connection"
    IT_EQUIPMENT = "it_equipment"
    CLOUD_FACILITY = "cloud_facility"
    METERED_AVERAGE_LOAD = "metered_average_load"
    PEAK_DEMAND = "peak_demand"
    NATIONAL_PRODUCTION = "national_electricity_production"
    NATIONAL_NET_CONSUMPTION = "national_net_electricity_consumption"


class EnergyBoundary(StrEnum):
    CLOUD_IT = "cloud_it"
    CLOUD_FACILITY = "cloud_facility"
    LOCAL_DEVICE = "local_device"


class SourceRecord(StrictModel):
    id: Identifier
    title: Annotated[str, StringConstraints(min_length=1)]
    publisher: Annotated[str, StringConstraints(min_length=1)]
    source_kind: SourceKind
    license: Annotated[str, StringConstraints(min_length=1)]
    url: str | None = None
    publication_date: date | None = None
    retrieved_date: date | None = None
    locator: str | None = None
    query_url: str | None = None
    snapshot_path: str | None = None
    snapshot_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None


class ClassificationReference(StrictModel):
    id: Annotated[str, StringConstraints(min_length=1)]
    name: Annotated[str, StringConstraints(min_length=1)]
    code: Annotated[str, StringConstraints(min_length=1)]
    valid_from: date | None = None
    based_on: str | None = None


class Observation(StrictModel):
    id: Identifier
    country_code: CountryCode
    year: int = Field(ge=1900, le=2200)
    metric: Metric
    unit: Unit
    value: FiniteNonnegative | None
    missing_reason: str | None = None
    source_id: Identifier
    definition: Annotated[str, StringConstraints(min_length=1)]
    boundary: Boundary
    evidence_status: EvidenceStatus
    locator: Annotated[str, StringConstraints(min_length=1)]
    period: str | None = None
    reference_period: str | None = None
    population_basis: str | None = None
    classification: ClassificationReference | None = None
    uncertainty_low: FiniteNonnegative | None = None
    uncertainty_high: FiniteNonnegative | None = None

    @model_validator(mode="after")
    def validate_semantics(self) -> Observation:
        allowed = {
            Metric.WORKERS: {
                (Unit.PEOPLE, Boundary.EMPLOYMENT_HEADCOUNT),
                (Unit.FTE, Boundary.EMPLOYMENT_FTE),
            },
            Metric.ANNUAL_HOURS: {
                (Unit.HOURS_PER_WORKER_YEAR, Boundary.HOURS_PER_WORKER),
                (Unit.HOURS_PER_FTE_YEAR, Boundary.HOURS_PER_FTE),
            },
            Metric.CONNECTION_CAPACITY: {(Unit.MW, Boundary.GRID_CONNECTION)},
            Metric.INSTALLED_IT_CAPACITY: {(Unit.MW, Boundary.IT_EQUIPMENT)},
            Metric.FACILITY_CAPACITY: {(Unit.MW, Boundary.CLOUD_FACILITY)},
            Metric.AVERAGE_LOAD: {
                (Unit.MW, Boundary.METERED_AVERAGE_LOAD),
                (Unit.MW, Boundary.CLOUD_FACILITY),
                (Unit.MW, Boundary.IT_EQUIPMENT),
            },
            Metric.PEAK_DEMAND: {(Unit.MW, Boundary.PEAK_DEMAND)},
            Metric.ELECTRICITY_PRODUCTION: {
                (Unit.MWH, Boundary.NATIONAL_PRODUCTION),
                (Unit.GWH, Boundary.NATIONAL_PRODUCTION),
            },
            Metric.ELECTRICITY_CONSUMPTION: {
                (Unit.MWH, Boundary.NATIONAL_NET_CONSUMPTION),
                (Unit.GWH, Boundary.NATIONAL_NET_CONSUMPTION),
            },
        }
        if (self.unit, self.boundary) not in allowed[self.metric]:
            raise ValueError("metric, unit, and boundary are incompatible")
        if self.value is None and not self.missing_reason:
            raise ValueError("a null value requires missing_reason")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("missing_reason is only valid for a null value")
        if (self.uncertainty_low is None) != (self.uncertainty_high is None):
            raise ValueError("uncertainty bounds must be supplied together")
        if self.uncertainty_low is not None:
            if self.uncertainty_low > self.uncertainty_high:
                raise ValueError("uncertainty_low must not exceed uncertainty_high")
            if self.value is not None and not (
                self.uncertainty_low <= self.value <= self.uncertainty_high
            ):
                raise ValueError("value must lie within uncertainty bounds")
        return self


class OccupationInput(StrictModel):
    id: Identifier
    title: Annotated[str, StringConstraints(min_length=1)]
    country_code: CountryCode
    year: int = Field(ge=1900, le=2200)
    workforce_basis: Literal["headcount", "fte"]
    workers_observation_id: Identifier
    annual_hours_observation_id: Identifier


class OccupationCoverageFrame(StrictModel):
    id: Identifier
    country_code: CountryCode
    year: int = Field(ge=1900, le=2200)
    classification: ClassificationReference
    declared_cell_ids: list[Identifier] = Field(min_length=1)
    cell_observation_ids: dict[Identifier, Identifier] = Field(default_factory=dict)
    occupation_cell_assignments: dict[Identifier, list[Identifier]] = Field(default_factory=dict)
    uncovered_cell_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_partition(self) -> OccupationCoverageFrame:
        if len(self.declared_cell_ids) != len(set(self.declared_cell_ids)):
            raise ValueError("coverage frame cell IDs must be unique")
        assigned = [
            cell_id
            for cell_ids in self.occupation_cell_assignments.values()
            for cell_id in cell_ids
        ]
        if len(assigned) != len(set(assigned)):
            raise ValueError("occupation coverage cells must not overlap")
        if len(self.uncovered_cell_ids) != len(set(self.uncovered_cell_ids)):
            raise ValueError("uncovered coverage cell IDs must be unique")
        if set(assigned) & set(self.uncovered_cell_ids):
            raise ValueError("modeled and uncovered coverage cells must not overlap")
        if set(assigned) | set(self.uncovered_cell_ids) != set(self.declared_cell_ids):
            raise ValueError("modeled and uncovered cells must partition the coverage frame")
        if set(self.cell_observation_ids) != set(self.declared_cell_ids):
            raise ValueError("each coverage cell must reference one observation")
        if len(self.cell_observation_ids.values()) != len(set(self.cell_observation_ids.values())):
            raise ValueError("coverage cells must reference distinct observations")
        return self


class PlacementInput(StrictModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    share: Fraction
    benchmark_id: Identifier


class TaskProfile(StrictModel):
    id: Identifier
    occupation_id: Identifier
    digital_fraction: Fraction | None = None
    ai_fraction: Fraction | None = None
    requests_per_ai_hour: FiniteNonnegative | None = None
    placements: list[PlacementInput] = Field(default_factory=list)
    source_ids: list[Identifier] = Field(min_length=1)
    missing_reason: str | None = None

    @model_validator(mode="after")
    def validate_shares(self) -> TaskProfile:
        values = (self.digital_fraction, self.ai_fraction, self.requests_per_ai_hour)
        if self.missing_reason is not None:
            if any(value is not None for value in values) or self.placements:
                raise ValueError("a missing task profile cannot contain modeled values")
            return self
        if any(value is None for value in values) or not self.placements:
            raise ValueError("a modeled task profile requires all values and placements")
        if not math.isclose(sum(item.share for item in self.placements), 1, abs_tol=1e-12):
            raise ValueError("placement shares must sum to 1")
        return self


class EnergyBenchmarkInput(StrictModel):
    id: Identifier
    title: Annotated[str, StringConstraints(min_length=1)]
    kwh_per_request: FiniteNonnegative
    boundary: EnergyBoundary
    source_id: Identifier
    definition: Annotated[str, StringConstraints(min_length=1)]
    measured_period: str | None = None
    model: str | None = None
    hardware: str | None = None
    workload: str | None = None
    batching: str | None = None
    context_and_output: str | None = None
    utilization: str | None = None
    limitations: str | None = None


class AssumptionValue(StrictModel):
    value: Annotated[float, Field(ge=1, allow_inf_nan=False)]
    source_ids: list[Identifier] = Field(min_length=1)


class ConstructionStatus(StrEnum):
    ANNOUNCED = "announced"
    PLANNING = "planning"
    APPROVED = "approved"
    UNDER_CONSTRUCTION = "under_construction"
    OPERATING = "operating"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class GridStatus(StrEnum):
    INQUIRY = "inquiry"
    QUEUED = "queued"
    RESERVED = "reserved"
    CONNECTED = "connected"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class ConstructionStatusRecord(StrictModel):
    status: ConstructionStatus
    as_of_date: date
    source_id: Identifier
    locator: Annotated[str, StringConstraints(min_length=1)]


class GridStatusRecord(StrictModel):
    status: GridStatus
    as_of_date: date
    source_id: Identifier
    locator: Annotated[str, StringConstraints(min_length=1)]


class ProjectPhase(StrictModel):
    id: Identifier
    title: Annotated[str, StringConstraints(min_length=1)]
    aliases: list[Annotated[str, StringConstraints(min_length=1)]] = Field(default_factory=list)
    observation_ids: list[Identifier] = Field(default_factory=list)
    construction_status: list[ConstructionStatusRecord] = Field(default_factory=list)
    grid_status: list[GridStatusRecord] = Field(default_factory=list)


class DataCenterProject(StrictModel):
    id: Identifier
    title: Annotated[str, StringConstraints(min_length=1)]
    country_code: CountryCode
    aliases: list[Annotated[str, StringConstraints(min_length=1)]] = Field(default_factory=list)
    phases: list[ProjectPhase] = Field(min_length=1)
    completeness_limitations: Annotated[str, StringConstraints(min_length=1)]


class EvidenceStance(StrEnum):
    SUPPORTING = "supporting"
    CHALLENGING = "challenging"
    MIXED = "mixed"


class EvidenceEntry(StrictModel):
    id: Identifier
    stance: EvidenceStance
    finding: Annotated[str, StringConstraints(min_length=1)]
    method: Annotated[str, StringConstraints(min_length=1)]
    applicability: Annotated[str, StringConstraints(min_length=1)]
    funding_and_conflicts: Annotated[str, StringConstraints(min_length=1)]
    limitations: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)
    affected_assumption_source_ids: list[Identifier] = Field(default_factory=list)


class ScenarioCategory(StrEnum):
    OCCUPATION_HUMAN_INFERENCE = "occupation_human_inference"
    AUTONOMOUS_BACKGROUND_INFERENCE = "autonomous_background_inference"
    CONSUMER_AI = "consumer_ai"
    FOUNDATION_TRAINING = "foundation_training"
    FINE_TUNING = "fine_tuning"
    RETRIEVAL_EMBEDDINGS = "retrieval_embeddings"
    NON_AI = "non_ai"


class AdoptionPresetName(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    HIGH = "high"


class PlacementPresetName(StrEnum):
    CLOUD_HEAVY = "cloud-heavy"
    HYBRID = "hybrid"
    LOCAL_HEAVY = "local-heavy"


class ScenarioCategoryActivity(StrictModel):
    category: ScenarioCategory
    pre_rebound_activity_units: FiniteNonnegative | None
    activity_unit: Annotated[str, StringConstraints(min_length=1)]
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)
    missing_reason: str | None = None

    @model_validator(mode="after")
    def validate_missing(self) -> ScenarioCategoryActivity:
        if self.pre_rebound_activity_units is None and not self.missing_reason:
            raise ValueError("unknown category activity requires missing_reason")
        if self.pre_rebound_activity_units is not None and self.missing_reason is not None:
            raise ValueError("missing_reason is only valid for unknown category activity")
        return self


class ScenarioEnergyIntensity(StrictModel):
    category: ScenarioCategory
    cloud_kwh_per_activity_unit: FiniteNonnegative | None
    cloud_missing_reason: str | None = None
    cloud_boundary: Literal[EnergyBoundary.CLOUD_IT, EnergyBoundary.CLOUD_FACILITY]
    local_device_kwh_per_activity_unit: FiniteNonnegative | None
    local_device_missing_reason: str | None = None
    activity_unit: Annotated[str, StringConstraints(min_length=1)]
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_missing(self) -> ScenarioEnergyIntensity:
        pairs = (
            (self.cloud_kwh_per_activity_unit, self.cloud_missing_reason, "cloud"),
            (
                self.local_device_kwh_per_activity_unit,
                self.local_device_missing_reason,
                "local-device",
            ),
        )
        for value, reason, label in pairs:
            if value is None and not reason:
                raise ValueError(f"unknown {label} energy intensity requires missing_reason")
            if value is not None and reason is not None:
                raise ValueError(
                    f"{label} missing_reason is only valid for an unknown energy intensity"
                )
        return self


class ReboundInput(StrictModel):
    category: ScenarioCategory
    baseline_activity_units: FiniteNonnegative
    additional_activity_fraction: FiniteNonnegative
    baseline_definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)


class AdoptionPreset(StrictModel):
    name: AdoptionPresetName
    occupation_activity_multiplier: FiniteNonnegative
    category_activities: list[ScenarioCategoryActivity]
    rebound: ReboundInput | None = None
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_categories(self) -> AdoptionPreset:
        categories = [item.category for item in self.category_activities]
        expected = set(ScenarioCategory) - {ScenarioCategory.OCCUPATION_HUMAN_INFERENCE}
        if len(categories) != len(set(categories)) or set(categories) != expected:
            raise ValueError("adoption preset must define each non-occupation category once")
        if self.rebound is not None and self.rebound.category not in expected:
            raise ValueError("rebound must target one explicit non-occupation category")
        return self


class PlacementPreset(StrictModel):
    name: PlacementPresetName
    cloud_share: Fraction
    domestic_hosting_share: Fraction
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)


class HostingInput(StrictModel):
    exported_hosting_mwh: FiniteNonnegative | None
    exported_hosting_missing_reason: str | None = None
    available_domestic_capacity_mwh: FiniteNonnegative | None = None
    available_domestic_capacity_missing_reason: str | None = None
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_missing(self) -> HostingInput:
        pairs = (
            (
                self.exported_hosting_mwh,
                self.exported_hosting_missing_reason,
                "exported hosting",
            ),
            (
                self.available_domestic_capacity_mwh,
                self.available_domestic_capacity_missing_reason,
                "available domestic capacity",
            ),
        )
        for value, reason, label in pairs:
            if value is None and not reason:
                raise ValueError(f"unknown {label} requires missing_reason")
            if value is not None and reason is not None:
                raise ValueError(f"{label} missing_reason is only valid for an unknown value")
        return self


class SensitivityRange(StrictModel):
    id: Identifier
    parameter: Literal[
        "demand_multiplier", "cloud_share", "domestic_hosting_share", "cloud_pue"
    ]
    low: FiniteNonnegative
    base: FiniteNonnegative
    high: FiniteNonnegative
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self) -> SensitivityRange:
        if not self.low <= self.base <= self.high:
            raise ValueError("sensitivity range must satisfy low <= base <= high")
        if self.parameter in {"cloud_share", "domestic_hosting_share"} and self.high > 1:
            raise ValueError("sensitivity share values must be between 0 and 1")
        if self.parameter == "cloud_pue" and self.low < 1:
            raise ValueError("cloud_pue sensitivity values must be at least 1")
        return self


class JointStressCase(StrictModel):
    id: Identifier
    demand_multiplier: FiniteNonnegative
    cloud_share: Fraction
    domestic_hosting_share: Fraction
    cloud_pue: Annotated[float, Field(ge=1, allow_inf_nan=False)]
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)


class SensitivityConfiguration(StrictModel):
    adoption: AdoptionPresetName
    placement: PlacementPresetName
    named_ranges: list[SensitivityRange] = Field(min_length=1)
    joint_stress_cases: list[JointStressCase] = Field(min_length=1)


class InverseAllocationInput(StrictModel):
    id: Identifier
    country_code: CountryCode
    year: int = Field(ge=1900, le=2200)
    facility_capacity_mw: FiniteNonnegative
    load_factor: Fraction
    allocation_share: Fraction
    kwh_per_activity_unit: FinitePositive
    energy_boundary: Literal[EnergyBoundary.CLOUD_IT, EnergyBoundary.CLOUD_FACILITY]
    denominator_value: FinitePositive
    denominator_unit: Annotated[str, StringConstraints(min_length=1)]
    denominator_definition: Annotated[str, StringConstraints(min_length=1)]
    activity_unit: Annotated[str, StringConstraints(min_length=1)]
    workload_scope: Identifier
    source_ids: list[Identifier] = Field(min_length=1)


class ScopedQuantity(StrictModel):
    value: FiniteNonnegative
    unit: Annotated[str, StringConstraints(min_length=1)]
    country_code: CountryCode
    year: int = Field(ge=1900, le=2200)
    boundary: Identifier
    definition: Annotated[str, StringConstraints(min_length=1)]
    source_ids: list[Identifier] = Field(min_length=1)


class ValueResourceRatioInput(StrictModel):
    id: Identifier
    value: ScopedQuantity
    resource: ScopedQuantity

    @model_validator(mode="after")
    def validate_compatibility(self) -> ValueResourceRatioInput:
        if (self.value.country_code, self.value.year) != (
            self.resource.country_code,
            self.resource.year,
        ):
            raise ValueError("value and resource country/year must match")
        if self.value.boundary != self.resource.boundary:
            raise ValueError("value and resource boundaries must match")
        if self.resource.value == 0:
            raise ValueError("resource denominator must be greater than 0")
        return self


class ScenarioConfiguration(StrictModel):
    country_code: CountryCode
    year: int = Field(ge=1900, le=2200)
    adoption_presets: list[AdoptionPreset]
    placement_presets: list[PlacementPreset]
    energy_intensities: list[ScenarioEnergyIntensity]
    hosting: HostingInput
    sensitivity: SensitivityConfiguration
    inverse_allocations: list[InverseAllocationInput] = Field(default_factory=list)
    value_resource_ratios: list[ValueResourceRatioInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scenario(self) -> ScenarioConfiguration:
        adoption_names = [item.name for item in self.adoption_presets]
        placement_names = [item.name for item in self.placement_presets]
        categories = [item.category for item in self.energy_intensities]
        if len(adoption_names) != 3 or set(adoption_names) != set(AdoptionPresetName):
            raise ValueError("scenario must define conservative, moderate, and high adoption")
        if len(placement_names) != 3 or set(placement_names) != set(PlacementPresetName):
            raise ValueError("scenario must define cloud-heavy, hybrid, and local-heavy placement")
        if len(categories) != len(set(categories)) or set(categories) != set(ScenarioCategory):
            raise ValueError("scenario must define one energy intensity for every category")
        intensity_units = {item.category: item.activity_unit for item in self.energy_intensities}
        for preset in self.adoption_presets:
            for activity in preset.category_activities:
                if activity.activity_unit != intensity_units[activity.category]:
                    raise ValueError("scenario activity and energy intensity units must match")
        range_ids = [item.id for item in self.sensitivity.named_ranges]
        stress_ids = [item.id for item in self.sensitivity.joint_stress_cases]
        if len(range_ids) != len(set(range_ids)) or len(stress_ids) != len(set(stress_ids)):
            raise ValueError("sensitivity and stress IDs must be unique")
        return self


class InputDataset(StrictModel):
    schema_version: Literal["1.0"]
    model_version: Literal["1.0"]
    sources: list[SourceRecord] = Field(min_length=1)
    observations: list[Observation] = Field(min_length=1)
    occupations: list[OccupationInput] = Field(min_length=1)
    occupation_coverage: list[OccupationCoverageFrame] = Field(default_factory=list)
    task_profiles: list[TaskProfile] = Field(min_length=1)
    energy_benchmarks: list[EnergyBenchmarkInput] = Field(min_length=1)
    cloud_pue: AssumptionValue
    facility_comparator_observation_ids: list[Identifier] = Field(default_factory=list)
    national_electricity_observation_ids: list[Identifier] = Field(default_factory=list)
    projects: list[DataCenterProject] = Field(default_factory=list)
    evidence: list[EvidenceEntry] = Field(default_factory=list)
    scenario: ScenarioConfiguration | None = None

    @model_validator(mode="after")
    def validate_collection(self) -> InputDataset:
        collections = (
            self.sources,
            self.observations,
            self.occupations,
            self.occupation_coverage,
            self.task_profiles,
            self.energy_benchmarks,
            self.projects,
            self.evidence,
        )
        for collection in collections:
            ids = [item.id for item in collection]
            if len(ids) != len(set(ids)):
                raise ValueError("IDs must be unique within each collection")

        sources = {item.id for item in self.sources}
        observations = {item.id: item for item in self.observations}
        occupations = {item.id: item for item in self.occupations}
        benchmarks = {item.id for item in self.energy_benchmarks}
        referenced_sources = {
            *(item.source_id for item in self.observations),
            *(item.source_id for item in self.energy_benchmarks),
            *self.cloud_pue.source_ids,
            *(source_id for profile in self.task_profiles for source_id in profile.source_ids),
            *(
                status.source_id
                for project in self.projects
                for phase in project.phases
                for status in [*phase.construction_status, *phase.grid_status]
            ),
            *(source_id for entry in self.evidence for source_id in entry.source_ids),
            *(
                source_id
                for entry in self.evidence
                for source_id in entry.affected_assumption_source_ids
            ),
        }
        if missing := referenced_sources - sources:
            raise ValueError(f"unknown source references: {sorted(missing)}")

        expected_units = {
            "headcount": (Unit.PEOPLE, Unit.HOURS_PER_WORKER_YEAR),
            "fte": (Unit.FTE, Unit.HOURS_PER_FTE_YEAR),
        }
        for occupation in self.occupations:
            try:
                workers = observations[occupation.workers_observation_id]
                hours = observations[occupation.annual_hours_observation_id]
            except KeyError as error:
                raise ValueError(f"unknown occupation observation: {error.args[0]}") from error
            if workers.metric != Metric.WORKERS or hours.metric != Metric.ANNUAL_HOURS:
                raise ValueError("occupation observation metrics are incompatible")
            if (workers.unit, hours.unit) != expected_units[occupation.workforce_basis]:
                raise ValueError("occupation observations do not match workforce_basis")
            for observation in (workers, hours):
                if (observation.country_code, observation.year) != (
                    occupation.country_code,
                    occupation.year,
                ):
                    raise ValueError("occupation and observation country/year must match")

        coverage_keys: set[tuple[str, int]] = set()
        for frame in self.occupation_coverage:
            key = (frame.country_code, frame.year)
            if key in coverage_keys:
                raise ValueError("each country/year must have at most one occupation coverage frame")
            coverage_keys.add(key)
            for cell_id, observation_id in frame.cell_observation_ids.items():
                observation = observations.get(observation_id)
                if observation is None or observation.metric != Metric.WORKERS:
                    raise ValueError("coverage cells must reference worker observations")
                if (observation.country_code, observation.year) != key:
                    raise ValueError("coverage frame and observation country/year must match")
                if observation.classification is None or observation.classification.code != cell_id:
                    raise ValueError("coverage cell and observation classification code must match")
            for occupation_id in frame.occupation_cell_assignments:
                occupation = occupations.get(occupation_id)
                if occupation is None:
                    raise ValueError(f"unknown coverage occupation reference: {occupation_id}")
                if (occupation.country_code, occupation.year) != key:
                    raise ValueError("coverage frame and occupation country/year must match")

        profile_occupations: set[str] = set()
        for profile in self.task_profiles:
            if profile.occupation_id not in occupations:
                raise ValueError(f"unknown occupation reference: {profile.occupation_id}")
            if profile.occupation_id in profile_occupations:
                raise ValueError("each occupation must have exactly one task profile")
            profile_occupations.add(profile.occupation_id)
            for placement in profile.placements:
                if placement.benchmark_id not in benchmarks:
                    raise ValueError(f"unknown benchmark reference: {placement.benchmark_id}")
        if profile_occupations != set(occupations):
            raise ValueError("each occupation must have exactly one task profile")

        for observation_id in self.facility_comparator_observation_ids:
            observation = observations.get(observation_id)
            if observation is None or observation.metric != Metric.FACILITY_CAPACITY:
                raise ValueError("facility comparator must reference a facility_capacity observation")

        for observation_id in self.national_electricity_observation_ids:
            observation = observations.get(observation_id)
            if observation is None or observation.metric not in {
                Metric.ELECTRICITY_PRODUCTION,
                Metric.ELECTRICITY_CONSUMPTION,
            }:
                raise ValueError("national electricity references must use electricity observations")

        project_metrics = {
            Metric.CONNECTION_CAPACITY,
            Metric.INSTALLED_IT_CAPACITY,
            Metric.FACILITY_CAPACITY,
            Metric.AVERAGE_LOAD,
            Metric.PEAK_DEMAND,
        }
        phase_ids: set[str] = set()
        attached_observations: set[str] = set()
        aliases: set[str] = set()
        for project in self.projects:
            project_aliases = [project.id, project.title, *project.aliases]
            for alias in project_aliases:
                normalized = alias.casefold().strip()
                if normalized in aliases:
                    raise ValueError("project IDs, titles, and aliases must be globally unique")
                aliases.add(normalized)
            for phase in project.phases:
                if phase.id in phase_ids:
                    raise ValueError("project phase IDs must be globally unique")
                phase_ids.add(phase.id)
                phase_aliases: set[str] = set()
                for alias in [phase.id, phase.title, *phase.aliases]:
                    normalized = alias.casefold().strip()
                    if normalized in phase_aliases:
                        raise ValueError("phase IDs, titles, and aliases must be unique within a phase")
                    phase_aliases.add(normalized)
                for observation_id in phase.observation_ids:
                    observation = observations.get(observation_id)
                    if observation is None or observation.metric not in project_metrics:
                        raise ValueError("project phases must reference project metric observations")
                    if observation.country_code != project.country_code:
                        raise ValueError("project and observation country must match")
                    if observation_id in attached_observations:
                        raise ValueError("a project observation may belong to only one phase")
                    attached_observations.add(observation_id)

        source_records = {item.id: item for item in self.sources}
        for entry in self.evidence:
            for source_id in entry.affected_assumption_source_ids:
                if source_records[source_id].source_kind != SourceKind.ASSUMPTION:
                    raise ValueError("affected assumptions must reference assumption sources")
        if self.scenario is not None:
            scenario = self.scenario
            assumption_source_ids = {
                *(source_id for item in scenario.adoption_presets for source_id in item.source_ids),
                *(
                    source_id
                    for item in scenario.adoption_presets
                    for activity in item.category_activities
                    for source_id in activity.source_ids
                ),
                *(
                    source_id
                    for item in scenario.adoption_presets
                    if item.rebound is not None
                    for source_id in item.rebound.source_ids
                ),
                *(
                    source_id
                    for item in scenario.placement_presets
                    for source_id in item.source_ids
                ),
                *(
                    source_id
                    for item in scenario.sensitivity.named_ranges
                    for source_id in item.source_ids
                ),
                *(
                    source_id
                    for item in scenario.sensitivity.joint_stress_cases
                    for source_id in item.source_ids
                ),
            }
            scenario_source_ids = {
                *scenario.hosting.source_ids,
                *assumption_source_ids,
                *(
                    source_id
                    for item in scenario.energy_intensities
                    for source_id in item.source_ids
                ),
                *(
                    source_id
                    for item in scenario.inverse_allocations
                    for source_id in item.source_ids
                ),
                *(
                    source_id
                    for item in scenario.value_resource_ratios
                    for quantity in (item.value, item.resource)
                    for source_id in quantity.source_ids
                ),
            }
            if missing := scenario_source_ids - sources:
                raise ValueError(f"unknown scenario source references: {sorted(missing)}")
            invalid_sources = {
                source_id
                for source_id in assumption_source_ids
                if source_records[source_id].source_kind
                not in {SourceKind.ASSUMPTION, SourceKind.SYNTHETIC}
            }
            if invalid_sources:
                raise ValueError("scenario assumptions must use assumption or synthetic sources")
            if scenario.sensitivity.adoption not in {
                item.name for item in scenario.adoption_presets
            } or scenario.sensitivity.placement not in {
                item.name for item in scenario.placement_presets
            }:
                raise ValueError("sensitivity must reference defined presets")
            for item in scenario.inverse_allocations:
                if (item.country_code, item.year) != (scenario.country_code, scenario.year):
                    raise ValueError("inverse allocation and scenario country/year must match")
        return self
