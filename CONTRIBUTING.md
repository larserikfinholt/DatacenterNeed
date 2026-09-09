# Contributing

Contributions improve the evidence record and assumptions through Git pull-request review. Do not silently overwrite existing source data or assumptions.

## Data and assumption submissions

For every submitted number or assumption, include:

- source and retrieval date;
- metric definition, unit, geography, and measurement boundary;
- reference period and data age;
- license/provenance and relevant funding or conflict information;
- uncertainty statement, or the reason it is unknown;
- raw snapshot checksum and locator when storage is allowed;
- classification as `synthetic`, `assumption`, or `source data`.

State whether worker figures are headcount, jobs, or FTE. Keep connection capacity, IT load, facility load, actual average load, and annual energy distinct. Identify overlapping occupational groups, project phases, or grid statuses before aggregation.

Synthetic fixtures are demonstrations only. Do not present them as observations or use them to infer national demand. Do not insert secrets, personal data, restricted content, or copied restricted PDFs. Do not add license headers unless the repository owner has agreed to them.

## Review expectations

Reviewers check that a claim can be traced to its source or is clearly an assumption; its license permits the proposed handling; units, definitions, time, geography, and boundary are compatible; and missing values remain unknown. Reviews should seek both supporting and disconfirming evidence and flag vendor-funded material.

Construction employment and permanent FTE are reviewed separately. Taxes, turnover, exports, and GDP/value added are not additive benefits without a defensible non-overlap argument. Scenario intervals are conditional ranges, not confidence intervals or arbitrary probabilities.

When correcting a source, submit the old and proposed values or records, the reason for the change, and updated provenance. A reviewer should be able to reproduce the proposed extraction or identify why reproduction is limited.

## Local checks

The main integration work will provide these checks. This document does not claim they have been run here.

```powershell
uv sync --frozen
uv run pytest
uv run ruff check .
uv run datacenter-need fetch-ssb
```

`fetch-ssb` is the only live-source check. Review its changed snapshot and manifest before submission; deterministic tests and builds replay the committed snapshot without network access.