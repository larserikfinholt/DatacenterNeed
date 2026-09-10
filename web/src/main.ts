import './style.css'
import './workforce.css'

const app = document.querySelector<HTMLDivElement>('#app')!
app.innerHTML =
  '<main class="loading"><h1>AI og strømbehov</h1><p role="status">Kontrollerer datagrunnlaget...</p></main>'

async function render(): Promise<void> {
  const params = new URL(window.location.href).searchParams
  if (!params.has('legacy') && !params.has('view') && !params.has('dataset')) {
    const { mountWorkforce } = await import('./workforce-app')
    mountWorkforce(app)
    return
  }
  const { loadArtifactIndex, loadCalculationResult, loadDeveloperReferenceResult } = await import('./artifacts')
  const { mountDashboard } = await import('./app')
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
  app.replaceChildren()
  const status = document.createElement('p')
  status.className = 'loading'
  status.setAttribute('role', 'alert')
  status.textContent = error instanceof Error ? error.message : 'Kunne ikke laste datagrunnlaget.'
  app.append(status)
})
