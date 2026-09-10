# Source Register

Checked: 2026-09-10. This register includes audited Norway workforce and electricity extracts plus a deliberately incomplete project identity sample. It is not a complete national project inventory or AI-demand estimate.

## Verified access and terms

| Source | Verified fact | Use status |
| --- | --- | --- |
| [SSB API](https://www.ssb.no/en/api) | Public API; no signup stated. SSB states CC BY 4.0. Statbank and Klass are separate APIs. | Candidate for audited retrieval. Verify each dataset and reuse condition. |
| [SSB PxWebApi](https://www.ssb.no/en/api/pxwebapi) | Current PxWebApi v2 supports GET and POST. The [v2 guide](https://www.ssb.no/en/api/pxwebapiv2) documents 800,000 cells per extract and 30 queries per minute per IP. Table 11658 was retrieved through a pinned one-cell GET query. | Implemented for one audited cell; no claim of broader table stability. |
| [Statnett grid requests and reservations](https://www.statnett.no/nettkapasitet-til-produksjon-og-forbruk/foresporsler-og-reservasjon-i-nettet/) | Inquiries have been manually registered since 2018; missing data is acknowledged. Queued, reserved, and connected cases are described. | Review official exports or manual evidence. No machine endpoint has been verified. |

Do not infer table IDs, observations, licenses beyond the verified SSB statement, query limits, or an undocumented endpoint. Each acquired number needs a dated snapshot, exact locator/query, checksum where allowed, and a record of its boundary and license.

## Audited observations and benchmarks

| ID | Value and boundary | Exact source and limitations |
| --- | --- | --- |
| `no-software-developers-2025k4` | 8,224 employees; headcount stock in the middle month of 2025 Q4; both sexes, all ages, residents and non-residents; main job per person | SSB table 11658, `Kjonn=0`, `Alder=999D`, `Yrke=2512`, `ContentsCode=Lonsstakere`, `Tid=2025K4`. Retrieved 2026-09-09 from the [pinned API query](https://data.ssb.no/api/pxwebapi/v2/tables/11658/data?lang=en&valueCodes%5BKjonn%5D=0&valueCodes%5BAlder%5D=999D&valueCodes%5BYrke%5D=2512&valueCodes%5BContentsCode%5D=Lonsstakere&valueCodes%5BTid%5D=2025K4&outputFormat=json-stat2). Snapshot SHA-256: `3201751ac6420b0b9dd1171a3e8669190d32a0294be39481352b148cec6a909b`. SSB warns that cells 1 and 2 are replaced by 0 or 3 for privacy and that occupational reporting changed materially around 2025 Q1. |
| `google-gemini-median-prompt-2025` | 0.24 Wh per median Gemini Apps text prompt in May 2025; cloud-facility boundary including accelerator, host CPU/RAM, idle capacity, and data-centre overhead | Google-authored [technical paper](https://arxiv.org/abs/2508.15734), published 2025-08-21 under CC BY 4.0. Exact model mix, hardware, batching, utilization values, and prompt/output lengths were not disclosed. Google states the point-in-time result is not representative of every prompt or future performance and was not independently verified. |
| `ssb-11658-2025k4-broad` | 2,839,036 employees: 2,830,506 in nine modeled broad groups and 8,530 in `0b`, unspecified or unidentifiable occupations | SSB table 11658, both sexes, all ages, number of employees, 2025 Q4. The ten disjoint cells reconcile exactly to the separately queried `0-9` control total, which is not added to them. Snapshot SHA-256: `fd7aa0a46cc6c9a811d1c1475acb4ae7de1f3a61fa7d500de6893996399dcfb5`. Annual hours and task profiles remain unknown. |
| `ssb-08307-2025-electricity` | 161,793 GWh total production and 130,125 GWh net consumption; annual flows for 2025 | SSB table 08307, `ProdTotal` and `Nettoforbruk`, entire year. SSB defines production as net production and net consumption as measured consumption across primary and secondary industries, tertiary industries, and households. Snapshot SHA-256: `8ba43b7a90c70d4ad9384a7cca43dba84c63f7e9eacf32817b536a11ea47ec63`. These are separate observations, not quantities to add. |

## Developer reference sources and assumptions

| ID | Use and boundary | Limitation and status |
| --- | --- | --- |
| `developer-glm-5.3-flash-model-card` | [GLM-5.3-Flash model card](https://huggingface.co/zai-org/GLM-5.3-Flash); model identity, native FP8 label, and hybrid-attention context | Vendor/model-card material is reported evidence, not an independent serving or power measurement. Matching 8-H100, 20-developer capacity remains unknown. |
| `developer-h100-sxm-specification` | [NVIDIA H100 specification](https://www.nvidia.com/en-us/data-center/h100/); H100 SXM 80 GB profile and configurable power-limit metadata | Configured TDP/power limit is not continuous inference power. SKU, form factor, engine and model precision must remain explicit. |
| `developer-synthetic-power-fixture` | Synthetic node fixture: 100 W idle/GPU, 600 W busy/GPU, 1,000 W other node IT, linear utilization fallback | Assumption only; not a measurement, confidence interval, or universal coefficient. The Stage 2 artifact applies it once at the node IT boundary and applies PUE only for the optional facility value. |

The standalone artifact at `build/developer-reference/v1/` is therefore a
conditional calculation reference. Its null memory, compatibility, and
capacity evidence are intentional unknowns, not zeros or verified performance.

The occupation classification is [STYRK-08](https://www.ssb.no/en/klass/klassifikasjoner/7), classification 7, valid from January 2011 and based on ISCO-08. Code 2512 is “Software developers.” The real input is `data/norway/software-developers-2025.yaml`; annual hours and AI usage in that file are explicit project assumptions.

The broad input is `data/norway/norway-2025.yaml`. Its nine task profiles and annual-hours observations are explicitly missing rather than estimated. The archived source bundle is under `data/sources/ssb/norway-2025-baseline/` and can be refreshed with `datacenter-need fetch-norway-baseline`.

## Limited project inventory

| Project ID | Evidence retained | Completeness limit |
| --- | --- | --- |
| `no-svg-rennesoy` | Green Mountain's current [SVG-Rennesøy](https://greenmountain.no/data-center/svg-rennesoy/) operator page describes available server rooms in the converted facility. | Operator-reported operating identity only. No municipal or grid case was audited and no public MW figure with a sufficiently clear boundary was entered. |
| `no-lefdal-mine` | Lefdal Mine Data Centers' current [facility page](https://www.lefdalmine.com/) offers data-centre services at Måløy and describes expansion potential. | Operator-reported operating identity only. The stated expansion capacity has an unclear quantity boundary and is not aggregated. |

This two-site list is a schema-backed pilot, not a census. Statnett states that its connection cases have been manually registered since 2018, may contain gaps, and currently show queued, reserved, and connected cases. Those statuses cannot be added together or treated as project identities without a reviewed alias mapping.

## Research backlog

| Topic | Needed audit |
| --- | --- |
| Electricity | Add compatible sector detail only when it does not duplicate the audited national production and net-consumption totals. |
| Employment and hours | Find occupation-compatible annual worked hours; the narrow slice's 1,600 hours remains explicitly assumed. |
| Occupations | Find reviewed task profiles for the nine broad groups; preserve `0b` as uncovered. |
| Capacity and projects | Expand beyond the two operator-backed identities using municipal primary records and reviewed Statnett aliases; retain separate phase, construction, grid, and MW boundaries. |
| Energy benchmarks | Independently inspect workload, model, hardware, utilization, and IT versus facility boundary. |
| Employment and value | Project documentation and job metrics separating construction work from permanent FTE. |

## Snapshot rules

Keep raw snapshots only when redistribution is allowed. Otherwise retain a locator, retrieval instructions, checksum where lawful, and reproduction limitation. Source updates are reviewed changes, never silent replacements. Missing evidence is recorded as unknown rather than estimated by default.

For a future audit, capture the published date, retrieval date, exact table or page locator, filters, classification/version, revision status, and whether the source reports a stock, a flow, a connection, or a facility measure. Preserve source wording where it defines a boundary; normalize units only with a reproducible conversion.