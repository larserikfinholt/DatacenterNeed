# Developer AI Power Reference: Implementation Handoff

Planning date: 2026-09-10. Status: Stage 1 implemented and locally validated.
This is the next implementation priority ahead of public-release Milestone 5.
The user requested a durable plan for a new session using lower-cost Sol and
Terra implementation agents. Do not require the previous chat to proceed.

## Start Prompt for a New Session

> Implement docs/developer-reference-plan.md in bounded stages. Read its full
> requirements and docs/methodology.md, then inspect current Git state and the
> nearest existing implementation/test before editing. Use GPT-5.6 Sol (copilot)
> for implementation subagents and GPT-5.6 Terra (copilot) for simpler fixtures,
> documentation, and independent review. The main session coordinates, reviews,
> and runs integrated checks. Delegation is explicitly authorized for this work.
> If either model cannot be selected, tell me and stop delegation; do not silently
> substitute a more expensive model. Start with Stage 1, complete and validate
> each stage before proceeding, and record any remaining work in the handoff.
> Preserve the existing request-based model and all Norway observations and null
> national totals. Keep assumptions distinct from evidence. Do not commit, push,
> deploy, configure Pages, change CI, rent GPUs, or create cloud resources.
> Finish the standalone reference, its artifacts, and dashboard before any
> occupational integration. Do not implement the deferred occupation stage yet.

Model identifiers previously accepted by the tool:

- `GPT-5.6 Sol (copilot)`
- `GPT-5.6 Terra (copilot)`

Bare `sol` was rejected in an earlier session. Availability is not guaranteed.
Use `runSubagent` with the explicit `model` value; naming a model in an agent's
prompt does not select it. Do not launch any implementation agents merely to
read or maintain this planning document.

## Objective and Scope

Estimate the electrical power required to support one developer doing sustained
agentic development. Treat that workload as the 100% reference for later
occupation-relative demand, not as 100% GPU utilization or universal adoption.
The target workflow may aspire to substantial productivity gains, but "10x"
is a capability hypothesis, never a measured gain or power multiplier.

Initial configuration: GLM-5.3-Flash or an explicitly named alternative,
8 x NVIDIA H100 SXM 80 GB in one node, 20 concurrent developers, normally one
agent job per developer. Make jobs per developer configurable and include a
two-job stress scenario. Do not build a subagent-tree simulator.

Deliver a transparent conditional capacity model, not a single definitive watt
coefficient. A node can consume little per allocated user while delivering an
unacceptably slow service; power allocation and service feasibility are separate
outputs. The request-energy method remains an alternative cross-check, never an
additional charge for the same inference workload.

In scope: profiles, pure calculations, validation, standalone offline artifacts,
scenario/sensitivity tables, dashboard controls and charts, evidence gaps, tests.
Out of scope: deployment, real GPU benchmarking without separate authorization,
training, broad agent parallelism, productivity valuation, new national totals,
and applying relative occupation coefficients to Norway in this implementation.

## Existing Anchors

- `src/datacenter_need/model.py`: pure accounting functions and explicit boundaries.
- `src/datacenter_need/schemas.py`: source/assumption contracts and dataset validation.
- `src/datacenter_need/pipeline.py`: deterministic exports, trace, output protection.
- `src/datacenter_need/cli.py`: argparse commands; reuse its conventions.
- `src/datacenter_need/scenario.py`: existing scenario algebra, not a place to
  silently replace occupational inference with this reference model.
- `data/norway/software-developers-2025.yaml`: observed SSB headcount plus separate
  assumed hours/usage and a reported Gemini median-prompt proxy. Leave unchanged.
- `tests/test_model.py`, `tests/test_data.py`, `tests/test_build.py`: neighboring patterns.
- `web/src/scenario.ts` and `scripts/export_dashboard_vectors.py`: browser/Python parity.
- `web/src/app.ts`, `web/src/dashboard.ts`, `web/src/style.css`: existing dashboard.
- `web/src/artifacts.ts`: strict versioned artifact parsing.
- `web/e2e/dashboard.spec.ts`: mobile/desktop browser checks.

Python is authoritative. The frontend is vanilla TypeScript/Vite with Vega-Lite
and Lucide, not React. Preserve its design and static-only architecture.

## Data Contract

