import { describe, expect, it } from 'vitest'

import goldenFixture from '../public/artifacts/v1/scenario-golden.json'
import norwayFixture from '../public/artifacts/v1/norway-2025/result.json'
import syntheticFixture from '../public/artifacts/v1/synthetic/result.json'
import {
  dashboardScenarioToSearchParams,
  evaluateDashboardScenario,
  parseDashboardScenario,
  ScenarioUnavailableError,
  ScenarioValidationError,
} from './scenario'

const completeSelection = {
  schemaVersion: '1.0',
  datasetId: 'synthetic',
  adoption: 'moderate',
  placement: 'hybrid',
  overrides: {
    demandMultiplier: 1,
    cloudShare: 0.5,
    domesticHostingShare: 0.75,
    cloudPue: 1.2,
  },
}

const syntheticSource = {
  datasetId: 'synthetic',
  inputTrace: syntheticFixture.input_trace,
  occupations: syntheticFixture.occupations,
}

describe('parseDashboardScenario', () => {
  it('accepts a complete versioned selection', () => {
    expect(parseDashboardScenario(completeSelection)).toEqual(completeSelection)
  })

  it.each([
    ['negative demand', { demandMultiplier: -0.1 }],
    ['cloud share above one', { cloudShare: 1.1 }],
    ['domestic hosting share below zero', { domesticHostingShare: -0.1 }],
    ['PUE below one', { cloudPue: 0.99 }],
    ['non-finite demand', { demandMultiplier: Number.POSITIVE_INFINITY }],
  ])('rejects %s', (_label, override) => {
    const selection = {
      ...completeSelection,
      overrides: { ...completeSelection.overrides, ...override },
    }

    expect(() => parseDashboardScenario(selection)).toThrow(ScenarioValidationError)
  })

  it('requires every explicit override and rejects future versions', () => {
    const missingOverride = structuredClone(completeSelection) as Record<string, unknown>
    delete (missingOverride.overrides as Record<string, unknown>).cloudPue

    expect(() => parseDashboardScenario(missingOverride)).toThrow(ScenarioValidationError)
    expect(() =>
      parseDashboardScenario({ ...completeSelection, schemaVersion: '2.0' }),
    ).toThrow(ScenarioValidationError)
  })

  it('serializes every selection field into versioned URL parameters', () => {
    expect(Object.fromEntries(dashboardScenarioToSearchParams(completeSelection))).toEqual({
      v: '1.0',
      dataset: 'synthetic',
      adoption: 'moderate',
      placement: 'hybrid',
      demand: '1',
      cloud: '0.5',
      domestic: '0.75',
      pue: '1.2',
    })
  })
})

describe('evaluateDashboardScenario', () => {
  it('matches every Python-generated category and result field exactly', () => {
    expect(goldenFixture.vectors).toHaveLength(23)
    for (const vector of goldenFixture.vectors) {
      expect(evaluateDashboardScenario(syntheticSource, vector.selection), vector.id).toEqual(
        vector.expected,
      )
    }
  })

  it('preserves PUE boundaries, additive rebound, and hosting conservation', () => {
    const result = evaluateDashboardScenario(syntheticSource, {
      ...completeSelection,
      adoption: 'high',
    })
    const categories = new Map(result.categories.map((item) => [item.category, item]))
    const human = categories.get('occupation_human_inference')
    const training = categories.get('foundation_training')
    const background = categories.get('autonomous_background_inference')

    expect(human?.cloud_facility_mwh).toBe((human?.cloud_it_mwh as number) * 1.2)
    expect(training?.cloud_it_mwh).toBeNull()
    expect(background?.activity_units).toBe(7_000_000)
    expect(background?.rebound_activity_units).toBe(2_000_000)
    expect(
      (result.hosting?.domestically_hosted_mwh as number) +
        (result.hosting?.imported_mwh as number),
    ).toBe(result.hosting?.domestic_consumption_mwh)
  })

  it('preserves unknown activity and known subtotals without allocating hosting', () => {
    const inputTrace = structuredClone(syntheticFixture.input_trace)
    const activity = inputTrace.scenario?.adoption_presets[0].category_activities[0] as
      | { pre_rebound_activity_units: number | null; missing_reason: string | null }
      | undefined
    if (activity === undefined) {
      throw new Error('Synthetic fixture must contain the conservative activity')
    }
    activity.pre_rebound_activity_units = null
    activity.missing_reason = 'Synthetic gap'

    const result = evaluateDashboardScenario(
      { ...syntheticSource, inputTrace },
      {
        ...completeSelection,
        adoption: 'conservative',
        placement: 'cloud-heavy',
        overrides: {
          ...completeSelection.overrides,
          cloudShare: 0.9,
          domesticHostingShare: 0.3,
        },
      },
    )
    const unknown = result.categories.find(
      ({ category }) => category === 'autonomous_background_inference',
    )

    expect(unknown?.activity_units).toBeNull()
    expect(unknown?.known_total_mwh).toBeNull()
    expect(unknown?.missing_reason).toBe('Synthetic gap')
    expect(result.known_national_subtotal_mwh).not.toBeNull()
    expect(result.national_total_mwh).toBeNull()
    expect(result.hosting).toBeNull()
  })

  it('keeps a known local component when a used cloud intensity is unknown', () => {
    const inputTrace = structuredClone(syntheticFixture.input_trace)
    const intensity = inputTrace.scenario?.energy_intensities[0] as
      | { cloud_kwh_per_activity_unit: number | null; cloud_missing_reason: string | null }
      | undefined
    if (intensity === undefined) {
      throw new Error('Synthetic fixture must contain an energy intensity')
    }
    intensity.cloud_kwh_per_activity_unit = null
    intensity.cloud_missing_reason = 'No cloud coefficient'

    const result = evaluateDashboardScenario(
      { ...syntheticSource, inputTrace },
      completeSelection,
    )
    const human = result.categories.find(
      ({ category }) => category === 'occupation_human_inference',
    )

    expect(human?.cloud_facility_mwh).toBeNull()
    expect(human?.local_device_mwh).not.toBeNull()
    expect(human?.known_total_mwh).toBeNull()
    expect(human?.missing_reason).toBe('No cloud coefficient')
    expect(result.hosting).toBeNull()
  })

  it('throws an explicit unavailable state when scenario configuration is absent', () => {
    expect(() =>
      evaluateDashboardScenario(
        {
          datasetId: 'norway-2025',
          inputTrace: norwayFixture.input_trace,
          occupations: norwayFixture.occupations,
        },
        { ...completeSelection, datasetId: 'norway-2025' },
      ),
    ).toThrow(ScenarioUnavailableError)
  })
})