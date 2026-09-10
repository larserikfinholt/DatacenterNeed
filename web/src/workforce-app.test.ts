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
  it('starts with estimates, base assumptions and explicit partial coverage', () => {
    expect(root.querySelector('[data-preset="50"]')?.getAttribute('aria-pressed')).toBe('true')
    expect(root.querySelectorAll('#occupation-rows tr')).toHaveLength(22)
    expect(root.textContent).toContain('22 / 407')
    expect(root.textContent).toContain('30,5 %')
    expect(root.textContent).toContain('Ikke et totalestimat for Norge')
    expect(root.textContent).toContain('379,5')
    expect(root.textContent).toContain('Kapasitet: uavklart')
  })
  it('updates controls without losing focus and resets all assumptions', () => {
    const range = root.querySelector<HTMLInputElement>('#adoption-range')!
    range.focus()
    change('#adoption-range', '80', 'input')
    expect(document.activeElement).toBe(range)
    expect(root.querySelector<HTMLInputElement>('#adoption-number')!.value).toBe('80')
    expect(root.querySelector<HTMLSelectElement>('#factor-level')!.value).toBe('base')
    change('#reference-profile', 'heavy')
    change('#annual-hours', '1000', 'input')
    expect(root.querySelector('#calibration-output')?.textContent).toContain('270 kWh')
    root.querySelector<HTMLButtonElement>('#reset-workforce')!.click()
    expect(root.querySelector<HTMLInputElement>('#annual-hours')!.value).toBe('1725')
    expect(root.querySelector<HTMLInputElement>('#adoption-number')!.value).toBe('50')
    expect(root.querySelector<HTMLSelectElement>('#reference-profile')!.value).toBe('baseline')
  })
  it('preserves unknowns and supports search, filtering and zero adoption', () => {
    change('#coverage-filter', 'all')
    expect(root.querySelectorAll('#occupation-rows tr')).toHaveLength(407)
    change('#occupation-search', '0000', 'input')
    expect(root.querySelectorAll('#occupation-rows tr')).toHaveLength(1)
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ukjent')
    change('#adoption-number', '0', 'input')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe('0 MW')
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ukjent')
    change('#occupation-search', 'ingen treff xyz', 'input')
    expect(root.querySelector('#occupation-rows')!.textContent).toContain('Ingen yrker')
  })
  it('does not compute invalid or empty inputs and exports all rows with assumptions', () => {
    const before = root.querySelector('[data-metric="mw"]')!.textContent
    change('#adoption-number', '101', 'input')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe(before)
    change('#annual-hours', '', 'input')
    expect(root.querySelector('[data-metric="mw"]')!.textContent).toBe(before)
    root.querySelector<HTMLButtonElement>('#export-workforce')!.click()
    const download = vi.mocked(triggerTextDownload).mock.calls[0][0]
    const rows = csvParse(download.content)
    expect(rows).toHaveLength(407)
    expect(rows[0].styrk08_code).toBe('0000')
    expect(rows[0].annual_it_gwh).toBe('')
    expect(rows[0].annual_active_hours_assumption).toBe('1725')
    expect(rows[0].adoption_percent).toBe('50')
    expect(rows[0].trace_id).toBe('scenario-baseline')
  })
})