Choose the smallest contracts consistent with existing Pydantic/provenance
patterns. Prefer separate reference profiles over an invasive national schema
rewrite. Proposed module names below are new files, not existing APIs.

| Profile | Required inputs and distinctions |
| --- | --- |
| Model | Model ID/revision, weight precision, reasoning effort, runtime weight memory, capability evidence/assumption |
| Accelerator/node | GPU SKU and form factor, count, memory, interconnect, GPUs per replica, replica count, serving engine/version |
| Power | GPU idle and workload-busy W, configured power limit/TDP as metadata, measured or assumed power curve, CPU/RAM/NIC/fan/PSU overhead with boundary |
| Workload | Concurrent developers, agent jobs/developer, inference duty cycle/job, workday hours, tool/user waiting, input/output/reasoning token lengths, context distribution |
| Serving | Aggregate output tokens/s, prefill workload/support, per-stream speed, latency objectives, practical concurrency, runtime/KV/recurrent-state memory, batching/prefix cache/speculation settings |
| Operations | Actual occupancy, burst margin, idle/off-hours schedule, allocation basis, optional PUE and explicit redundancy assumptions |
| Evidence | Source IDs, source kind, date, locator/snapshot/hash where permitted, units, boundary, uncertainty interval or unknown reason, applicability and vendor affiliation |

Every material numeric assumption must be editable and traceable. Unknown values
are null with reasons, never zero or silently borrowed from another model.
Reject nonfinite values, negative power, invalid fractions, impossible counts,
incompatible topology, and incompatible profile references. Reject unsupported
hardware/precision combinations or report them explicitly as unverified when
compatibility is unknown. H100, H200, and B200 are profiles, not formula branches.

GPU memory utilization settings are allocation fractions, not compute utilization.
Keep GPU compute utilization, job inference duty cycle, developer occupancy,
production headroom, and annual facility load factor separate.

## Calculation Contract

### Power and Allocation

For G GPUs and compute utilization u, an explicitly approximate fallback is:

$$P_{IT}(u)=G[P_{idle}+(P_{busy}-P_{idle})f(u)]+P_{other}(u)$$

Use f(u)=u only as a labeled assumption. Prefer workload-matched measured points
or measured whole-node power. Do not add component estimates to a whole-node
measurement that already includes them. TDP is not the busy-power measurement.
GPU telemetry excludes parts of the node; prefer AC node/PDU measurements for
complete IT electricity, including conversion losses.

Expose at least:

- Total node IT W/kW at the scenario's load.
- W and kW per actually active developer: P_IT / N_active, with denominator defined.
- Practical-full-capacity reference: P_IT(N_max) / N_max, only if capacity is known.
- Per-developer energy at actual occupancy, including allocated idle capacity.
- Workday kWh: integrate node W over hours, divide by 1000 and the explicitly
  served developer count for a constant cohort. For changing cohorts, allocate
  time slices first and report developer-hours rather than inventing a count.
- Optional off-hours idle allocation separately from workday energy.
- Optional facility values: IT x PUE exactly once; no extra PUE on facility data.

Do not divide by occupancy after already using actual user count. Do not multiply
by duty cycle again after using power averaged over that same workload. An idle
node may consume power with zero users; its per-user result is null, not infinity.
Workday power is not calendar-year average power, peak demand, or grid capacity.

### Capacity and Service Feasibility

Report three layers, never conflating them:

1. Theoretical bounds: weight/runtime/cache fit per GPU/rank and compute/memory
   limits under named assumptions. A memory concurrency bound is not goodput.
2. Practical production capacity: concurrency and completed throughput meeting
   explicit latency objectives for this model, hardware, engine, and workload.
3. Actual average load: observed or assumed users, job demand, utilization and
   occupancy; not automatically equal to the production maximum.

For N users, J jobs/user and duty fraction d (inference service time, excluding
tool waits and queue time), average inference concurrency is C_avg = N x J x d.
Queue delays must not masquerade as increased useful inference activity. This
approximation needs stable service conditions; request/agent traces are better.

For a burst margin b >= 1, a concurrency-only screening bound is:

$$N_{screen}=\left\lfloor\frac{C_{practical}}{bJd}\right\rfloor$$

It is not a guarantee. Also check aggregate throughput, per-stream latency,
prefill demand, memory and workload bursts. Zero J or d implies zero inference
demand, not an infinite validated developer capacity. Avoid applying the same
headroom twice if already embedded in the practical benchmark.

