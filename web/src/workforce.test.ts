import { describe, expect, it } from 'vitest'
import { evaluateWorkforce, type Occupation } from './workforce'
import { getReference, occupations, parseOccupations } from './workforce-data'

const developer: Occupation = {
  code: '2512', title: 'Utvikler', fte: 1,
  factors: { low: 1, base: 1, high: 1 }, rationale: 'Reference',
}
const calibration = { watts: 220, annualHours: 1725 }

describe('workforce energy scaling', () => {
  it('reconciles the pinned workforce coverage and reference trace', () => {
    const result = evaluateWorkforce(occupations, 50, 'base', calibration)
    expect(occupations).toHaveLength(407)
    expect(occupations[0].code).toBe('0000')
    expect(result.assessedCodes).toBe(22)
    expect(result.missingFteCodes).toBe(14)
    expect(result.knownFte).toBe(2465032.25)
    expect(result.coveredFte).toBe(752935)
    expect(result.rows.filter((row) => row.factor === null)).toHaveLength(385)
    expect(getReference().watts).toBe(220)
    expect(getReference().capacityStatus).toBe('unknown')
    expect(getReference('heavy').watts).toBe(270)
    expect(() => getReference('missing')).toThrow()
  })
  it('rejects inconsistent CSV sources', () => {
    expect(() => parseOccupations('styrk08_code,occupation_factor_base\n2512,0.5',
      'styrk08_code,occupation_factor_base\n2512,1')).toThrow()
  })
  it('uses annual active hours exactly once and calendar hours for mean power', () => {
    const result = evaluateWorkforce([developer], 100, 'base', calibration)
    expect(result.annualKwhPerFte).toBe(379.5)
    expect(result.gwh).toBe(0.0003795)
    expect(result.mw).toBeCloseTo(0.3795 / 8760, 12)
  })
  it('scales adoption and factors independently', () => {
    const rows = [{ ...developer, fte: 100, factors: { low: 0.2, base: 0.5, high: 0.8 } }]
    expect(evaluateWorkforce(rows, 40, 'base', calibration).gwh)
      .toBe(evaluateWorkforce(rows, 20, 'base', calibration).gwh! * 2)
    expect(evaluateWorkforce(rows, 40, 'high', calibration).equivalents).toBe(32)
  })
  it('extrapolates unassessed occupations only when explicitly selected', () => {
    const weighted = evaluateWorkforce(occupations, 50, 'base', calibration, 'fte-weighted-mean')
    const unweighted = evaluateWorkforce(occupations, 50, 'base', calibration, 'unweighted-mean')
    expect(weighted.fallbackFactor).toBeCloseTo(0.245463)
    expect(weighted.extrapolatedCodes).toBe(385)
    expect(weighted.coveragePercent).toBeCloseTo(30.5446)
    expect(weighted.gwh).toBeCloseTo(114.8127, 4)
    expect(weighted.activeMw).toBeCloseTo(66.5581, 4)
    expect(unweighted.fallbackFactor).toBeCloseTo(0.368182)
    expect(unweighted.gwh).toBeCloseTo(154.6805, 4)
  })
  it('keeps missing values unknown, including at zero adoption', () => {
    const missingFactor = { ...developer, code: '0000', factors: null }
    const missingFte = { ...developer, code: '0110', fte: null }
    const result = evaluateWorkforce([developer, missingFactor, missingFte], 0, 'base', calibration)
    expect(result.rows.map((row) => row.gwh)).toEqual([0, null, null])
    expect(result.coveragePercent).toBe(50)
    expect(result.missingFteCodes).toBe(1)
    expect(evaluateWorkforce([missingFactor], 50, 'base', calibration).gwh).toBeNull()
  })
  it.each([-1, 101, NaN, Infinity])('rejects invalid adoption %s', (adoption) => {
    expect(() => evaluateWorkforce([developer], adoption, 'base', calibration)).toThrow()
  })
})