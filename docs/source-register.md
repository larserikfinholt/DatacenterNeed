# Source Register

Checked: 2026-09-08. This register records only facts verified during initial planning. It is not a data inventory and contains no numerical observations.

## Verified access and terms

| Source | Verified fact | Use status |
| --- | --- | --- |
| [SSB API](https://www.ssb.no/en/api) | Public API; no signup stated. SSB states CC BY 4.0. Statbank and Klass are separate APIs. | Candidate for audited retrieval. Verify each dataset and reuse condition. |
| [SSB PxWebApi](https://www.ssb.no/en/api/pxwebapi) | Current PxWebApi v2 supports GET and POST. | Candidate interface; exact tables, queries, and limits remain unverified. |
| [Statnett grid requests and reservations](https://www.statnett.no/nettkapasitet-til-produksjon-og-forbruk/foresporsler-og-reservasjon-i-nettet/) | Inquiries have been manually registered since 2018; missing data is acknowledged. Queued, reserved, and connected cases are described. | Review official exports or manual evidence. No machine endpoint has been verified. |

Do not infer table IDs, observations, licenses beyond the verified SSB statement, query limits, or an undocumented endpoint. Each acquired number needs a dated snapshot, exact locator/query, checksum where allowed, and a record of its boundary and license.

## Research backlog

| Topic | Needed audit |
| --- | --- |
| Electricity | NVE and SSB observations for production, consumption, and definitions. |
| Employment and hours | SSB sources for workforce counts and annual hours, including population basis. |
| Occupations | STYRK08/ISCO08 classification and mapping verification through SSB Klass; do not substitute industry data. |
| Capacity and projects | Primary project documents and Statnett evidence, with phases and grid status kept distinct. |
| Energy benchmarks | Independently inspect workload, model, hardware, utilization, and IT versus facility boundary. |
| Employment and value | Project documentation and job metrics separating construction work from permanent FTE. |

## Snapshot rules

Keep raw snapshots only when redistribution is allowed. Otherwise retain a locator, retrieval instructions, checksum where lawful, and reproduction limitation. Source updates are reviewed changes, never silent replacements. Missing evidence is recorded as unknown rather than estimated by default.

For a future audit, capture the published date, retrieval date, exact table or page locator, filters, classification/version, revision status, and whether the source reports a stock, a flow, a connection, or a facility measure. Preserve source wording where it defines a boundary; normalize units only with a reproducible conversion.