# Occupation factors: Developer Reference scaling

Checked: 2026-09-10. Status: research and an unreviewed scenario starter, not a
national demand estimate. The frontend now implements this scaling chain as a
partial conditional scenario; the Python calculation engine is unchanged.

The frontend defaults to 50% adoption, base occupation factors, baseline Developer
Reference power (220 W IT per active developer) and an editable assumption of
1,725 active hours per FTE-year. This annual-hours assumption is not measured by
SSB. The same time basis applies to reference and occupation FTE. PUE and idle
energy outside active hours are excluded, explicitly, rather than silently
allocated. Alternative factor profiles, reference scenarios and annual hours are
separate sensitivity controls. No national extrapolation is performed.

## Recommended model

Use a heavy AI-using developer as the normalized reference of 1.0. Do not estimate
tokens, model mix or requests separately for every occupation. The occupation
factor represents the relative inference energy per adopted FTE on the same
annual-hours basis as the developer, not the fraction of jobs eliminated.

`developer_equivalent_fte = sum(fte * occupation_factor * adoption)`

Adoption is the share of occupation FTE using AI at the intensity represented by
the factor. Do not multiply by another digital-task or AI-task fraction: that
would discount the same potential twice. Factor 1.0 is a chosen scenario ceiling,
not evidence that no occupation can ever exceed a developer's consumption.

## Files and coverage

- [Combined table](../data/norway/occupation-workforce-factors-2025-v0.csv): 407
  four-digit STYRK-08 rows, including unspecified occupation 0000. SSB's reported
  employee count for 2025 Q4 and FTE for each quarter of 2025 are retained.
- [Editable factors](../data/norway/occupation-factors-v0.csv): 22 occupation
  profiles with low/base/high factors, qualitative potential and a rationale.
  These are AI-assisted project proposals, not reviewed expert estimates.
- [Source manifest](../data/sources/ssb/occupation-workforce-2025/manifest.json):
  exact query, date, boundaries, license and SHA-256 checksums. The adjacent raw
  JSON-stat2 data and metadata retain source labels, notes and missing-cell status.
- [Offline exporter](../scripts/export_occupation_starter.ps1): rebuilds the
  combined table from the pinned raw data and editable factors. Run from the
  repository root in PowerShell: `./scripts/export_occupation_starter.ps1`.

All factors are dimensionless assumptions conditional on full adoption. Missing
factors remain blank with `factor_status=not_assessed`, never zero. Import STYRK
codes as text to preserve leading zeros. CSV numbers use a decimal point.

The annual FTE proxy is the arithmetic mean of all four quarterly
`HeltidsEkvMnd` values. It is left blank if any quarter is missing. This is an
explicit approximation based on February, May, August and November snapshots,
not an SSB observation of actual annual hours or a twelve-month average.

## Verified sources

### SSB: workforce and classification

