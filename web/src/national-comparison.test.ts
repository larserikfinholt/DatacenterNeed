import { describe, expect, it } from 'vitest'
import { adoptionForYear, aiShareOfCommitted, buildNationalComparison } from './national-comparison'
import type { Occupation } from './workforce'

const developer: Occupation = {
  code: '2512', title: 'Utvikler', fte: 100,
  factors: { low: 1, base: 1, high: 1 }, rationale: 'Reference',
}

describe('national comparison', () => {
  it('ramps from current to target adoption over one year and then stays constant', () => {
    expect(adoptionForYear(2025, 2025, 20, 60)).toBe(20)
    expect(adoptionForYear(2026, 2025, 20, 60)).toBe(60)
    expect(adoptionForYear(2030, 2025, 20, 60)).toBe(60)
  })

  it('supports a multi-year adoption ramp', () => {
    expect(adoptionForYear(2025, 2025, 20, 100, 2)).toBe(20)
    expect(adoptionForYear(2026, 2025, 20, 100, 2)).toBe(60)
    expect(adoptionForYear(2027, 2025, 20, 100, 2)).toBe(100)
  })

  it('keeps capacity statuses additive and calculates the committed-capacity share', () => {
    const result = buildNationalComparison([developer], 20, 60, 'base',
      { watts: 220, annualHours: 1725 }, 'none', [
        { year: 2025, existingMw: 10, committedAdditionalMw: 0, announcedAdditionalMw: 0 },
        { year: 2026, existingMw: 10, committedAdditionalMw: 5, announcedAdditionalMw: 20 },
      ])
    expect(result[1].committedTotalMw).toBe(15)
    expect(result[1].includingAnnouncedMw).toBe(35)
    expect(result[1].aiTwh).toBeCloseTo(result[1].aiAnnualAverageMw! * 8760 / 1e6)
    expect(result[1].aiMw).toBeGreaterThan(result[1].aiAnnualAverageMw!)
    expect(aiShareOfCommitted(result[1])).toBeCloseTo(result[1].aiMw! / 15 * 100)
  })
})