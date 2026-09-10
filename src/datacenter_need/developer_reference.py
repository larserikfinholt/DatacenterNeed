"""Pure calculations for the standalone developer workload reference."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


def _finite_nonnegative(name: str, value: float) -> float:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def _fraction(name: str, value: float) -> float:
    _finite_nonnegative(name, value)
    if value > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _nonnegative_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    revision: str
    weight_precision: str
    weight_memory_gib: float | None
    capability_evidence: str

    def __post_init__(self) -> None:
        if not self.model_id or not self.revision or not self.weight_precision:
            raise ValueError("model identifiers and precision must not be empty")
        if self.weight_memory_gib is not None:
            _finite_nonnegative("weight_memory_gib", self.weight_memory_gib)
        if not self.capability_evidence:
            raise ValueError("capability_evidence must not be empty")


@dataclass(frozen=True)
class AcceleratorProfile:
    gpu_sku: str
    form_factor: str
    gpu_count: int
    memory_gib_per_gpu: float
    interconnect: str
    gpus_per_replica: int
    replica_count: int
    serving_engine: str

    def __post_init__(self) -> None:
        if not self.gpu_sku or not self.form_factor or not self.interconnect or not self.serving_engine:
            raise ValueError("accelerator identifiers must not be empty")
        _positive_integer("gpu_count", self.gpu_count)
        _finite_nonnegative("memory_gib_per_gpu", self.memory_gib_per_gpu)
        _positive_integer("gpus_per_replica", self.gpus_per_replica)
        _positive_integer("replica_count", self.replica_count)
        if self.gpu_count != self.gpus_per_replica * self.replica_count:
            raise ValueError("GPU topology is incompatible with replica count")


@dataclass(frozen=True)
class PowerProfile:
    gpu_idle_w: float
    gpu_busy_w: float
    other_node_w: float
    configured_power_limit_w: float | None = None
    curve_evidence: str = "assumption"
    other_boundary: str = "node_it"

    def __post_init__(self) -> None:
        _finite_nonnegative("gpu_idle_w", self.gpu_idle_w)
        _finite_nonnegative("gpu_busy_w", self.gpu_busy_w)
        _finite_nonnegative("other_node_w", self.other_node_w)
        if self.configured_power_limit_w is not None:
            _finite_nonnegative("configured_power_limit_w", self.configured_power_limit_w)
        if self.other_boundary not in {"node_it", "gpu_only"}:
            raise ValueError("other_boundary must be node_it or gpu_only")


@dataclass(frozen=True)
class WorkloadProfile:
    concurrent_developers: int
    jobs_per_developer: int
    inference_duty_cycle: float
    workday_hours: float
    tool_wait_fraction: float
    input_tokens: float
    output_tokens: float
    reasoning_tokens: float

    def __post_init__(self) -> None:
        _nonnegative_integer("concurrent_developers", self.concurrent_developers)
        _nonnegative_integer("jobs_per_developer", self.jobs_per_developer)
        _fraction("inference_duty_cycle", self.inference_duty_cycle)
        _finite_nonnegative("workday_hours", self.workday_hours)
        _fraction("tool_wait_fraction", self.tool_wait_fraction)
        _finite_nonnegative("input_tokens", self.input_tokens)
        _finite_nonnegative("output_tokens", self.output_tokens)
        _finite_nonnegative("reasoning_tokens", self.reasoning_tokens)


@dataclass(frozen=True)
class ServingProfile:
    aggregate_output_tokens_per_second: float | None
    per_stream_output_tokens_per_second: float | None
    practical_concurrency: int | None
    runtime_memory_gib: float | None
    kv_memory_gib: float | None
    prefill_supported: bool
    hardware_precision_compatibility: bool | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("aggregate_output_tokens_per_second", self.aggregate_output_tokens_per_second),
            ("per_stream_output_tokens_per_second", self.per_stream_output_tokens_per_second),
            ("runtime_memory_gib", self.runtime_memory_gib),
            ("kv_memory_gib", self.kv_memory_gib),
        ):
            if value is not None:
                _finite_nonnegative(name, value)
        if self.practical_concurrency is not None:
            _nonnegative_integer("practical_concurrency", self.practical_concurrency)


@dataclass(frozen=True)
class OperationsProfile:
    actual_occupancy: float
    burst_margin: float
    off_hours: float
    pue: float | None = None

    def __post_init__(self) -> None:
        _fraction("actual_occupancy", self.actual_occupancy)
        if self.burst_margin < 1 or not math.isfinite(self.burst_margin):
            raise ValueError("burst_margin must be finite and at least 1")
        _finite_nonnegative("off_hours", self.off_hours)
        if self.pue is not None and (self.pue < 1 or not math.isfinite(self.pue)):
            raise ValueError("pue must be finite and at least 1")


@dataclass(frozen=True)
class EvidenceRecord:
    source_id: str
    source_kind: str
    date: str | None
    locator: str | None
    boundary: str
    uncertainty: tuple[float, float] | None = None
    unknown_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_kind or not self.boundary:
            raise ValueError("evidence source_id, source_kind, and boundary are required")
        if self.uncertainty is not None:
            low, high = self.uncertainty
            _finite_nonnegative("uncertainty_low", low)
            _finite_nonnegative("uncertainty_high", high)
            if low > high:
                raise ValueError("uncertainty_low must not exceed uncertainty_high")
        if self.unknown_reason is not None and not self.unknown_reason:
            raise ValueError("unknown_reason must not be empty")


class CapacityStatus(StrEnum):
    CONDITIONAL_PASS = "conditional_pass"
    OVERLOAD = "overload"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapacityScreen:
    status: CapacityStatus
    requested_developers: int
    requested_streams: int | None
    supported_developers: int | None
    supported_streams: int | None
    required_output_tokens_per_second: float | None
    limiting_constraint: str | None
    unknown_reason: str | None = None


@dataclass(frozen=True)
class EnergyAllocation:
    node_it_w: float
    active_developers: int
    watts_per_active_developer: float | None
    workday_kwh_per_active_developer: float | None
    facility_node_w: float | None
    off_hours_kwh: float


def _validate_power_boundary(power: PowerProfile) -> None:
    if power.other_boundary != "node_it":
        raise ValueError("other_node_w must have node_it boundary for node power")


def node_it_power_w(
    gpu_count: int,
    gpu_idle_w: float,
    gpu_busy_w: float,
    gpu_utilization: float,
    other_node_w: float,
) -> float:
    """Estimate node IT power using a labeled linear GPU utilization fallback."""
    if isinstance(gpu_count, bool) or not isinstance(gpu_count, int) or gpu_count < 0:
        raise ValueError("gpu_count must be a nonnegative integer")
    idle = _finite_nonnegative("gpu_idle_w", gpu_idle_w)
    busy = _finite_nonnegative("gpu_busy_w", gpu_busy_w)
    if busy < idle:
        raise ValueError("gpu_busy_w must be at least gpu_idle_w")
    utilization = _fraction("gpu_utilization", gpu_utilization)
    other = _finite_nonnegative("other_node_w", other_node_w)
    return gpu_count * (idle + (busy - idle) * utilization) + other


def power_from_profiles(
    accelerator: AcceleratorProfile,
    power: PowerProfile,
    gpu_utilization: float,
) -> float:
    """Return node IT power without treating TDP as measured busy power."""
    _validate_power_boundary(power)
    return node_it_power_w(
        accelerator.gpu_count,
        power.gpu_idle_w,
        power.gpu_busy_w,
        gpu_utilization,
        power.other_node_w,
    )


def allocate_workday_energy(
    node_power_w: float,
    active_developers: int,
    workday_hours: float,
    actual_occupancy: float = 1.0,
    pue: float | None = None,
    off_hours_hours: float = 0.0,
) -> EnergyAllocation:
    """Allocate measured scenario power to active developers without double occupancy."""
    node_power = _finite_nonnegative("node_power_w", node_power_w)
    active = _nonnegative_integer("active_developers", active_developers)
    hours = _finite_nonnegative("workday_hours", workday_hours)
    _fraction("actual_occupancy", actual_occupancy)
    idle_hours = _finite_nonnegative("off_hours_hours", off_hours_hours)
    if pue is not None and (pue < 1 or not math.isfinite(pue)):
        raise ValueError("pue must be finite and at least 1")
    active_power = node_power
    watts_per_developer = active_power / active if active else None
    workday_kwh = active_power * hours / 1_000 / active if active else None
    facility_power = None if pue is None else node_power * pue
    off_hours_kwh = node_power * idle_hours / 1_000
    return EnergyAllocation(
        node_it_w=node_power,
        active_developers=active,
        watts_per_active_developer=watts_per_developer,
        workday_kwh_per_active_developer=workday_kwh,
        facility_node_w=facility_power,
        off_hours_kwh=off_hours_kwh,
    )


def screen_capacity(
    requested_developers: int,
    jobs_per_developer: int,
    duty_cycle: float,
    burst_margin: float,
    practical_concurrency: int | None,
    aggregate_output_tokens_per_second: float | None = None,
    per_stream_output_tokens_per_second: float | None = None,
) -> CapacityScreen:
    """Screen concurrency and decode throughput without claiming a benchmark."""
    requested = _nonnegative_integer("requested_developers", requested_developers)
    jobs = _nonnegative_integer("jobs_per_developer", jobs_per_developer)
    duty = _fraction("duty_cycle", duty_cycle)
    if burst_margin < 1 or not math.isfinite(burst_margin):
        raise ValueError("burst_margin must be finite and at least 1")
    if aggregate_output_tokens_per_second is not None:
        _finite_nonnegative("aggregate_output_tokens_per_second", aggregate_output_tokens_per_second)
    if per_stream_output_tokens_per_second is not None:
        _finite_nonnegative("per_stream_output_tokens_per_second", per_stream_output_tokens_per_second)
    requested_streams = requested * jobs
    required_output = (
        None
        if per_stream_output_tokens_per_second is None
        else requested_streams * per_stream_output_tokens_per_second
    )
    if practical_concurrency is None:
        return CapacityScreen(
            CapacityStatus.UNKNOWN,
            requested,
            requested_streams,
            None,
            None,
            required_output,
            None,
            "practical concurrency is missing",
        )
    _nonnegative_integer("practical_concurrency", practical_concurrency)
    if jobs == 0 or duty == 0:
        supported = None if practical_concurrency == 0 else practical_concurrency
        return CapacityScreen(
            CapacityStatus.CONDITIONAL_PASS,
            requested,
            requested_streams,
            supported,
            practical_concurrency,
            required_output,
            "no inference demand" if requested else None,
        )
    if aggregate_output_tokens_per_second is None or per_stream_output_tokens_per_second is None:
        return CapacityScreen(
            CapacityStatus.UNKNOWN,
            requested,
            requested_streams,
            None,
            None,
            required_output,
            "throughput evidence",
            "aggregate and per-stream throughput are both required",
        )
    if per_stream_output_tokens_per_second > 0:
        supported_by_decode = math.floor(
            aggregate_output_tokens_per_second / per_stream_output_tokens_per_second
        )
    else:
        supported_by_decode = practical_concurrency
    supported_streams = math.floor(practical_concurrency / (burst_margin * duty))
    supported_developers = supported_streams // jobs
    supported_streams = min(supported_streams, supported_by_decode)
    supported_developers = supported_streams // jobs
    status = (
        CapacityStatus.CONDITIONAL_PASS
        if requested <= supported_developers
        else CapacityStatus.OVERLOAD
    )
    return CapacityScreen(
        status,
        requested,
        requested_streams,
        supported_developers,
        supported_streams,
        required_output,
        "practical concurrency or decode throughput" if status == CapacityStatus.OVERLOAD else None,
    )


def serving_memory_gib(
    model: ModelProfile,
    accelerator: AcceleratorProfile,
    serving: ServingProfile,
) -> float | None:
    """Return total required memory, or None when a required component is unknown."""
    if (
        model.weight_memory_gib is None
        or serving.runtime_memory_gib is None
        or serving.kv_memory_gib is None
    ):
        return None
    return model.weight_memory_gib + serving.runtime_memory_gib + serving.kv_memory_gib


def validate_memory_compatibility(
    model: ModelProfile,
    accelerator: AcceleratorProfile,
    serving: ServingProfile,
) -> None:
    """Reject known memory overflow and leave unknown memory as an explicit result."""
    required = serving_memory_gib(model, accelerator, serving)
    if required is not None:
        available = accelerator.gpus_per_replica * accelerator.memory_gib_per_gpu
        if required > available:
            raise ValueError("model and serving state exceed accelerator memory")


def validate_profile_compatibility(
    model: ModelProfile,
    accelerator: AcceleratorProfile,
    serving: ServingProfile,
) -> str | None:
    """Return an unknown reason when compatibility cannot be established."""
    validate_memory_compatibility(model, accelerator, serving)
    if serving.hardware_precision_compatibility is False:
        raise ValueError("model precision is incompatible with serving hardware")
    if serving.hardware_precision_compatibility is None:
        return "hardware and precision compatibility is unverified"
    if model.weight_memory_gib is None or serving.runtime_memory_gib is None:
        return "model or runtime memory is missing"
    if serving.kv_memory_gib is None:
        return "KV memory is missing"
    return None