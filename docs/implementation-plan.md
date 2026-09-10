# Implementation Plan and Session Handoff

Updated: 2026-09-09 after completion of Milestone 4 static dashboard. This file is the durable handoff for a fresh coding session.
It supersedes the original session-only plan where implementation status differs.

## Prompt for the Next Session

> Read docs/implementation-plan.md, docs/implementation-status.md, and the research brief in readme.md. Continue from Milestone 5, preserving the implemented Python foundation, audited Norway 2025 coverage baseline, scenario engine, and static dashboard. Use GPT-5.6 Sol (copilot) for implementation subagents and GPT-5.6 Terra (copilot) for simpler tasks. Tell me if those models cannot be selected. First verify the local baseline and inspect the versioned dashboard artifacts. Keep assumptions separate from observations and do not convert Norway's incomplete evidence into national figures. Prepare public-release work only when authorized; do not commit, push, deploy, configure Pages, or change CI without my request. Update the handoff and status documents when the milestone is complete.

## Agreed Direction

- Build an open, evidence-based research project, starting with Norway but country-neutral in its calculations.
- First usable release: research foundation plus a deliberately simple public dashboard.
- Python is the authoritative ingestion, validation, and calculation pipeline.
- Publish versioned JSON/CSV artifacts to a static TypeScript dashboard.
- Use Git-reviewed contributions for observations, assumptions, corrections, and new countries.
- Proposed hosting is GitHub Pages. No database, accounts, backend API, or Azure resources are needed initially.
- The project must be capable of supporting higher demand, lower demand, or no conclusion. It must actively seek counterevidence to its central hypothesis.

## Completed Checkpoint

The foundation is implemented, not merely planned:

- Python package with Hatchling, Pydantic 2, Pint, PyYAML, pytest, Ruff, and a uv lockfile.
- Provenance-linked input validation: source references, unique IDs, finite values, units, measurement boundaries, workforce basis, country/year compatibility, and placement shares.
- Pure functions for annual requests, request-level inference electricity, PUE handling, annual-average load, equivalent capacity, and inverse requests per worker.
- CLI commands: `validate`, `build`, and `schema`.
- Deterministic offline JSON/CSV exports, a replayable `input_trace`, and a SHA-256 manifest.
- Unknown occupation inputs stay unknown; all-unknown country subtotals are `null`, not zero. `national_total_mwh` remains `null` because coverage is incomplete.
- Build output protection: invalid inputs preserve the previous output; unrelated files, an output directory containing the input, and unresolved backup directories are rejected.
- Synthetic NO/SE regression fixtures plus one separately named, audited Norwegian SSB employee observation and one reported facility-energy benchmark.
- Methodology, source register, contribution guidance, README quickstart, and CI configuration.

Last verified locally on Windows on 2026-09-09:

- 59 tests passed and Ruff passed.
- Synthetic, `software-developers-2025`, and `norway-2025` inputs validated and built offline.
- Schema export and `git diff --check` passed.

CI is configured for Windows/Ubuntu and Python 3.12/3.13. Remote CI has not been verified. No deployment, Pages configuration, CI integration for the dashboard, remote resource creation, commit, or push was performed by the assistant. The user may check in the work after this handoff; inspect Git state rather than assuming changes remain uncommitted.

Milestone 2 added an atomic SSB Norway baseline fetch, explicit occupation coverage partitions, national electricity contracts, project/phase/status schemas, unknown-preserving project aggregation, and an evidence ledger. The 2025 dataset contains nine broad modeled groups and one uncovered `0b` cell, observed production/net consumption, and a limited two-site project identity pilot without MW totals.

Milestone 3 added optional scenario contracts and a separate scenario engine. It evaluates all 3 adoption by 3 placement combinations; keeps seven demand categories separate; models explicit pre-rebound activity plus additive documented-baseline rebound; conserves imports, domestic hosting, and exports while retaining unknown residuals/gaps; and supports named one-at-a-time ranges and joint stress. It also adds explicit AI-only inverse denominators, matched country/year/boundary value-resource ratios, and assumption/observed/reported/synthetic provenance. Unknown used activity, intensity, or incomplete occupation coverage blocks complete national totals and complete hosting, while known subtotals remain available. Only `synthetic.yaml` contains explicit synthetic scenario assumptions and complete synthetic coverage; Norway datasets have no scenario configuration, remain unchanged, and keep `national_total_mwh` null.