At r output tokens/s per generating stream, C_decode streams require at least
C_decode x r output tokens/s. This is a necessary decode-side check, not a
prefill model. Track input and output separately and include reasoning tokens;
do not sum prefill-only and decode-only peak benchmarks as simultaneous capacity.
Do not charge batching/cache/context overhead twice when measured throughput
already includes it. KV/recurrent-state requirements are model-specific: do not
apply a dense-transformer KV formula blindly to this hybrid model.

Report requested streams, supported streams, supported developers and the
limiting constraint. Distinguish proven invalid configurations, conditional
passes based on assumptions, benchmark-supported passes, overload, and unknown
capacity. Missing evidence must remain visible even if a user supplies a number.
For overload, power allocation may still be shown but must not be labeled the
energy required to successfully support all requested users.

Do not infer GPU utilization directly from stream count without a calibrated
mapping. Support explicit utilization assumptions for point scenarios. Chart
sweeps need either a traceable load-to-power mapping or a prominently labeled
fixed-power allocation mode; never invent a throughput or utilization curve.

## Initial Examples and Arithmetic Fixtures

All values below are assumptions, not measured H100/GLM performance. Initial
model profile: GLM-5.3-Flash native FP8, H100 SXM 80 GB x 8, 20 users, 8 hours.
Power fixture: idle 100 W/GPU, busy 600 W/GPU, other node power 1000 W, f(u)=u.

| Scenario | Jobs/user | Duty | Assumed GPU utilization | Node kW | W/user | kW/user | Workday kWh/user |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Low load | 1 | 0.40 | 0.25 | 2.8 | 140 | 0.140 | 1.12 |
| Baseline | 1 | 0.80 | 0.65 | 4.4 | 220 | 0.220 | 1.76 |
| Heavy | 2 | 0.80 | 0.90 | 5.4 | 270 | 0.270 | 2.16 |

The heavy row's electricity is merely an allocation if capacity fails.
For a separate synthetic capacity fixture use C_practical=20, b=1.25,
d=0.8: the concurrency screen gives 20 users at J=1 and 10 users at J=2.
At 40 output tokens/s/stream, 20 generating streams need 800 output tokens/s.
These numbers are not a GLM benchmark and do not establish production adequacy.

Exploratory sensitivity intervals, all provisional assumptions: GPU busy
350-650 W, GPU idle 60-150 W, other node power 700-2000 W. Vary practical
capacity, occupancy, context, reasoning, jobs/user and duty cycle as well.
Do not present these ranges as empirical confidence intervals or imply all
independent extremes describe one physically consistent workload.

## Research Already Performed

Web pages were consulted on 2026-09-10. No benchmark snapshots were added to
the repository and no GPU experiment was performed. Verify/pin sources before
promoting these planning notes to evidence records. Vendor/engine documentation
is not independent verification; source dates and software versions matter.

| Source | Finding | Applicability/limitation |
| --- | --- | --- |
| https://huggingface.co/zai-org/GLM-5.3-Flash | About 320B total / 18B active parameters; FP8 checkpoint; hybrid attention | Model card, not power or 20-user serving benchmark; productivity not established |
| https://recipes.vllm.ai/zai-org/GLM-5.3-Flash | About 306 GiB native FP8 weights before runtime/cache; Hopper support; BF16 KV required on Hopper in this recipe | Text updated 2026-09-05; memory estimate is not a fit/concurrency guarantee; distinguish weights from UI memory estimates |
| https://www.nvidia.com/en-us/data-center/h100/ | H100 SXM 80 GB, up to 700 W configurable TDP | Not actual continuous inference power; distinguish SXM from PCIe/NVL |
| https://docs.nvidia.com/dgx/dgxh100-user-guide/introduction-to-dgxh100.html | DGX H100: 8 GPUs, 640 GB aggregate GPU memory, 10.2 kW maximum system power | DGX-specific maximum, not average; PSU ratings are not consumption |
| https://nvidia.github.io/TensorRT-LLM/performance/performance-tuning-guide/benchmarking-default-performance.html | Example output: 1585.748 output tokens/s, Llama-3.3-70B BF16, 4 NVLink H100 SXM 80 GB, TP4, TRT-LLM 0.16.0, 2048 input/2048 output, 1000 requests issued together | Throughput demonstration, not GLM or agent workload; separate batch-1 test is about 32 tokens/s; do not combine its latency with the throughput run or scale linearly to 8 GPUs |
| https://mlcommons.org/2024/03/mlperf-inference-v4/ | Published inference and power benchmark program with measured system-power submissions | No matching GLM/H100 power result was extracted in planning; keep that evidence gap open |
| https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html | Definitions for TTFT, token latency, system vs user throughput | Metrics must match across benchmarks |
| https://docs.vllm.ai/en/latest/cli/bench/serve/ | Workload/concurrency controls, trace replay, percentiles and goodput objectives | Benchmark methodology, not a measured capacity |

