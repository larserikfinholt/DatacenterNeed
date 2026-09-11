import { expect, test } from '@playwright/test'

for (const viewport of [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'desktop', width: 1440, height: 1000 },
]) {
  test(`${viewport.name} national comparison, controls and coverage`, async ({ page }, testInfo) => {
    const errors: string[] = []
    page.on('pageerror', (error) => errors.push(error.message))
    await page.setViewportSize(viewport)
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Hvor stort er behovet sammenlignet med det Norge bygger?' })).toBeVisible()
    await expect(page.locator('[data-metric="mw"]')).toBeInViewport()
    await expect(page.locator('#headline-output')).toContainText('2030 forpliktet')
    await expect(page.locator('#headline-output')).toContainText('1,69 %')
    await expect(page.locator('#headline-output')).toContainText('4 MW årsgjennomsnitt')
    await expect(page.locator('.comparison-chart')).toBeInViewport()
    await expect(page.locator('.chart-ai-point')).toHaveCount(6)
    await expect(page.locator('#coverage-output')).toContainText('22 / 407')
    await expect(page.locator('#occupation-rows tr')).toHaveCount(22)
    expect(await page.locator('.coverage-track > div').evaluate((element) => element.getBoundingClientRect().width)).toBeGreaterThan(20)
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}.png`), fullPage: true })
    await page.getByRole('button', { name: 'Høy 80 %' }).click()
    await expect(page.locator('#target-adoption')).toHaveValue('80')
    await expect(page.locator('#factor-level')).toHaveValue('base')
    await page.locator('#target-adoption').fill('0')
    await expect(page.locator('[data-metric="mw"]')).toHaveText('0 MW')
    await page.locator('#factor-fallback').selectOption('fte-weighted-mean')
    await page.locator('#target-adoption').fill('50')
    await expect(page.locator('[data-metric="mw"]')).toHaveText('66,56 MW')
    await expect(page.locator('#coverage-output')).toContainText('385 uvurderte koder')
    await page.locator('#coverage-filter').selectOption('all')
    await expect(page.locator('#occupation-rows tr')).toHaveCount(407)
    await page.locator('#occupation-search').fill('0000')
    await expect(page.locator('#occupation-rows')).toContainText('Ukjent')
    await page.getByRole('button', { name: 'Tilbakestill antakelser' }).click()
    await expect(page.locator('#current-adoption')).toHaveValue('20')
    await expect(page.locator('#target-adoption')).toHaveValue('50')
    await expect(page.locator('#factor-fallback')).toHaveValue('none')
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Eksporter CSV' }).click()
    expect((await downloadPromise).suggestedFilename()).toBe('ai-adopsjon-norge-2025.csv')
    for (const link of await page.locator('#sources a[download]').all()) {
      const response = await page.request.get((await link.getAttribute('href'))!)
      expect(response.ok()).toBe(true)
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width)
    expect(errors).toEqual([])
  })
}