Milestone 4 added a static Vite vanilla TypeScript dashboard under `web/`, with no backend, runtime Python, or visitor-side upstream fetching. It reads committed versioned artifacts under `web/public/artifacts/v1`: the Norway 2025 observed baseline and a prominently labeled synthetic example. `scripts/refresh_web_artifacts.py` verifies each `result.json` SHA-256 against its manifest before deterministic copying and indexing; `scripts/export_dashboard_vectors.py` exports authoritative Python scenario vectors. The four views cover Electricity & capacity, Demand & scenarios, Projects & resources, and Sources, assumptions & evidence. Norway remains the default and shows its null national total, no scenario, explicit missing occupation calculations, no MW project totals, non-exhaustive two-site inventory, observed 2025 electricity only, and absent benefits. Adjustable scenario workflows are available only for the synthetic dataset.

## Start Here

1. Read the [research brief](../readme.md), [methodology](methodology.md), [source register](source-register.md), and [contribution guidance](../CONTRIBUTING.md).
2. Inspect current Git status and applicable repository instructions. Preserve user changes; do not scaffold over the existing project.
3. Run the baseline below. These commands already exist, unlike the future commands mentioned later.
4. Inspect the nearest schema, pipeline, and test before changing behavior. Choose one small source integration and validate it before expanding coverage.

```powershell
uv sync --frozen
uv run pytest
uv run ruff check .
uv run datacenter-need validate --input data/examples/synthetic.yaml
uv run datacenter-need build --offline --input data/examples/synthetic.yaml --output build/example
uv run datacenter-need schema --output build/input.schema.json
```

Run from the repository root. The build writes `result.json`, `occupation_breakdown.csv`, `input.schema.json`, and `manifest.json` under `build/example/`. Generated output and local caches are ignored by Git; source fixtures and the lockfile are not.

For dashboard development and browser checks, install frontend dependencies with `npm ci --prefix web` and the pinned browser runtime with `npm --prefix web exec playwright install chromium` before running `npm --prefix web run test:all`.

## Existing Implementation Map

| File | Responsibility |
| --- | --- |
| [pyproject.toml](../pyproject.toml) | Package, dependencies, CLI entry point, test/lint configuration |
| [schemas.py](../src/datacenter_need/schemas.py) | SourceRecord, Observation, OccupationInput, TaskProfile, EnergyBenchmarkInput, InputDataset |
| [model.py](../src/datacenter_need/model.py) | annual_requests, inference_energy, annual_average_load_mw, facility_energy_mwh, equivalent_capacity_mw, inverse_requests_per_worker |
| [pipeline.py](../src/datacenter_need/pipeline.py) | load_dataset, evaluate_dataset, build_dataset; tracing and deterministic artifacts |
| [cli.py](../src/datacenter_need/cli.py) | argparse commands for validation, builds, and schema export |
| [synthetic.yaml](../data/examples/synthetic.yaml) | Explicitly synthetic two-country fixture and 2 GW thought experiment |
| [test_model.py](../tests/test_model.py) | Calculation, PUE, conversion, and inverse tests |
| [test_data.py](../tests/test_data.py) | Input contracts, missing data, country neutrality, and replayable trace tests |
| [test_build.py](../tests/test_build.py) | Repeatability, offline behavior, and output protection tests |
| [ci.yml](../.github/workflows/ci.yml) | Frozen installation, tests, lint, validation, and offline build |
| [web/](../web/) | Static Vite vanilla TypeScript dashboard, browser scenario algebra, charts, and tests |
| [refresh_web_artifacts.py](../scripts/refresh_web_artifacts.py) | Manifest-verified deterministic artifact refresh and index generation |
| [export_dashboard_vectors.py](../scripts/export_dashboard_vectors.py) | Authoritative Python scenario-vector export for browser parity tests |

## Completed Milestone: Verified Norwegian Data

