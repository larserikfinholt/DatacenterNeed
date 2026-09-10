# Implementation Status

## Foundation

- [x] Python schemas and validation
- [x] Pure calculation functions
- [x] CLI validation and deterministic offline build artifacts
- [x] Methodology and source register
- [x] Final integrated local verification: 22 tests passed, Ruff passed, frozen installation and offline build succeeded (2026-09-08)

## Verified Norwegian Data

- [x] Audited SSB PxWebApi v2 adapter and explicit `fetch-ssb` command
- [x] Atomic, checksummed snapshot for table 11658, STYRK-08 2512, 2025 Q4
- [x] One observed Norwegian employee count replayable without network access
- [x] One traced occupation calculation with annual hours and AI usage visibly marked as assumptions
- [x] Facility-boundary request benchmark with disclosed and missing conditions recorded

Verified 2026-09-09: 33 tests and Ruff pass; frozen installation, both input validations, both offline builds, and schema export succeed. The slice contains 8,224 observed employees and an illustrative result of 1.70532864 MWh. This is one occupation scenario, not a national estimate.

## Milestone 2: Norway Coverage and Project Inventory

- [x] Audited 2025 Q4 SSB workforce frame with nine disjoint broad groups and explicit `0b` uncovered category
- [x] Exact reconciliation: 2,830,506 modeled-group employees plus 8,530 unidentifiable equals 2,839,036 employees
- [x] Unknown annual hours and task profiles remain null; no national occupational AI-energy total is produced
- [x] Audited 2025 SSB annual electricity: 161,793 GWh production and 130,125 GWh net consumption
- [x] Stable project/phase IDs and aliases, independent construction/grid histories, and boundary-specific quantities
- [x] Unknown-preserving project aggregation; aliases and status records cannot duplicate quantities
- [x] Evidence ledger with stance, method, applicability, funding/conflicts, limitations, and source links
- [x] Two-site operator-backed inventory pilot with explicit non-exhaustiveness and no boundary-ambiguous MW totals

Milestone 2 is complete as a bounded, traceable baseline. It does not claim comprehensive Norway project coverage or estimate national AI electricity demand. The next data refresh should add municipal/grid corroboration and reviewed occupation assumptions as evidence permits.

Verified 2026-09-09: 43 tests and Ruff pass; frozen installation, synthetic and both Norway validations/builds, archived snapshot replay, and schema export succeed.

The test model uses synthetic fixtures only. It is not a national finding: all NO/SE fixture values are synthetic, and `national_total` is `null`.

## Milestone 3: Scenarios, Hosting, and Value

- [x] Optional scenario contracts and a separate scenario engine
- [x] Nine explicit presets from 3 adoption levels by 3 placement profiles
- [x] Seven separated demand categories, including pre-rebound activity and additive documented-baseline rebound
- [x] Hosting conservation across imports, domestic hosting, and exports, with unknown residuals/gaps retained
- [x] Named one-at-a-time ranges, joint stress cases, explicit AI-only inverse denominators, and matched country/year/boundary value-resource ratios
- [x] Categorized assumption, observed, reported, and synthetic provenance

Milestone 3 is complete. Unknown used activity or intensity, and incomplete occupation coverage, prevent complete national totals and complete hosting; known subtotals remain. Norway datasets have no scenario configuration, remain unchanged, and keep `national_total_mwh` null. Only `synthetic.yaml` contains explicit synthetic scenario assumptions and complete synthetic coverage.

Verified 2026-09-09 on Windows: 59 tests passed and Ruff passed; synthetic, `software-developers-2025`, and `norway-2025` inputs all validated and built offline; schema export and `git diff --check` passed. This is local verification only: it does not establish real national Norway scenario findings, deployment, or remote CI.

## Milestone 4: Static Dashboard

- [x] Static Vite vanilla TypeScript dashboard under `web/`, with no backend, runtime Python, or upstream fetching
- [x] Versioned committed artifact reader for Norway 2025 observed baseline and prominently labeled synthetic example
- [x] Manifest SHA-256 verification and deterministic artifact copy/index refresh; authoritative Python scenario-vector export
- [x] Four views: Electricity & capacity; Demand & scenarios; Projects & resources; Sources, assumptions & evidence
- [x] Norway default preserves null national total and scenario, missing occupation calculations, no MW project totals, a non-exhaustive two-site inventory, observed 2025 electricity only, and absent benefits
- [x] Synthetic-only adjustable scenarios: presets, four validated overrides, compare/reset, versioned URL sharing, validated versioned JSON selection import/export, and CSV downloads
- [x] Vega-Lite charts with HTML table equivalents, Lucide icons, strict artifact version parsing, and rejection of incompatible artifacts, URLs, and imports
- [x] Browser parity for 23 exact Python-generated golden vectors plus unknown/null mutations, covering PUE, rebound, hosting, provenance, and null semantics

Verified locally on Windows 2026-09-09: 24 frontend unit/parity tests, 4 Playwright tests, and the production frontend build passed. Playwright checks 375x812 and 1440x1000 viewports, keyboard navigation, no document overflow, nonblank SVG marks, Norway missing states, and synthetic resource values. Manual screenshots at both widths were inspected as readable and nonoverlapping. The lazy-loaded Vega embed chunk is about 850 KB while the main UI bundle is about 40 KB; this is a non-blocking performance follow-up.

## Not Yet Implemented

## Developer AI Power Reference

- [x] Stage 1 standalone contracts and pure calculations
- [x] Stage 1 focused regression tests for power, energy allocation, capacity,
  unknowns, overload, topology, memory, PUE, and token-rate semantics

Verified 2026-09-10 on Windows: 12 focused tests, 71 full Python tests, and
Ruff passed. This remains a conditional reference model; no real GLM/H100
capacity or power measurement is claimed. Stage 2 offline artifacts and Stage
3 dashboard work remain.

- [ ] Deployment
- [ ] Pages configuration, dashboard CI integration, remote CI verification, and licensing resolution

## Next Milestone

Implement Milestone 5: public release and contributions. Preserve source, unit, date, boundary, provenance, uncertainty, and coverage states; do not render invented national Norway scenario figures or conceal null/incomplete results. No deployment, Pages configuration, CI integration, remote CI verification, commit, push, or licensing resolution has been completed.

See the [implementation plan and session handoff](implementation-plan.md) for the complete remaining roadmap, acceptance gates, model preferences, and a prompt for the next coding session.