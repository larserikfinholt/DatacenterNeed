import { evaluateWorkforce, type FactorFallback, type FactorLevel, type Occupation,
  type ReferenceCalibration } from './workforce'

export interface CapacityOutlookPoint {
  year: number
  existingMw: number
  committedAdditionalMw: number
  announcedAdditionalMw: number
}

export interface NationalComparisonPoint extends CapacityOutlookPoint {
  adoptionPercent: number
  aiMw: number | null
  aiAnnualAverageMw: number | null
  aiTwh: number | null
  committedTotalMw: number
  includingAnnouncedMw: number
}

export const CAPACITY_OUTLOOK: readonly CapacityOutlookPoint[] = [
  { year: 2025, existingMw: 500, committedAdditionalMw: 0, announcedAdditionalMw: 0 },
  { year: 2026, existingMw: 500, committedAdditionalMw: 140, announcedAdditionalMw: 110 },
  { year: 2027, existingMw: 500, committedAdditionalMw: 290, announcedAdditionalMw: 260 },
  { year: 2028, existingMw: 500, committedAdditionalMw: 430, announcedAdditionalMw: 470 },
  { year: 2029, existingMw: 500, committedAdditionalMw: 560, announcedAdditionalMw: 740 },
  { year: 2030, existingMw: 500, committedAdditionalMw: 700, announcedAdditionalMw: 1100 },
]

export function adoptionForYear(year: number, startYear: number, current: number, target: number, rampYears = 1) {
  if (year <= startYear) return current
  if (rampYears <= 0 || year >= startYear + rampYears) return target
  return current + (target - current) * (year - startYear) / rampYears
}

export function buildNationalComparison(
  occupations: readonly Occupation[],
  currentAdoption: number,
  targetAdoption: number,
  factorLevel: FactorLevel,
  reference: ReferenceCalibration,
  factorFallback: FactorFallback = 'none',
  capacity = CAPACITY_OUTLOOK,
  adoptionRampYears = 1,
): NationalComparisonPoint[] {
  const startYear = capacity[0]?.year ?? 2025
  return capacity.map((point) => {
    const adoptionPercent = adoptionForYear(point.year, startYear, currentAdoption, targetAdoption, adoptionRampYears)
    const estimate = evaluateWorkforce(occupations, adoptionPercent, factorLevel, reference, factorFallback)
    return {
      ...point,
      adoptionPercent,
      aiMw: estimate.activeMw,
      aiAnnualAverageMw: estimate.mw,
      aiTwh: estimate.gwh === null ? null : estimate.gwh / 1000,
      committedTotalMw: point.existingMw + point.committedAdditionalMw,
      includingAnnouncedMw: point.existingMw + point.committedAdditionalMw + point.announcedAdditionalMw,
    }
  })
}

export function aiShareOfCommitted(point: NationalComparisonPoint) {
  return point.aiMw === null || point.committedTotalMw <= 0
    ? null : point.aiMw / point.committedTotalMw * 100
}