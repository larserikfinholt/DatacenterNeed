import './style.css'
import { loadArtifactIndex, loadCalculationResult, loadDeveloperReferenceResult } from './artifacts'
import { mountDashboard } from './app'

const app = document.querySelector<HTMLDivElement>('#app')!
app.innerHTML =
  '<main class="loading"><p class="eyebrow">Datacenter Need</p><h1>Loading research artifacts</h1><p role="status">Validating local datasets...</p></main>'

async function render(): Promise<void> {
  const index = await loadArtifactIndex()
  const loaded = await Promise.all(
    index.datasets.map(
      async (dataset) => [dataset.id, await loadCalculationResult(dataset)] as const,
    ),
  )
  const reference = await loadDeveloperReferenceResult()
  mountDashboard(app, {
    index,
    results: new Map(loaded),
    reference,
    clipboard: navigator.clipboard,
  })
}

render().catch((error: unknown) => {
  const status = document.querySelector<HTMLElement>('[role="status"]')!
  status.setAttribute('role', 'alert')
  status.textContent = error instanceof Error ? error.message : 'Unable to load datasets.'
})
