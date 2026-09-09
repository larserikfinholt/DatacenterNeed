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
    FACILITY_CAPACITY = "facility_capacity"


class Unit(StrEnum):
    PEOPLE = "people"
    FTE = "fte"
    HOURS_PER_WORKER_YEAR = "hour_per_worker_year"
    HOURS_PER_FTE_YEAR = "hour_per_fte_year"
    MW = "MW"


class Boundary(StrEnum):
    EMPLOYMENT_HEADCOUNT = "employment_headcount"
    EMPLOYMENT_FTE = "employment_fte"
    HOURS_PER_WORKER = "annual_hours_per_worker"
    HOURS_PER_FTE = "annual_hours_per_fte"
    CLOUD_FACILITY = "cloud_facility"


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
            Metric.FACILITY_CAPACITY: {(Unit.MW, Boundary.CLOUD_FACILITY)},
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


class PlacementInput(StrictModel):
    name: Annotated[str, StringConstraints(min_length=1)]
    share: Fraction
    benchmark_id: Identifier


class TaskProfile(StrictModel):
    id: Identifier
    occupation_id: Identifier
    digital_fraction: Fraction
    ai_fraction: Fraction
    requests_per_ai_hour: FiniteNonnegative
    placements: list[PlacementInput] = Field(min_length=1)
    source_ids: list[Identifier] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_shares(self) -> TaskProfile:
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


class InputDataset(StrictModel):
    schema_version: Literal["1.0"]
    model_version: Literal["1.0"]
    sources: list[SourceRecord] = Field(min_length=1)
    observations: list[Observation] = Field(min_length=1)
    occupations: list[OccupationInput] = Field(min_length=1)
    task_profiles: list[TaskProfile] = Field(min_length=1)
    energy_benchmarks: list[EnergyBenchmarkInput] = Field(min_length=1)
    cloud_pue: AssumptionValue
    facility_comparator_observation_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_collection(self) -> InputDataset:
        collections = (
            self.sources,
            self.observations,
            self.occupations,
            self.task_profiles,
            self.energy_benchmarks,
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
        return self