[Table 11658](https://www.ssb.no/statbank/table/11658) provides both
`Lonsstakere` (employees) and `HeltidsEkvMnd` (full-time equivalents/monthly work
units) by four-digit occupation. Use the latter for the scaling chain; do not
assume one employee equals one FTE or estimate FTE as headcount times an arbitrary
full-time share. Publication/update date: 2026-08-13; retrieved: 2026-09-10.
Publisher: Statistics Norway; source data; reuse: CC BY 4.0.

[SSB definitions](https://www.ssb.no/arbeid-og-lonn/sysselsetting/statistikk/antall-arbeidsforhold-og-lonn)
describe FTE as the sum of jobs weighted by their contractual position fraction.
Actual overtime, absence and holidays are not measured work hours in this metric.
The population includes resident and non-resident employees in Norway, not the
self-employed. The latter gap matters especially in occupations such as gardening,
farming and legal practice. This is not the complete Norwegian workforce.

[STYRK-08, classification 7](https://www.ssb.no/klass/klassifikasjoner/7), valid
from January 2011, is based on ISCO-08 but is not identical to it. For example,
Norwegian 2221 denotes specialist nurses, and 2223 denotes nurses; ISCO-08 2221
denotes nursing professionals. Do not automatically join every equal-looking code.

### ILO/NASK: evidence about potential, not energy

[Gmyrek et al., ILO Working Paper 140](https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure),
published 2025-05-20, combines task assessments, expert input and AI predictions.
The [online paper, Annex Table A1](https://webapps.ilo.org/static/english/intserv/working-papers/wp140/index.html)
provides mean exposure and standard deviation by four-digit ISCO-08 occupation.
The paper also links to [interactive task scores](https://pgmyrek.github.io/2025_GenAI_scores_ISCO08/).
These are reported/modelled research estimates, not observed AI use in Norway.

Examples from Table A1: software developers 2512 have mean exposure 0.53;
lawyers 2611, 0.36; general office clerks 4110, 0.60; health care assistants
5321, 0.14; gardeners 6113, 0.18; nursing professionals 2221, 0.25.
Exposure is neither energy demand nor a time-use fraction. Its task standard
deviation is not an uncertainty interval for our occupation factor.

In particular, lawyers are labelled "Minimal Exposure" by this index, while
office clerks have higher exposure than developers. A high lawyer energy factor
therefore remains a scenario judgement about research and drafting, not an ILO
finding. Simply dividing every ILO score by 0.53 would give gardeners about 0.34
and office clerks above 1.0; it does not establish relative compute intensity.

Use ILO to challenge and refine the occupational ordering and rationales, not as
a hidden conversion to watts. No bulk ILO dataset or paper is redistributed here;
only these attributed factual examples and locators are recorded. Dataset-specific
redistribution terms and a reviewed STYRK-08/ISCO-08 crosswalk remain to be checked
before a bulk import. No vendor energy measurement is used to set these factors.

## Initial scenarios

All factors below are project assumptions (`occupation-factor-assumptions-v0`),
proposed 2026-09-10 for Norway using 2025 workforce data. They are conditional
planning bounds, not confidence intervals or measured shares. There is no fitted
conversion from ILO exposure to these factors, and no independent validation or
external commissioning/funding evidence is recorded for the proposals.

| STYRK-08 | Occupation | Annual FTE proxy | Low | Base | High |
| --- | --- | ---: | ---: | ---: | ---: |
| 2512 | Software developers | 7,954.25 | 1.00 | 1.00 | 1.00 |
| 2611 | Lawyers/legal professionals | 11,178.50 | 0.30 | 0.60 | 0.80 |
| 4110 | General office clerks | 47,175.00 | 0.25 | 0.45 | 0.65 |
| 2341 | Primary school teachers | 73,851.00 | 0.10 | 0.25 | 0.45 |
| 2223 | Nurses | 54,142.50 | 0.05 | 0.12 | 0.25 |
| 5321 | Health care assistants | 79,177.25 | 0.02 | 0.05 | 0.12 |
| 6113 | Gardeners | 5,947.75 | 0.01 | 0.03 | 0.08 |
| 9112 | Cleaners in establishments | 46,392.75 | 0.00 | 0.01 | 0.04 |

Do not put all health occupations into the same low-intensity bucket. Nursing,
medical documentation and direct personal care have different opportunities.
Likewise, an ordinary developer occupation includes non-adopters: factor 1.0
defines adopted reference intensity, while adoption is still applied separately.

For an initial sensitivity exercise, use adoption 0.20 / 0.50 / 0.80 as explicit
low/base/high assumptions, applied uniformly. These are illustrative planning
scenarios without a forecast year, not SSB measurements or an adoption forecast.
Vary adoption while holding the base occupation factors fixed first; vary the
factor range separately to see which assumption drives the result.

## Power and energy boundary

The current [developer reference input](../data/examples/developer-reference.yaml)
still uses synthetic power assumptions and has unresolved capacity evidence. It
is not yet the empirical calibration sought here. Keep those engineering checks
inside the reference, without duplicating its workload model for each occupation.

If `P_dev` is mean IT watts per active developer during the reference workday and
`H` is compatible annual active hours per FTE:

`annual_kwh = P_dev * H * developer_equivalent_fte / 1000`

`annual_average_w = P_dev * H * developer_equivalent_fte / 8760` (2025)

Alternatively, calibrate annual kWh per reference FTE directly and multiply by
developer-equivalent FTE. Use a separately justified hours ratio only when the
occupation and reference annual-hours bases differ. Do not apply both an annual
energy calibration and the hours correction a second time. Allocate off-hours
idle energy explicitly if it is not already in the calibration. Apply PUE once
for facility energy, or not at all if the reference already includes it.

Neither formula estimates peak demand. Peak/grid sizing additionally requires a
concurrency/load-shape assumption and capacity evidence; annual FTE cannot tell
us how many workers or AI jobs run at the same instant. Demand attributable to
Norwegian workers also does not establish where that compute is hosted.

## Audit and remaining work

The 407 detailed rows reconcile to 2,839,036 employees in 2025 Q4, exactly the
separately reported control total. Known Q4 FTE sum to 2,477,013 versus the
control's 2,477,036: a difference of -23. Missing cells and disclosure/rounding
effects prevent exact FTE reconciliation; the precise contribution of each is
unknown. No balancing value has been invented.

Fourteen rows lack at least one quarterly FTE value. The sum of the available
annual proxies is 2,465,032.25, not a complete national annual total. The 22
assessed occupations cover 752,935 of those proxy FTE (about 30.5%); 385 codes
remain without a factor, including unspecified occupations. An aggregate of only
assessed rows must be labelled partial, never total AI demand for Norway.

Next: review factors with occupation-specific task evidence and practitioners;
extend the table using an explicit STYRK-08/ISCO-08 crosswalk; resolve missing
cells and self-employed coverage; calibrate developer energy on a consistent
annual basis. No per-occupation token model is needed for this chain.