// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { csvParse } from 'd3-dsv'
import { mountWorkforce } from './workforce-app'
import { triggerTextDownload } from './dashboard'

vi.mock('./dashboard', () => ({ triggerTextDownload: vi.fn() }))
let root: HTMLElement
beforeEach(() => {
  vi.clearAllMocks()
  root = document.createElement('div')
  document.body.replaceChildren(root)
  mountWorkforce(root)
})

function change(selector: string, value: string, event = 'change') {
  const input = root.querySelector<HTMLInputElement>(selector)!
  input.value = value
  input.dispatchEvent(new Event(event, { bubbles: true }))
}

describe('workforce analysis', () => {
  it('starts with an extrapolated national comparison and occupation examples', () => {
    expect(root.querySelector<HTMLSelectElement>('#target-adoption')!.value).toBe('50')
    expect(root.querySelector<HTMLSelectElement>('#adoption-years')!.value).toBe('1')
    expect(root.querySelector('.settings-section')?.textContent).toContain('Developer Reference')
    expect(root.querySelectorAll('#occupation-rows tr')).toHaveLength(22)
    expect(root.querySelector<HTMLSelectElement>('#factor-fallback')!.value).toBe('fte-weighted-mean')
    expect(root.textContent).toContain('Estimert AI-effektbehov · ekstrapolert scenario')
    expect(root.textContent).toContain('67 MW')
    expect(root.textContent).toContain('årsverksvektet snitt (0,245)')
    expect(root.querySelectorAll('.scenario-examples tbody tr')).toHaveLength(4)
    expect(root.querySelector('.scenario-examples')!.textContent).toContain('Programvareutviklere')
    expect(root.querySelector('.scenario-examples')!.textContent).toContain('Jurister og advokater')
    expect(root.querySelector('.scenario-examples')!.textContent).toContain('Tømrere og snekkere')
    expect(root.querySelector('.scenario-examples')!.textContent).toContain('385 ekstrapolerte yrker')
    expect(root.querySelector('.scenario-examples tfoot')!.textContent).toContain('Totalt')
    expect(root.querySelector('.scenario-examples')!.textContent).toContain('GWh/år')
    expect(root.textContent).toContain('393 av 407 yrkeskoder')
    expect(root.textContent).toContain('Annonsert / planlagt, ikke garantert')
    expect(root.querySelectorAll('.chart-ai-point')).toHaveLength(6)
    expect(root.textContent).toContain('380 kWh')
    expect(root.textContent).toContain('Foreløpig kapasitetsbane')
  })
  it('updates controls without losing focus and resets all assumptions', () => {
    const target = root.querySelector<HTMLSelectElement>('#target-adoption')!
    target.focus()
    change('#target-adoption', '80')
    expect(document.activeElement).toBe(target)
    expect(root.querySelector<HTMLSelectElement>('#target-adoption')!.value).toBe('80')
    expect(root.querySelector<HTMLSelectElement>('#factor-level')!.value).toBe('base')
    change('#reference-profile', 'heavy')
    change('#annual-hours', '1000', 'input')
    expect(root.querySelector('#calibration-output')?.textContent).toContain('270 kWh')
    root.querySelector<HTMLButtonElement>('#reset-workforce')!.click()
    expect(root.querySelector<HTMLInputElement>('#annual-hours')!.value).toBe('1725')
    expect(root.querySelector<HTMLSelectElement>('#target-adoption')!.value).toBe('50')
    expect(root.querySelector<HTMLSelectElement>('#adoption-years')!.value).toBe('1')
    expect(root.querySelector<HTMLSelectElement>('#reference-profile')!.value).toBe('baseline')
    expect(root.querySelector<HTMLSelectElement>('#factor-fallback')!.value).toBe('fte-weighted-mean')
  })
  it('updates the extrapolation method and keeps extrapolated occupations explicit', () => {
    change('#factor-fallback', 'unweighted-mean')
    change('#factor-fallback', 'fte-weighted-mean')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe('67 MW')
    expect(root.querySelector('.scenario-examples tfoot')!.textContent).toContain('115 GWh/år')
    expect(root.textContent).toContain('årsverksvektet snitt (0,245)')
    expect(root.textContent).toContain('385 ekstrapolerte yrker')
    change('#coverage-filter', 'missing')
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ekstrapolert')
  })
  it('preserves unknowns and supports search and filtering', () => {
    change('#factor-fallback', 'none')
    change('#coverage-filter', 'all')
    expect(root.querySelectorAll('#occupation-rows tr')).toHaveLength(407)
    change('#occupation-search', '0000', 'input')
    expect(root.querySelectorAll('#occupation-rows tr')).toHaveLength(1)
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ukjent')
    change('#target-adoption', '20')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).not.toBe('0 MW')
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ukjent')
    change('#occupation-search', 'ingen treff xyz', 'input')
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ingen yrker')
  })
  it('does not compute invalid or empty inputs and exports all rows with assumptions', () => {
    change('#factor-fallback', 'none')
    const before = root.querySelector('[data-metric="mw"]')!.textContent
    change('#target-adoption', '100')
    const afterTarget = root.querySelector('[data-metric="mw"]')!.textContent
    expect(afterTarget).not.toBe(before)
    change('#annual-hours', '', 'input')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe(afterTarget)
    root.querySelector<HTMLButtonElement>('#export-workforce')!.click()
    const download = vi.mocked(triggerTextDownload).mock.calls[0][0]
    const rows = csvParse(download.content)
    expect(rows).toHaveLength(407)
    expect(rows[0].styrk08_code).toBe('0000')
    expect(rows[0].annual_it_gwh).toBe('')
    expect(rows[0].active_it_mw).toBe('')
    expect(rows[0].factor_is_extrapolated).toBe('false')
    expect(rows[0].factor_fallback).toBe('none')
    expect(rows[0].annual_active_hours_assumption).toBe('1725')
    expect(rows[0].current_adoption_percent).toBe('20')
    expect(rows[0].target_adoption_percent).toBe('100')
    expect(rows[0].trace_id).toBe('scenario-baseline')
  })
})