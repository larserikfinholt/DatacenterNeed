export type FactorLevel = 'low' | 'base' | 'high'

export interface Occupation {
  code: string
  title: string
  fte: number | null
  factors: Record<FactorLevel, number> | null
  rationale: string
}

export interface ReferenceCalibration {
  watts: number
  annualHours: number
}

export const ADOPTION_PRESETS = { low: 20, base: 50, high: 80 } as const
export const DEFAULT_ANNUAL_HOURS = 1725
export const HOURS_IN_YEAR = 8760

export function evaluateWorkforce(
  occupations: readonly Occupation[],
  adoptionPercent: number,
  factorLevel: FactorLevel,
  reference: ReferenceCalibration,
) {
  if (!Number.isFinite(adoptionPercent) || adoptionPercent < 0 || adoptionPercent > 100) {
    throw new Error('Adopsjon må være mellom 0 og 100 prosent.')
  }
  if (!Number.isFinite(reference.watts) || reference.watts < 0 ||
      !Number.isFinite(reference.annualHours) || reference.annualHours <= 0 ||
      reference.annualHours > HOURS_IN_YEAR) {
    throw new Error('Ugyldig effekt eller årlig timegrunnlag i referansen.')
  }
  const annualKwhPerFte = reference.watts * reference.annualHours / 1000
  const rows = occupations.map((occupation) => {
    const factor = occupation.factors?.[factorLevel] ?? null
    if ((occupation.fte !== null && (!Number.isFinite(occupation.fte) || occupation.fte < 0)) ||
        (factor !== null && (!Number.isFinite(factor) || factor < 0))) {
      throw new Error(`Ugyldig årsverk eller faktor: ${occupation.code}`)
    }
    const equivalents = occupation.fte === null || factor === null
      ? null : occupation.fte * factor * adoptionPercent / 100
    const gwh = equivalents === null ? null : equivalents * annualKwhPerFte / 1e6
    return { ...occupation, factor, equivalents, gwh, mw: gwh === null ? null : gwh * 1000 / HOURS_IN_YEAR }
  })
  const knownFte = rows.reduce((total, row) => total + (row.fte ?? 0), 0)
  const coveredFte = rows.reduce((total, row) => total + (row.equivalents === null ? 0 : row.fte ?? 0), 0)
  const equivalents = rows.reduce((total, row) => total + (row.equivalents ?? 0), 0)
  const hasEstimate = rows.some((row) => row.equivalents !== null)
  const gwh = hasEstimate ? equivalents * annualKwhPerFte / 1e6 : null
  return {
    rows, knownFte, coveredFte, equivalents: hasEstimate ? equivalents : null,
    annualKwhPerFte, gwh, mw: gwh === null ? null : gwh * 1000 / HOURS_IN_YEAR,
    assessedCodes: rows.filter((row) => row.factors !== null).length,
    missingFteCodes: rows.filter((row) => row.fte === null).length,
    coveragePercent: knownFte > 0 ? coveredFte / knownFte * 100 : null,
  }
}