Completed 2026-09-09 with a narrow audited slice:

- SSB table 11658, 2025 Q4, both sexes, all ages, STYRK-08 2512 “Software developers,” number of employees: 8,224 persons.
- The source is archived as deterministic JSON-stat2 with its exact query, source update time, retrieval date, and SHA-256 manifest. A strict adapter rejects changed dimensions, units, labels, boundaries, malformed responses, and invalid values; suppressed/null cells remain missing.
- The one-cell request is below SSB's documented limits of 800,000 cells per extract and 30 queries per minute per IP.
- `fetch-ssb` is the explicit network operation. Offline validation and builds use the committed snapshot and input.
- `data/norway/software-developers-2025.yaml` keeps the employee count observed while annual hours and usage remain assumptions.
- The Google-reported May 2025 median Gemini Apps prompt benchmark is 0.24 Wh at cloud-facility boundary. It includes serving infrastructure and PUE, so PUE is not reapplied. Important undisclosed conditions and lack of independent verification are recorded.
- The resulting 1.70532864 MWh is an illustrative one-occupation calculation, not a national estimate; `national_total_mwh` remains `null`.

### Implemented Work

#### 1. Audit a Narrow Source Slice

- Verify exact SSB employment table IDs, metadata, filters, reference periods, and population basis. Use the current PxWebApi v2 documentation, not guessed endpoints or remembered table definitions.
- Verify STYRK-08/ISCO-08 classification and mapping through SSB Klass. Do not substitute industry categories for occupations or combine parent totals with child rows.
- Choose one occupational group and compatible annual hours data. If group-specific hours cannot be verified, retain a missing value or a clearly documented assumption rather than presenting national-average hours as an observed group value.
- Select a reference year based on compatible observations, not merely the current year or the synthetic fixture's 2025 date.
- Record source URL, query, table/cell locator, publication/retrieval dates, unit, definition, geography, license, and limitations.

Starting sources checked during planning on 2026-09-08:

