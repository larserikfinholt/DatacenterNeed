import { expect, test } from '@playwright/test'

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'desktop', width: 1440, height: 1000 },
] as const

for (const viewport of viewports) {
  test(`${viewport.name} Norway baseline preserves missing evidence`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.goto('/')

    await expect(page.locator('#dataset')).toHaveValue('norway-2025')
    await expect(page.getByRole('heading', { name: 'Capacity unavailable' })).toBeVisible()
    await expect(page.getByText('Absence is not rendered as zero.')).toBeVisible()
    await expect(page.locator('#electricity-chart svg')).toBeVisible()
    await expect(page.locator('#electricity-chart svg')).toHaveAttribute('width', /\d+/)
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(await page.evaluate(() => document.documentElement.clientWidth))

    await page.getByRole('button', { name: /Demand & scenarios/ }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: 'No national AI-energy estimate' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'No scenario configuration' })).toBeVisible()
  })
}

test('synthetic scenario is keyboard operable and renders nonblank chart marks', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await page.goto('/')
  await page.locator('#dataset').selectOption('synthetic')
  await page.getByRole('button', { name: /Demand & scenarios/ }).focus()
  await page.keyboard.press('Enter')

  await expect(page.getByRole('heading', { name: 'Scenario controls' })).toBeVisible()
  await expect(page.getByText('not probabilities or confidence intervals')).toBeVisible()
  await expect(page.locator('#scenario-chart svg')).toBeVisible()
  expect(await page.locator('#scenario-chart svg path, #scenario-chart svg rect').count()).toBeGreaterThan(5)
  await expect(page.getByText('681.99 MWh').first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    await page.evaluate(() => document.documentElement.clientWidth),
  )
})

test('computed synthetic resource outputs are visible', async ({ page }) => {
  await page.goto('/?v=1.0&dataset=synthetic&view=projects')

  await expect(page.getByText('1,825,000 AI requests / synthetic_workers')).toBeVisible()
  await expect(page.getByText('10 permanent_jobs/facility_MW')).toBeVisible()
})