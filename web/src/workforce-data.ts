import { csvParse } from 'd3-dsv'
import workforceCsv from '../../data/norway/occupation-workforce-factors-2025-v0.csv?raw'
import factorsCsv from '../../data/norway/occupation-factors-v0.csv?raw'
import referenceResult from '../public/artifacts/v1/developer-reference/result.json'
import referenceTrace from '../public/artifacts/v1/developer-reference/trace.json'
import type { FactorLevel, Occupation } from './workforce'

function numeric(value: string | undefined): number | null {
  if (value === undefined || value.trim() === '') return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) throw new Error('Ugyldig tall i yrkesgrunnlaget.')
  return parsed
}

export function parseOccupations(workforce: string, factors: string): Occupation[] {
  const profiles = csvParse(factors)
  const byCode = new Map(profiles.map((row) => [row.styrk08_code, row]))
  if (byCode.size !== profiles.length) throw new Error('Dupliserte faktorprofiler.')
  const seen = new Set<string>()
  const occupations = csvParse(workforce).map((row): Occupation => {
    const code = row.styrk08_code
    if (!/^\d{4}$/.test(code) || seen.has(code)) throw new Error('Ugyldig eller duplisert yrkeskode.')
    seen.add(code)
    const profile = byCode.get(code)
    const values = {} as Record<FactorLevel, number>
    for (const level of ['low', 'base', 'high'] as const) {
      const combined = numeric(row[`occupation_factor_${level}`])
      const source = numeric(profile?.[`occupation_factor_${level}`])
      if (combined !== source || (profile && source === null)) {
        throw new Error(`Faktorfilene avviker for ${code}.`)
      }
      if (source !== null) values[level] = source
    }
    if (profile && (values.low > values.base || values.base > values.high)) {
      throw new Error(`Ugyldig faktorintervall for ${code}.`)
    }
    if ((profile && (profile.factor_status !== 'assumption' || row.factor_status !== 'assumption')) ||
        (!profile && row.factor_status !== 'not_assessed')) {
      throw new Error(`Ugyldig faktorstatus for ${code}.`)
    }
    return { code, title: row.occupation_label_no, fte: numeric(row.annual_fte_proxy_2025),
      factors: profile ? values : null, rationale: profile?.rationale ?? '' }
  })
  if (profiles.some((profile) => !seen.has(profile.styrk08_code))) {
    throw new Error('Faktorprofil mangler i årsverkstabellen.')
  }
  return occupations
}

export const occupations = parseOccupations(workforceCsv, factorsCsv)

export function getReference(id = 'baseline') {
  const result = referenceResult.scenarios.find((scenario) => scenario.id === id)
  const trace = referenceTrace.scenarios.find((scenario) => scenario.id === id)
  if (!result || !trace || result.trace_id !== trace.trace_id ||
      referenceResult.reference_id !== referenceTrace.input.reference_id ||
      result.watts_per_active_developer !== trace.watts_per_active_developer ||
      result.workload.workday_hours !== trace.workload.workday_hours ||
      result.node_it_w / result.workload.concurrent_developers !== result.watts_per_active_developer ||
      Math.abs(result.workday_kwh_per_active_developer * 1000 / result.workload.workday_hours -
        result.watts_per_active_developer) > 1e-9) {
    throw new Error('Developer Reference har inkonsistent resultat eller sporingsgrunnlag.')
  }
  return { id, watts: result.watts_per_active_developer, traceId: result.trace_id,
    capacityStatus: result.capacity.status, capacityReason: result.capacity.unknown_reason,
    evidenceGaps: referenceResult.evidence_gaps, referenceId: referenceResult.reference_id }
}