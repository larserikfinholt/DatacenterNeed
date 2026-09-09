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

The test model uses synthetic fixtures only. It is not a national finding: all NO/SE fixture values are synthetic, and `national_total` is `null`.

## Not Yet Implemented

- [ ] Scenario modeling
- [ ] Web dashboard
- [ ] Deployment

## Next Milestone

Expand Norway coverage and project inventory without double-counting occupations or project phases. Keep unknown coverage explicit.

See the [implementation plan and session handoff](implementation-plan.md) for the complete remaining roadmap, acceptance gates, model preferences, and a prompt for the next coding session.