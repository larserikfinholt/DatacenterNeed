# Implementation Status

## Foundation

- [x] Python schemas and validation
- [x] Pure calculation functions
- [x] CLI validation and deterministic offline build artifacts
- [x] Methodology and source register
- [x] Tested locally; final integrated run pending

The test model uses synthetic fixtures only. It is not a national finding: all NO/SE fixture values are synthetic, and `national_total` is `null`.

## Not Yet Implemented

- [ ] Audited SSB source adapter
- [ ] Audited empirical data
- [ ] Scenario modeling
- [ ] Web dashboard
- [ ] Deployment

## Next Milestone

Deliver one exact, verified source slice with replayable provenance, then build the frontend on the resulting artifact contract.