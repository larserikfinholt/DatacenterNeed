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

Verified 2026-09-09 on Windows: 59 tests passed and Ruff passed; synthetic, `software-developers-2025`, and `norway-2025` inputs all validated and built offline; schema export and `git diff --check` passed. This is local verification only: it does not establish real national Norway scenario findings, deployment, frontend work, or remote CI.

## Not Yet Implemented

- [ ] Web dashboard
- [ ] Deployment

## Next Milestone

Implement Milestone 4 as a static dashboard from versioned artifacts. Preserve source, unit, date, boundary, provenance, uncertainty, and coverage states; do not render invented national Norway scenario figures or conceal null/incomplete results.

See the [implementation plan and session handoff](implementation-plan.md) for the complete remaining roadmap, acceptance gates, model preferences, and a prompt for the next coding session.