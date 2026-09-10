import { describe, expect, it } from 'vitest'

import indexFixture from '../public/artifacts/v1/index.json'
import norwayFixture from '../public/artifacts/v1/norway-2025/result.json'
import syntheticFixture from '../public/artifacts/v1/synthetic/result.json'
import referenceFixture from '../public/artifacts/v1/developer-reference/result.json'
import {
  ArtifactValidationError,
  parseArtifactIndex,
  parseCalculationResult,
  parseDeveloperReferenceResult,
} from './artifacts'

describe('artifact fixtures', () => {
  it('loads the copied index and Norway baseline with preserved nulls', () => {
    const index = parseArtifactIndex(indexFixture)
    const norway = parseCalculationResult(norwayFixture)

    expect(index.datasets).toHaveLength(2)
    expect(index.datasets.find(({ id }) => id === 'norway-2025')?.kind).toBe(
      'observed-baseline',
    )
    expect(norway.countries[0].national_total_mwh).toBeNull()
    expect(norway.scenario).toBeNull()
  })

  it('loads the synthetic dataset kind and scenario', () => {
    const index = parseArtifactIndex(indexFixture)
    const synthetic = parseCalculationResult(syntheticFixture)

    expect(index.datasets.find(({ id }) => id === 'synthetic')?.kind).toBe('synthetic')
    expect(synthetic.scenario).not.toBeNull()
  })

  it('loads the standalone developer reference and preserves evidence gaps', () => {
    const reference = parseDeveloperReferenceResult(referenceFixture)
    expect(reference.reference_id).toBe('glm-5.3-flash-h100-8')
    expect(reference.scenarios).toHaveLength(3)
    expect(reference.evidence_gaps.length).toBeGreaterThan(0)
  })
})

describe('parseArtifactIndex', () => {
  it('rejects incompatible schema versions', () => {
    const incompatible = {
      datasets: [
        {
          id: 'future',
          title: 'Future dataset',
          kind: 'synthetic',
          country: 'NO',
          year: 2025,
          schemaVersion: '2.0',
          modelVersion: '1.0',
          paths: {
            result: '/result.json',
            manifest: '/manifest.json',
            occupationBreakdown: '/occupation_breakdown.csv',
          },
        },
      ],
    }

    expect(() => parseArtifactIndex(incompatible)).toThrow(ArtifactValidationError)
  })

  it('rejects incompatible result model versions', () => {
    const incompatible = structuredClone(syntheticFixture) as Record<string, unknown>
    incompatible.model_version = '2.0'

    expect(() => parseCalculationResult(incompatible)).toThrow(ArtifactValidationError)
  })
})