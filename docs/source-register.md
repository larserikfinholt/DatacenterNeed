# Source Register

Checked: 2026-09-09. This register includes the deliberately narrow audited source slice below; it is not a national data inventory.

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

The occupation classification is [STYRK-08](https://www.ssb.no/en/klass/klassifikasjoner/7), classification 7, valid from January 2011 and based on ISCO-08. Code 2512 is “Software developers.” The real input is `data/norway/software-developers-2025.yaml`; annual hours and AI usage in that file are explicit project assumptions.

## Research backlog

| Topic | Needed audit |
| --- | --- |
| Electricity | NVE and SSB observations for production, consumption, and definitions. |
| Employment and hours | Expand beyond the one verified employee stock. Find occupation-compatible annual worked hours; the current 1,600 hours is explicitly assumed. |
| Occupations | STYRK08/ISCO08 classification and mapping verification through SSB Klass; do not substitute industry data. |
| Capacity and projects | Primary project documents and Statnett evidence, with phases and grid status kept distinct. |
| Energy benchmarks | Independently inspect workload, model, hardware, utilization, and IT versus facility boundary. |
| Employment and value | Project documentation and job metrics separating construction work from permanent FTE. |

## Snapshot rules

Keep raw snapshots only when redistribution is allowed. Otherwise retain a locator, retrieval instructions, checksum where lawful, and reproduction limitation. Source updates are reviewed changes, never silent replacements. Missing evidence is recorded as unknown rather than estimated by default.

For a future audit, capture the published date, retrieval date, exact table or page locator, filters, classification/version, revision status, and whether the source reports a stock, a flow, a connection, or a facility measure. Preserve source wording where it defines a boundary; normalize units only with a reproducible conversion.