"""Strict, provenance-aware input contracts for the developer reference."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, model_validator

from datacenter_need.schemas import FiniteNonnegative, Fraction, Identifier, StrictModel


class ReferenceSource(StrictModel):
    id: Identifier
    title: str = Field(min_length=1)
    url: str | None = None
    kind: str = Field(min_length=1)


class ReferenceEvidence(StrictModel):
    id: Identifier
    source_id: Identifier
    boundary: str = Field(min_length=1)
    status: str = Field(min_length=1)
    unknown_reason: str | None = None


class ReferenceModel(StrictModel):
    model_id: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    weight_precision: str = Field(min_length=1)
    weight_memory_gib: FiniteNonnegative | None = None
    capability_evidence: str = Field(min_length=1)
    source_ids: list[Identifier] = Field(default_factory=list, min_length=1)


class ReferenceAccelerator(StrictModel):
    gpu_sku: str = Field(min_length=1)
    form_factor: str = Field(min_length=1)
    gpu_count: int = Field(ge=1)
    memory_gib_per_gpu: FiniteNonnegative
    interconnect: str = Field(min_length=1)
    gpus_per_replica: int = Field(ge=1)
    replica_count: int = Field(ge=1)
    serving_engine: str = Field(min_length=1)
    source_ids: list[Identifier] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def validate_topology(self) -> ReferenceAccelerator:
        if self.gpu_count != self.gpus_per_replica * self.replica_count:
            raise ValueError("GPU topology is incompatible with replica count")
        return self


class ReferencePower(StrictModel):
    gpu_idle_w: FiniteNonnegative
    gpu_busy_w: FiniteNonnegative
    other_node_w: FiniteNonnegative
    configured_power_limit_w: FiniteNonnegative | None = None
    curve_evidence: str = Field(min_length=1)
    other_boundary: str = "node_it"
    source_ids: list[Identifier] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def validate_boundary(self) -> ReferencePower:
        if self.gpu_busy_w < self.gpu_idle_w:
            raise ValueError("gpu_busy_w must be at least gpu_idle_w")
        if self.other_boundary != "node_it":
            raise ValueError("other_boundary must be node_it")
        return self


class ReferenceServing(StrictModel):
    aggregate_output_tokens_per_second: FiniteNonnegative | None = None
    per_stream_output_tokens_per_second: FiniteNonnegative | None = None
    practical_concurrency: int | None = Field(default=None, ge=0)
    runtime_memory_gib: FiniteNonnegative | None = None
    kv_memory_gib: FiniteNonnegative | None = None
    prefill_supported: bool
    hardware_precision_compatibility: bool | None = None
    source_ids: list[Identifier] = Field(default_factory=list, min_length=1)


class ReferenceOperations(StrictModel):
    actual_occupancy: Fraction
    burst_margin: Annotated[float, Field(ge=1, allow_inf_nan=False)]
    off_hours: FiniteNonnegative
    pue: Annotated[float, Field(ge=1, allow_inf_nan=False)] | None = None
    source_ids: list[Identifier] = Field(default_factory=list, min_length=1)


class ReferenceWorkload(StrictModel):
    concurrent_developers: int = Field(ge=0)
    jobs_per_developer: int = Field(ge=0)
    inference_duty_cycle: Fraction
    workday_hours: FiniteNonnegative
    tool_wait_fraction: Fraction
    input_tokens: FiniteNonnegative
    output_tokens: FiniteNonnegative
    reasoning_tokens: FiniteNonnegative


class ReferenceScenario(StrictModel):
    id: Identifier
    title: str = Field(min_length=1)
    gpu_utilization: Fraction
    workload: ReferenceWorkload
    source_ids: list[Identifier] = Field(default_factory=list, min_length=1)


class DeveloperReferenceInput(StrictModel):
    schema_version: str
    model_version: str
    reference_id: Identifier
    sources: list[ReferenceSource]
    evidence: list[ReferenceEvidence]
    model: ReferenceModel
    accelerator: ReferenceAccelerator
    power: ReferencePower
    serving: ReferenceServing
    operations: ReferenceOperations
    scenarios: list[ReferenceScenario]

    @model_validator(mode="after")
    def validate_references(self) -> DeveloperReferenceInput:
        source_ids = {item.id for item in self.sources}
        if len(source_ids) != len(self.sources):
            raise ValueError("source IDs must be unique")
        evidence_ids = {item.id for item in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            raise ValueError("evidence IDs must be unique")
        if not {item.source_id for item in self.evidence} <= source_ids:
            raise ValueError("evidence source_id must reference a declared source")
        all_ids = set(self.model.source_ids) | set(self.accelerator.source_ids)
        all_ids |= set(self.power.source_ids) | set(self.serving.source_ids)
        all_ids |= set(self.operations.source_ids)
        all_ids |= {source_id for scenario in self.scenarios for source_id in scenario.source_ids}
        if not all_ids <= source_ids:
            raise ValueError("all source_ids must reference declared sources")
        if not self.scenarios:
            raise ValueError("scenarios must not be empty")
        scenario_ids = [scenario.id for scenario in self.scenarios]
        if len(set(scenario_ids)) != len(scenario_ids):
            raise ValueError("scenario IDs must be unique")
        return self