No directly matching published 8-H100 / GLM-5.3-Flash / 20-heavy-developer result
with latency and whole-node power was verified. Preserve this gap rather than
converting the initial 20-user assumption into an empirical coefficient.

Future measurement protocol: fixed model/engine revisions, explicit reasoning,
input/output/context distributions, 1/5/10/20/40 users, 1/2 jobs, warm/cold prefix
cache and burst tests. Set p95 TTFT, p95 token latency and error-rate objectives
before the experiment. Measure throughput, service/queue/tool time, per-rank
memory, GPU utilization/power and node AC power over the same interval; include
idle and repeat runs. Save raw results and provenance. Do not run or rent such
infrastructure as part of this implementation without separate authorization.

## Staged Work and Agent Ownership

The main agent owns integration decisions and shared-file edits unless it
explicitly assigns them to one delegate. Agree contracts before dependent
work starts. Never parallelize agents editing the same files. Delegate bounded
stages, not the entire project repeatedly; prefer one Sol agent per active
implementation stage and Terra for genuinely independent work.

### Stage 1: Standalone Calculation and Contracts (Sol)

Proposed new files: `src/datacenter_need/developer_reference.py`,
`src/datacenter_need/developer_reference_schemas.py`, and
`tests/test_developer_reference.py`. Final names may follow nearby conventions.
Reuse source contracts and units without importing national aggregation into
this calculator. Cover power, occupancy/energy, capacity screening, unknowns,
overload, topology/memory compatibility, and evidence status.

First edit: implement the smallest pure power calculation plus arithmetic test;
immediately run its focused pytest slice. Expand locally only after it passes.
The main agent reviews dimensional consistency, all denominators, capacity
semantics, and absence of duty/occupancy/PUE double counting before Stage 2.

### Stage 2: Profiles, Evidence and Offline Artifacts (Sol + Terra)

After Stage 1 contracts stabilize, Terra may own new example/profile data and
documentation, including source-register entries and explicit assumption labels.
Sol owns standalone evaluation/export tests. The main agent owns any edits to
existing CLI/pipeline/schema files unless assigned exclusively to Sol.

Use a dedicated developer-reference example and result namespace with a
versioned contract, JSON result, scenario CSV, trace and hash manifest. Prefer
a narrowly scoped reference CLI command using existing output-safety patterns;
do not force the national dataset shape or alter old artifact interpretation.
Pin the chosen command name in this handoff after implementing it. Existing
national and request-based builds must remain unchanged and reproducible.

Gate: offline input validation/build, deterministic outputs, source links,
invalid-input output protection, and complete reference calculation trace pass.

### Stage 3: Dashboard and Charts (Sol)

Add a standalone developer-reference view/section, independent of the selected
Norway dataset's missing scenario. Load versioned static artifacts, with no
browser calls to upstream research APIs and no backend. Reuse Vega-Lite and
Lucide, the existing visual language, and accessible table alternatives.

Controls cover the required profiles/inputs, compare/reset and explicit units.
Keep substantial assumptions editable; do not hide workload details behind a
single GPU slider. Show IT/facility boundary and service feasibility beside W,
kW, workday kWh, supported developers and practical streams. Match existing
validated share/export conventions where reference selections are shareable.

Charts: kW/developer vs concurrent developers, and kW/developer vs jobs/user.
Each point must be reproducible from its input trace. Show power assumptions,
capacity/headroom limits, overload and unknown regions. Never extend a declining
allocation curve as a promise of unlimited capacity. Sweep scenarios with the
same service objectives; show hardware node counts separately if scaling beyond
one node is added later, not as an implicit assumption in the initial graph.

