// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import indexFixture from '../public/artifacts/v1/index.json'
import norwayFixture from '../public/artifacts/v1/norway-2025/result.json'
import syntheticFixture from '../public/artifacts/v1/synthetic/result.json'
import referenceFixture from '../public/artifacts/v1/developer-reference/result.json'
import { mountDashboard } from './app'
import { parseArtifactIndex, parseCalculationResult, parseDeveloperReferenceResult } from './artifacts'
import {
  buildDashboardUrl,
  DEFAULT_SYNTHETIC_SELECTION,
  parseDashboardUrl,
  scenarioResultToCsv,
  scenarioSelectionDownload,
} from './dashboard'
import { evaluateDashboardScenario } from './scenario'

const index = parseArtifactIndex(indexFixture)
const results = new Map([
  ['norway-2025', parseCalculationResult(norwayFixture)],
  ['synthetic', parseCalculationResult(syntheticFixture)],
])
const reference = parseDeveloperReferenceResult(referenceFixture)

function mount(url = 'https://example.test/'): HTMLElement {
  const root = document.createElement('div')
  document.body.replaceChildren(root)
  mountDashboard(root, { index, results, reference, initialUrl: url, embedCharts: false })
  return root
}

beforeEach(() => vi.restoreAllMocks())

describe('dashboard DOM', () => {
  it('defaults to Norway and renders missing capacity as unavailable rather than zero', () => {
    const root = mount()

    expect(root.querySelector<HTMLSelectElement>('#dataset')?.value).toBe('norway-2025')
    expect(root.textContent).toContain('Capacity unavailable')
    expect(root.textContent).toContain('Absence is not rendered as zero')
    expect(root.textContent).toContain('161,793')

    root.querySelector<HTMLButtonElement>('[data-view="demand"]')?.click()
    expect(root.textContent).toContain('No national AI-energy estimate')
    expect(root.textContent).toContain('No scenario configuration')
  })

  it('switching to synthetic exposes the scenario editor', () => {
    const root = mount()
    const select = root.querySelector<HTMLSelectElement>('#dataset')!
    select.value = 'synthetic'
    select.dispatchEvent(new Event('change', { bubbles: true }))
    root.querySelector<HTMLButtonElement>('[data-view="demand"]')?.click()

    expect(root.querySelector('#scenario-editor-title')?.textContent).toBe('Scenario controls')
    expect(root.querySelectorAll('[data-override]')).toHaveLength(8)
    expect(root.textContent).toContain('not probabilities or confidence intervals')
  })

  it('shows computed synthetic resource outputs in the projects view', () => {
    const root = mount('https://example.test/?dataset=synthetic&view=projects')

    expect(root.textContent).toContain('Synthetic inverse allocation')
    expect(root.textContent).toContain('1,825,000')
    expect(root.textContent).toContain('Synthetic value-resource ratio')
    expect(root.textContent).toContain('10 permanent_jobs/facility_MW')
    expect(root.textContent).not.toContain('Unavailable Not reported')
  })

  it('renders the standalone developer reference view', () => {
    const root = mount('https://example.test/?view=reference')
    expect(root.textContent).toContain('Developer AI power reference')
    expect(root.textContent).toContain('Heavy two-job stress')
    expect(root.textContent).toContain('Capacity is not presented as a measured')
    root.querySelector<HTMLSelectElement>('#reference-scenario')!.value = 'heavy'
    root.querySelector<HTMLSelectElement>('#reference-scenario')!.dispatchEvent(new Event('change', { bubbles: true }))
    expect(root.textContent).toContain('unknown')
  })

  it('rejects an incompatible imported selection in the editor', async () => {
    const root = mount('https://example.test/?dataset=synthetic&view=demand')
    const input = root.querySelector<HTMLInputElement>('#import-selection')!
    const file = new File(
      [JSON.stringify({ ...DEFAULT_SYNTHETIC_SELECTION, schemaVersion: '2.0' })],
      'selection.json',
      { type: 'application/json' },
    )
    Object.defineProperty(input, 'files', { value: [file] })
    input.dispatchEvent(new Event('change', { bubbles: true }))

    await vi.waitFor(() =>
      expect(root.querySelector('#scenario-message')?.textContent).toContain('Import rejected'),
    )
  })
})

describe('URL and downloads', () => {
  it('parses and rebuilds a complete versioned URL', () => {
    const url = buildDashboardUrl(
      'https://example.test/explorer',
      'synthetic',
      'demand',
      DEFAULT_SYNTHETIC_SELECTION,
    )
    const parsed = parseDashboardUrl(new URL(url).search, ['synthetic', 'norway-2025'])

    expect(parsed).toMatchObject({
      datasetId: 'synthetic',
      view: 'demand',
      selection: DEFAULT_SYNTHETIC_SELECTION,
      warning: null,
    })
  })

  it('rejects future URL versions and falls back to validated defaults', () => {
    const parsed = parseDashboardUrl('?v=2.0&dataset=synthetic&view=demand', [
      'synthetic',
      'norway-2025',
    ])

    expect(parsed.warning).toContain('Unsupported dashboard URL version')
    expect(parsed.selection).toEqual(DEFAULT_SYNTHETIC_SELECTION)
  })

  it('creates versioned JSON and CSV downloads with nulls left empty', () => {
    const result = evaluateDashboardScenario(
      {
        datasetId: 'synthetic',
        inputTrace: syntheticFixture.input_trace,
        occupations: syntheticFixture.occupations,
      },
      DEFAULT_SYNTHETIC_SELECTION,
    )
    const download = scenarioSelectionDownload(DEFAULT_SYNTHETIC_SELECTION)
    const csv = scenarioResultToCsv(result)

    expect(download.filename).toBe('synthetic-scenario-selection-v1.0.json')
    expect(JSON.parse(download.content)).toEqual(DEFAULT_SYNTHETIC_SELECTION)
    expect(csv).toContain('category,cloud_facility_mwh,local_device_mwh')
    expect(csv.split('\n')).toHaveLength(9)
    expect(csv).not.toContain('null')
  })
})