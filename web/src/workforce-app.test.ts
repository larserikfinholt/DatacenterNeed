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
    expect(root.querySelector('#adoption-title')).toBeNull()
    expect(root.querySelector('#factor-title')?.textContent).toBe('Yrkesfaktorer')
    const referenceMethod = root.querySelector<HTMLSelectElement>('#reference-method')!
    expect(referenceMethod.disabled).toBe(false)
    expect(referenceMethod.options).toHaveLength(2)
    expect(referenceMethod.selectedOptions[0].textContent).toBe('Delt server · H100 + GLM-5.3')
    const methodDetails = root.querySelector('.reference-method-details')!
    expect(methodDetails.textContent).toContain('8 NVIDIA H100, 65 % GPU-utnyttelse og 20 samtidige utviklere')
    expect(methodDetails.textContent).toContain('8 × 425 W + 1 000 W = 4 400 W')
    expect(methodDetails.textContent).toContain('4 400 W ÷ 20 = 220 W')
    expect(methodDetails.textContent).toContain('ikke verifisert')
    const quickControls = root.querySelector('.settings-quick-row')!
    const adoptionNote = quickControls.querySelector('.assumption-note')!
    expect(quickControls.lastElementChild).toBe(adoptionNote)
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
    expect(root.querySelector('nav a[href="#assumptions"]')?.textContent).toBe('Forklaringer')
    expect(Array.from(root.querySelectorAll('nav a')).map((link) => link.textContent)).toEqual([
      'Sammenligning',
      'Forklaringer',
      'Innstillinger',
      'Yrker',
    ])
    expect(root.querySelector('#assumptions')?.textContent).toContain('Hva betyr dette?')
    expect(Array.from(root.querySelectorAll('#assumptions h2')).map((heading) => heading.textContent)).toEqual([
      'Hva sammenligningen viser',
      'Hva betyr dette?',
      'Hvordan har vi regnet ut dette?',
    ])
    expect(root.querySelector('#assumptions')?.textContent).not.toContain('Hva er utelatt?')
    expect(root.querySelector('.sources-grid > div:last-child')?.textContent).toContain('Hva er utelatt?')
    expect(root.querySelector('#assumptions')?.textContent).toContain('20 % av regnekapasiteten')
    expect(root.querySelector('.workforce-header')?.textContent).toContain('estimat generert september 2026')
    expect(root.querySelector('.workforce-footer')?.textContent).toContain('Estimat generert september 2026')
    expect(root.querySelector('.workforce-footer a')).toBeNull()
    expect(root.textContent).not.toContain('Referansens evidensgap')
  })
  it('offers a local M3 Ultra reference for one developer', () => {
    change('#reference-method', 'mac-m3-ultra')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe('82 MW')
    expect(root.querySelector('#calibration-output')!.textContent).toContain('466 kWh')
    const details = root.querySelector('#reference-method-details')!
    expect(details.textContent).toContain('Qwen3.5-27B · 4-bit MLX · 16,1 GB')
    expect(details.textContent).toContain('270 W × 1 maskin ÷ 1 utvikler = 270 W')
    expect(details.textContent).toContain('Lokal strøm er heller ikke datasenterlast')
    root.querySelector<HTMLButtonElement>('#reset-workforce')!.click()
    expect(root.querySelector<HTMLSelectElement>('#reference-method')!.value).toBe('h100-glm')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe('67 MW')
  })
  it('updates controls without losing focus and resets all assumptions', () => {
    const target = root.querySelector<HTMLSelectElement>('#target-adoption')!
    target.focus()
    change('#target-adoption', '80')
    expect(document.activeElement).toBe(target)
    expect(root.querySelector<HTMLSelectElement>('#target-adoption')!.value).toBe('80')
    expect(root.querySelector<HTMLSelectElement>('#factor-level')!.value).toBe('base')
    change('#annual-hours', '1000', 'input')
    expect(root.querySelector('#calibration-output')?.textContent).toContain('220 kWh')
    root.querySelector<HTMLButtonElement>('#reset-workforce')!.click()
    expect(root.querySelector<HTMLInputElement>('#annual-hours')!.value).toBe('1725')
    expect(root.querySelector<HTMLSelectElement>('#target-adoption')!.value).toBe('50')
    expect(root.querySelector<HTMLSelectElement>('#adoption-years')!.value).toBe('1')
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