Gate: Python-exported golden vectors agree with browser calculations, including
unknown and overload states. Browser tests cover profile changes, both charts,
reset/compare, invalid inputs, accessible tables and 375x812/1440x1000 layouts
without overflow or overlaps. Inspect screenshots and nonblank chart marks.
Start a local dev server on a free port and provide its URL when UI work ends.

### Stage 4: Integrated Review and Handoff (Main + Terra)

Terra performs an independent read-only review against this plan, with file/line
findings, assumptions mislabeled as measurements, missing requirements and test
gaps. The main agent fixes/integrates and validates; a delegate's report alone
does not satisfy a gate. Update implementation status and this checklist with
actual commands/results, remaining evidence gaps and next starting point.

### Deferred Stage: Occupational Scaling

Do not implement this stage yet. Later, use occupation-specific headcount or FTE
with matching hours, relative workload and adoption exactly once. SSB employment
counts do not establish AI intensity. Define whether usage observations include
non-adopters. Scale resource demand before allocating fixed idle overhead;
linear W/person scaling assumes comparable workload, occupancy and service.
Do not add this estimate to request-based energy for the same jobs, or let
complete workforce coverage manufacture a complete national energy estimate.

## Delegate Prompt Template

Give each delegate: the exact stage/subtask, this document, owned file paths,
frozen input/output contracts, the nearest existing implementation/test,
acceptance checks and forbidden shared-file edits. Require the following final
report: files changed, behavior implemented, commands and actual results,
unresolved issues, and integration notes. Require an immediate focused test
after the first substantive edit. Load applicable skills from the environment;
do not spend agent budget broadly mapping unrelated repository surfaces.

## Verification and Completion

Before code changes, inspect Git state and run an appropriate local baseline;
the historical test counts in implementation-plan.md are not current evidence.
Dependencies should use the existing locked tooling. Relevant existing commands
(run separately from the repository root):

```powershell
uv run pytest
uv run ruff check .
npm --prefix web run test:unit
npm --prefix web run test:e2e
npm --prefix web run build
git diff --check
```

Use the new focused pytest file after each calculation edit; run targeted
Vitest/Playwright slices for UI work. Only run broader gates at integration.
If dependencies/browser binaries are missing, follow the existing setup in
implementation-plan.md. No network is needed for deterministic model builds.

Required regression cases: arithmetic table above; zero users and idle energy;
zero jobs/duty without infinite capacity; missing throughput/concurrency; profile
incompatibility; overload; memory-limited serving; idle/off-hours allocation;
PUE once; no double occupancy/duty adjustment; input/output token distinction;
changing hardware without changing equations; unchanged Norway null totals;
deterministic trace/hash; browser parity and nonblank responsive charts.

Acceptance does not require pretending to verify real-world capacity. A complete
implementation may correctly report that measured GLM/H100 capacity is unknown.
Clearly separate implemented calculations, passing tests, and unverified
physical assumptions in the final report.

- [x] Stage 1: contracts and pure model validated. Added
  `src/datacenter_need/developer_reference.py` and
  `tests/test_developer_reference.py`; focused tests: 12 passed, full Python
  suite: 71 passed, Ruff passed. The model keeps power allocation separate
  from service feasibility, returns explicit unknown/overload states, applies
  PUE once, and preserves null per-user results for zero active developers.
- [x] Stage 2: traceable profiles and deterministic offline artifacts validated.
  Added the standalone `build-developer-reference` command, versioned result,
  scenarios CSV, trace, schema and manifest under
  `build/developer-reference/v1/`; focused builder tests pass.
- [x] Stage 3: dashboard, charts and Python/browser parity validated. Added a
  separate static Developer reference view with scenario control, accessible
  table, two charts, unknown-state labeling, and copied artifacts under
  `web/public/artifacts/v1/developer-reference/`.
- [x] Stage 4: integrated review, regression gates and handoff complete.
  Python and frontend unit/e2e checks pass; remaining physical evidence gaps
  are documented and no occupation integration was added.
- [ ] Deferred occupation integration: requires a later authorized task.

Stages 1-4 were verified on 2026-09-10 on Windows. No real hardware
measurements or GLM/H100 production-capacity claims were added. The next
authorized work is the deferred occupational integration stage; it must remain
separate from this reference model and preserve unknown national totals.