- [SSB public APIs](https://www.ssb.no/en/api): public access without registration; SSB states CC BY 4.0; separate Statbank and Klass APIs.
- [SSB PxWebApi](https://www.ssb.no/en/api/pxwebapi): v2 supports GET/POST and metadata. Exact table IDs, query limits, and extraction requests remain unverified.
- [Statnett connection statistics](https://www.statnett.no/nettkapasitet-til-produksjon-og-forbruk/foresporsler-og-reservasjon-i-nettet/): manually registered inquiries since 2018, acknowledged gaps, queued/reserved/connected categories. No machine-readable endpoint or numerical capacity dataset was verified.
- NVE, SSB electricity statistics, municipal planning records, and operator filings are research candidates, not already-ingested evidence.

#### 2. Implement Fetch and Normalize Separately

- Add an SSB adapter under `src/datacenter_need/sources/ssb.py` with tests under `tests/`. These paths are proposed, not existing modules.
- Add `httpx` through uv when required. Do not install pandas or other planned libraries until the actual transformation warrants them.
- Capture raw permitted snapshots plus metadata and checksums. Keep network fetching explicit and separate from offline builds; add a fetch command only once its contract is tested.
- Use bounded requests, timeouts, and retries appropriate to the published API limits. Do not silently overwrite the last good snapshot on failure.
- Extend existing schemas only as the real source requires: classification/version, population basis, dated observations, richer benchmark metadata, and source evidence distinctions are likely additions.
- Keep the synthetic fixture as a regression example. Put real observations and assumption records in separate, clearly named data files.
- Test missing/suppressed cells, changed dimensions, unit conversion, invalid responses, source attribution, and replay from pinned snapshots without network access.

#### 3. Complete One Research Calculation

- Find a defensible request-level energy benchmark and one documented capacity or electricity observation. Capture benchmark model/version, hardware, workload, batching, context/output lengths, utilization, and measurement boundary where available.
- Do not treat GPU-only measurements as complete IT electricity. Do not derive energy from API prices or model size alone.
- Use reviewed manual extraction with exact locators if a source has no stable export. Do not invent a machine-readable endpoint.
- Preserve unknown or explicitly assumed AI usage, energy coefficients, and domestic-hosting shares. Verified employment alone does not make the resulting AI-demand estimate empirical.
- Expose the result, assumptions, missing components, and source trace in the offline artifacts. Never relabel the existing synthetic 2 GW example as a real project.

Acceptance gate: at least one actual Norwegian observation is reproducible from its archived source, and an occupation calculation can be traced through explicit assumptions to its output. Relevant tests, lint, and offline build pass. If energy or capacity evidence is unavailable, publish the gap and accurately report partial completion rather than fabricate a complete milestone. Update the source register, README notice, and implementation status accordingly.

## Remaining Roadmap

### Completed Milestone 2: Norway Coverage and Project Inventory

- Expand to nonoverlapping broad workforce coverage, with detailed task profiles for approximately 10-15 occupational groups where evidence permits. Show the uncovered remainder explicitly.
- Add national electricity production/consumption and a dated project inventory with visible completeness limits.
- Give projects and phases stable IDs and aliases. Separate construction status from grid status. Deduplicate observations of the same project across announcements, queues, reservations, and filings.
- Extend metric/boundary contracts for connection MW, installed IT MW, facility MW, actual/average load, peak demand, and annual electricity. Do not force all quantities into the current facility-capacity metric.
- Add an evidence ledger with supporting/challenging/mixed findings, methods, applicability, funding, limitations, and links to affected assumptions.
- Collect permanent FTE separately from construction jobs/job-years. Add land, taxes, value added, exports, and public infrastructure costs only with compatible definitions and periods.

Acceptance gate: published totals show coverage and dates, have no project/occupation double-counting, and remain traceable. Unknown categories cannot become zero by aggregation.

Completed 2026-09-09 as a bounded baseline. The workforce partition reconciles to the all-occupations control total, while missing annual hours and task profiles keep every broad-group energy result and the national total null. National electricity is published as two separately bounded annual observations. Project support is deliberately limited to two operator-backed identities with stable phase IDs and independent status fields; no ambiguous MW is aggregated, and national inventory completeness remains unknown.

### Completed Milestone 3: Scenarios, Hosting, and Value

- Optional scenario contracts and a dedicated engine separate scenario evaluation from the baseline calculation pipeline.
- Conservative/moderate/high adoption crossed with cloud-heavy/hybrid/local-heavy placement produces nine combinations; all scenario assumptions remain explicit.
- Seven demand categories remain separated, including explicit pre-rebound activity and additive rebound only against a documented baseline.
- Hosting conserves imports, domestic hosting, and exports; unknown residuals and gaps are retained rather than inferred as exports or waste.
- Named one-at-a-time ranges and joint stress cases are supported without claiming probability distributions or confidence intervals.
- AI-only inverse denominators and matched country/year/boundary value-resource ratios are explicit; provenance distinguishes assumptions, observations, reports, and synthetic values.

Acceptance outcome: 59 tests passed, Ruff passed, all three inputs validated and built offline, schema export succeeded, and `git diff --check` passed. The synthetic fixture exercises complete synthetic scenario coverage. Norway inputs contain no scenario configuration, remain unchanged, and do not produce a national scenario finding or a complete national total.

### Completed Milestone 4: Static Dashboard

- Static Vite vanilla TypeScript dashboard under `web/`, using Vega-Lite charts with HTML table equivalents and Lucide icons. It has no backend, runtime Python, or upstream fetching.
- Four views are implemented: Electricity & capacity; Demand & scenarios; Projects & resources; and Sources, assumptions & evidence. Benefits are explicitly absent where the source artifacts contain none.
- Norway is the default baseline. It retains `national_total_mwh: null`, `scenario: null`, explicit missing occupation calculations, no MW project totals, a non-exhaustive two-site inventory, and observed 2025 electricity only.
- The synthetic dataset is prominently labeled. It alone enables adjustable scenario workflows: adoption/placement presets, four validated overrides, compare/reset, versioned URL sharing, validated versioned JSON selection import/export, and scenario plus original occupation CSV downloads.
- `scripts/refresh_web_artifacts.py` verifies result SHA-256 values from manifests before deterministic copy/index output. `scripts/export_dashboard_vectors.py` exports authoritative Python vectors. Artifact versions are parsed strictly; incompatible artifacts, URLs, and imports are rejected.
- Browser parity covers 23 exact Python-generated golden vectors: 9 presets, 12 sensitivity points, 1 joint stress case, and 1 explicit override. Vitest also mutates unknown/null cases; PUE, rebound, hosting, provenance, and null semantics are covered.

Acceptance outcome: local verification on 2026-09-09 passed 59 Python tests and Ruff; 24 frontend unit/parity tests; 4 Playwright tests; and the frontend production build. Playwright covered 375x812 and 1440x1000 viewports, keyboard navigation, no document overflow, nonblank SVG marks, Norway missing states, and synthetic resource values. Manual screenshots at both target widths were inspected as readable and nonoverlapping. `git diff --check` also passed earlier. The Vite build warns that the lazy-loaded Vega embed chunk is about 850 KB while the main UI bundle is about 40 KB; this is a non-blocking Milestone 5 performance follow-up, not a correctness gap.

### Milestone 5: Public Release and Contributions

- Extend existing CI with artifact reproducibility, browser tests, and parity checks. Live source smoke tests belong to a separate refresh workflow, not deterministic offline tests. This CI integration has not been implemented.
- Add reviewed manual source refresh first; scheduled refreshes may later propose changes, never silently replace published evidence or assumptions.
- Confirm repository ownership/settings and publication authorization before deployment. Implement Pages base-path/static navigation support and publish versioned validated artifacts from a trusted branch.
- Keep least-privilege permissions and publishing credentials away from untrusted pull requests. Preserve the last good release and provide change history.
- Add contribution examples/templates for source corrections, alternative assumptions, benchmarks, and country adapters.
- Resolve project code/data licensing with the owner before public release. No license has been granted by this implementation; source licenses remain independent. Do not redistribute restricted documents or personal data.

Acceptance gate: clean-checkout builds work, a second reader can reproduce a result from its source, public navigation works, and licensing/coverage limitations are visible.

### Later Research

Add a real second country, detailed traditional-cloud/HPC/storage/video/telecom workloads, consumer demand, training and multimodal models, local capability trends, and regional grid/sovereignty/resilience constraints. Add probabilistic uncertainty only with defensible distributions and correlations. These are not prerequisites for the first honest, limited public release.

## Accounting Rules to Preserve

- Annual requests = employed people x annual hours/person x digital-time fraction x AI-active fraction of digital time x requests/AI-active hour. Adoption appears once. Headcount and FTE require their matching hours basis.
- Placement shares sum to one. Local energy is separate from cloud energy and is not zero.
- PUE applies once to cloud IT electricity, never again to facility-metered electricity and never to local devices.
- Annual MWh divided by calendar-year hours gives annual-average MW. Modeled energy implies modeled load, not measured use. Equivalent capacity additionally requires a positive explicit load factor; reserves and peak sizing are separate.
- The synthetic 2,000 MW full-year example equals 17.52 TWh in a 365-day year. It is a conversion test, not a Norwegian capacity claim.
- Occupational inference is only part of demand. Neither a small estimate nor a large planned facility alone proves excess capacity, useful societal demand, or export orientation.
- All public results retain source/assumption provenance, date, definition, unit, geography, measurement boundary, uncertainty or its absence, and coverage limitations.

## Delegation and Working Preferences

- User explicitly prefers cheaper subagents: `GPT-5.6 Sol (copilot)` for implementation, `GPT-5.6 Terra (copilot)` for simpler tasks such as docs and CI.
- Both full identifiers were accepted by `runSubagent` in this session. Bare `sol` was rejected. If unavailable in the new session, tell the user rather than silently select an expensive substitute.
- Split independent tasks by file ownership; the main assistant integrates and validates delegated output. Subagent summaries are not a substitute for running the integrated checks.
- Keep changes incremental and run the narrowest relevant test immediately after substantive edits. Do not perform unrelated cleanup or revert user changes.
- No need to reload the old chat or session memory: this document and the repository are the handoff. Update this file and the status document at each completed milestone.