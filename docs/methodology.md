# Methodology

## Purpose and first milestone

This project tests, rather than assumes, claims about data-centre need and societal value. It can support higher demand, lower demand, or no conclusion. Occupational inference is not a measure of full national data-centre demand.

The synthetic fixture demonstrates the accounting model and makes no claim about Norway or any other country. A separate audited slice uses one observed Norwegian employee count; all downstream hours and usage assumptions remain labeled, and the result is not a national estimate.

Choose a reference year only when the underlying observations are sufficiently compatible. Record each observation date and warn when its age or reference year differs. Unknown is `null` with a reason; a known subtotal is never labelled a national total.

## Occupational inference

Declare whether employment is headcount, jobs, or FTE before aggregation; do not combine them. The initial annual request estimate for an occupational group is:

$$
R = H \times A \times D \times I \times Q
$$

where $H$ is employed headcount, $A$ is annual hours per employed person, $D$ is digital fraction, $I$ is AI-active fraction within digital hours, and $Q$ is requests per AI-active hour.

The fractions must include adoption exactly once. Do not double-count workers through overlapping occupational groups or add a separate adoption multiplier to a fraction that already includes non-adopters. Occupational classification is not industry classification; validate STYRK08/ISCO08 mappings before use.

Broad workforce coverage uses an explicit partition of source-defined atomic cells. Each cell links to one worker observation and belongs either to one modeled occupation group or to the uncovered set. Parent totals are reconciliation controls, not additional cells. A complete worker frame does not imply complete energy modeling when annual hours or task profiles are unknown.

Worker task productivity is not societal productivity. Autonomous agents and background workloads are separately sourced activities or agent-hours: worker hours do not bound them. Non-AI workloads, consumer use, agents, training, fine-tuning, and retrieval stay unknown until studied, rather than becoming zero.

## Workload and energy accounting

Allocate requests across workload/task and model/placement shares. Each allocation set sums to one. The initial implementation uses empirical or explicitly assumed energy per request, with its model, date, workload conditions, measurement boundary, and provenance recorded. It does not represent a full tokens, hardware, or FLOPs model; token-level accounting is later work.

Local-device electricity is tracked and is not zero. Apply PUE exactly once:

- Cloud IT electricity multiplied by PUE yields facility electricity.
- A cloud facility benchmark already measured at facility boundary receives no extra PUE.
- Local-device use receives no PUE.

Rebound is one documented usage response against a stated baseline. Do not multiply it again into a scenario that already embodies the same increased use.

## Capacity, energy, and geography

Keep distinct: MW connection capacity, IT MW, total-facility MW, actual average load MW, peak load, and annual MWh. Annual energy divided by hours in the selected year gives annual-average load; a modeled energy input gives a modeled load, not observed use. Use 8,784 hours in leap years and 8,760 otherwise. Average load is neither reserve nor peak.

Installed or equivalent capacity may use an explicit load factor (LF). A zero LF produces zero energy for a given capacity, but inferring equivalent capacity by dividing energy by zero LF is undefined. The conversion $2{,}000\ \mathrm{MW} \times 8{,}760\ \mathrm{h} = 17.52\ \mathrm{TWh}$ is a hypothetical unit conversion, not Norwegian capacity.

Account separately for national consumption, domestic hosting, imported services, and exported workloads. A residual gap is unallocated: it is not automatically exports, waste, or overbuild. Compare only matched geographies, periods, load boundaries, and units.

## Evidence and interpretation

Every numerical value needs a source snapshot or assumption record: locator, retrieval date, reference date, definition, unit, geography, boundary, license/provenance, and uncertainty or unknown reason. Flag vendor funding and other relevant conflicts.

Select evidence symmetrically: actively record supporting, challenging, and mixed evidence, along with method, applicability, and limitations. Scenarios are conditional intervals, not confidence intervals; do not attach arbitrary probabilities. Do not double-count taxes, turnover, exports, and GDP as benefits. Construction employment or job-years are distinct from permanent FTE.

Results report coverage, material gaps, and sensitivity. They do not make a national conclusion from occupational demand alone.

## Scenario and comparison rules

Scenarios name every changed assumption and preserve a calculation trace. Adoption, task mix, model mix, placement, energy coefficient, domestic-hosting share, background activity, and PUE are separate axes unless evidence establishes a non-overlapping combined measure.

Compare a modeled flow with observed or proposed capacity only after declaring whether each is IT, facility, connection, average, peak, or annual energy. Connection requests, queued projects, reservations, operating facilities, and announced projects are statuses, not interchangeable totals.

Projects and physical phases have stable IDs; names used by operators, municipalities, and grid records are aliases only. Construction and grid status are separate dated histories. A quantity observation belongs to at most one phase, and project totals group only identical country, year, metric, unit, and boundary combinations. Aliases and status transitions never add capacity.

An inverse calculation begins with an explicitly hypothetical capacity and allocation. It may answer what request intensity would be implied under those assumptions; it cannot validate the assumptions or establish observed use.

## Missing-data practice

Use `null` for a missing, withheld, incompatible, or not-yet-studied value, and record which reason applies. Do not replace an unknown with zero, an average from a different boundary, or a value inferred from capacity alone.

Do not use API price as an energy proxy, parameter count alone as FLOPs, or model size alone as task adequacy. Benchmark conditions such as batching, context length, output length, throughput, utilization, and included overhead determine whether a coefficient applies.

Evidence gaps are outputs of the research. A scenario may use an explicit assumption to explore a gap, but the result remains conditional and must retain the gap in its provenance.