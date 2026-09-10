import {
  createIcons,
  Download,
  ExternalLink,
  FileDown,
  RotateCcw,
  Share2,
  Upload,
} from 'lucide'

import type { ArtifactIndex, CalculationResult, DatasetIndexEntry } from './artifacts'
import {
  buildDashboardUrl,
  DASHBOARD_VIEWS,
  DEFAULT_SYNTHETIC_SELECTION,
  parseDashboardUrl,
  scenarioCsvDownload,
  scenarioSelectionDownload,
  triggerTextDownload,
  type DashboardView,
} from './dashboard'
import {
  evaluateDashboardScenario,
  parseDashboardScenario,
  type DashboardScenarioV1,
  type ScenarioCombinationResult,
} from './scenario'

type DataRecord = Record<string, unknown>

const dashboardIcons = { Download, ExternalLink, FileDown, RotateCcw, Share2, Upload }

export interface DashboardOptions {
  index: ArtifactIndex
  results: ReadonlyMap<string, CalculationResult>
  initialUrl?: string
  embedCharts?: boolean
  clipboard?: Pick<Clipboard, 'writeText'>
}

const VIEW_LABELS: Record<DashboardView, string> = {
  electricity: 'Electricity & capacity',
  demand: 'Demand & scenarios',
  projects: 'Projects & resources',
  sources: 'Sources, assumptions & evidence',
}

const CATEGORY_LABELS: Record<string, string> = {
  occupation_human_inference: 'Occupation-linked human inference',
  autonomous_background_inference: 'Autonomous background inference',
  consumer_ai: 'Consumer AI',
  foundation_training: 'Foundation training',
  fine_tuning: 'Fine-tuning',
  retrieval_embeddings: 'Retrieval & embeddings',
  non_ai: 'Non-AI workloads',
}

function records(value: unknown): DataRecord[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is DataRecord =>
          typeof item === 'object' && item !== null && !Array.isArray(item),
      )
    : []
}

function record(value: unknown): DataRecord | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as DataRecord)
    : null
}

function text(value: unknown, fallback = 'Not reported'): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function formatNumber(value: unknown, maximumFractionDigits = 2): string {
  const numeric = number(value)
  return numeric === null
    ? 'Unavailable'
    : new Intl.NumberFormat('en-GB', { maximumFractionDigits }).format(numeric)
}

function statusBadge(status: unknown): string {
  const normalized = text(status, 'unknown').toLowerCase()
  return `<span class="badge badge--${escapeHtml(normalized)}">${escapeHtml(normalized)}</span>`
}

function sourceButton(sourceId: unknown): string {
  return `<button class="source-link" type="button" data-source="${escapeHtml(sourceId)}">${escapeHtml(sourceId)}</button>`
}

function emptyState(title: string, body: string): string {
  return `<section class="empty-state" role="status"><span class="empty-state__mark" aria-hidden="true">—</span><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(body)}</p></div></section>`
}

function metricTable(rows: DataRecord[]): string {
  return `<div class="table-wrap"><table id="electricity-data"><caption>National electricity data behind the chart</caption><thead><tr><th>Measure</th><th>Value</th><th>Unit</th><th>Year</th><th>Boundary</th><th>Uncertainty</th><th>Status</th><th>Source</th></tr></thead><tbody>${rows
    .map(
      (row) => {
        const low = number(row.uncertainty_low)
        const high = number(row.uncertainty_high)
        const uncertainty =
          low === null || high === null
            ? 'Not reported'
            : `${formatNumber(low)}–${formatNumber(high)} ${escapeHtml(text(row.unit))}`
        return `<tr><th>${escapeHtml(text(row.definition))}</th><td>${formatNumber(row.value)}</td><td>${escapeHtml(text(row.unit))}</td><td>${escapeHtml(row.year)}</td><td>${escapeHtml(text(row.boundary))}</td><td>${uncertainty}</td><td>${statusBadge(row.evidence_status)}</td><td>${sourceButton(row.source_id)}</td></tr>`
      },
    )
    .join('')}</tbody></table></div>`
}

function electricityView(result: CalculationResult): string {
  const electricity = records(result.national_electricity)
  const comparators = records(result.facility_comparators)
  const projectTotals = records(result.project_totals)
  const comparatorContent =
    comparators.length > 0
      ? comparators
          .map(
            (item) => `<div class="synthetic-panel">
              <div>${statusBadge(item.evidence_status)} <strong>${formatNumber(item.capacity_mw)} MW</strong></div>
              <p>${escapeHtml(text(item.interpretation))}</p>
              <dl><div><dt>Annual energy</dt><dd>${formatNumber(item.annual_energy_mwh)} MWh</dd></div><div><dt>Load factor</dt><dd>${formatNumber(item.load_factor, 3)}</dd></div><div><dt>Boundary</dt><dd>Cloud facility</dd></div></dl>
            </div>`,
          )
          .join('')
      : '<p class="muted">No facility comparator is present in this dataset.</p>'
  const capacityContent =
    projectTotals.length > 0
      ? `<div class="table-wrap"><table><caption>Capacity totals supplied by the artifact</caption><tbody>${projectTotals
          .map(
            (item) =>
              `<tr><th>${escapeHtml(text(item.status))}</th><td>${formatNumber(item.capacity_mw)} MW</td></tr>`,
          )
          .join('')}</tbody></table></div>`
      : emptyState(
          'Capacity unavailable',
          'No boundary-clear national or project MW total is present. Absence is not rendered as zero.',
        )
  return `<section class="view-section" aria-labelledby="electricity-title">
    <div class="section-heading"><div><p class="eyebrow">Observed system context</p><h2 id="electricity-title">Electricity & capacity</h2></div><p>National flows and explicitly bounded facility comparators. Units are never converted without an artifact field.</p></div>
    ${
      electricity.length > 0
        ? `<figure aria-describedby="electricity-data"><figcaption>Observed national electricity flows · GWh · annual boundary</figcaption><div id="electricity-chart" class="chart" aria-label="Bar chart of observed national electricity production and consumption"></div>${metricTable(electricity)}</figure>`
        : emptyState(
            'No national electricity observations',
            'This artifact supplies no observed national electricity series.',
          )
    }
    <div class="split-band"><section><p class="eyebrow">Facility comparator</p><h3>${comparators.length > 0 ? 'Synthetic thought experiment' : 'No comparator available'}</h3>${comparatorContent}</section><section><p class="eyebrow">Capacity inventory</p><h3>Reported project totals</h3>${capacityContent}</section></div>
  </section>`
}

function occupationTable(result: CalculationResult): string {
  return `<div class="table-wrap"><table><caption>Occupation coverage and calculated demand</caption><thead><tr><th>Occupation</th><th>Requests / year</th><th>Cloud facility</th><th>Local device</th><th>Total</th><th>Status and missing reason</th></tr></thead><tbody>${records(
    result.occupations,
  )
    .map(
      (row) => `<tr><th>${escapeHtml(text(row.title))}</th><td>${formatNumber(row.annual_requests, 0)}</td><td>${number(row.cloud_facility_mwh) === null ? 'Unavailable' : `${formatNumber(row.cloud_facility_mwh)} MWh`}</td><td>${number(row.local_device_mwh) === null ? 'Unavailable' : `${formatNumber(row.local_device_mwh)} MWh`}</td><td>${number(row.known_total_mwh) === null ? 'Unavailable' : `${formatNumber(row.known_total_mwh)} MWh`}</td><td>${statusBadge(row.status)}<span class="cell-note">${escapeHtml(text(row.missing_reason, 'No missing reason'))}</span></td></tr>`,
    )
    .join('')}</tbody></table></div>`
}

function scenarioTable(result: ScenarioCombinationResult, id: string, caption: string): string {
  return `<div class="table-wrap"><table id="${id}"><caption>${escapeHtml(caption)}</caption><thead><tr><th>Category</th><th>Cloud facility</th><th>Local device</th><th>Known total</th><th>Status</th><th>Provenance</th></tr></thead><tbody>${result.categories
    .map((row) => {
      const provenance = [
        ...row.provenance.observed_source_ids,
        ...row.provenance.reported_source_ids,
        ...row.provenance.assumption_source_ids,
        ...row.provenance.synthetic_source_ids,
      ]
      return `<tr><th>${escapeHtml(CATEGORY_LABELS[row.category] ?? row.category)}</th><td>${number(row.cloud_facility_mwh) === null ? 'Unavailable' : `${formatNumber(row.cloud_facility_mwh)} MWh`}</td><td>${number(row.local_device_mwh) === null ? 'Unavailable' : `${formatNumber(row.local_device_mwh)} MWh`}</td><td>${number(row.known_total_mwh) === null ? 'Unavailable' : `${formatNumber(row.known_total_mwh)} MWh`}</td><td>${statusBadge(row.status)}${row.missing_reason ? `<span class="cell-note">${escapeHtml(row.missing_reason)}</span>` : ''}</td><td>${provenance.map(sourceButton).join(' ')}</td></tr>`
    })
    .join('')}</tbody></table></div>`
}

function scenarioEditor(selection: DashboardScenarioV1, compare: boolean): string {
  const controls = [
    ['demandMultiplier', 'Demand multiplier', 0, 5, 0.1],
    ['cloudShare', 'Cloud share', 0, 1, 0.01],
    ['domesticHostingShare', 'Domestic hosting share', 0, 1, 0.01],
    ['cloudPue', 'Cloud PUE', 1, 2, 0.01],
  ] as const
  return `<section class="scenario-editor" aria-labelledby="scenario-editor-title"><div class="editor-heading"><div><p class="eyebrow">Synthetic conditional model</p><h3 id="scenario-editor-title">Scenario controls</h3></div><span class="badge badge--synthetic">synthetic</span></div>
    <fieldset><legend>Adoption preset</legend><div class="segments">${(
      ['conservative', 'moderate', 'high'] as const
    )
      .map(
        (value) =>
          `<button type="button" data-adoption="${value}" aria-pressed="${selection.adoption === value}">${value}</button>`,
      )
      .join('')}</div></fieldset>
    <fieldset><legend>Placement preset</legend><div class="segments">${(
      ['cloud-heavy', 'hybrid', 'local-heavy'] as const
    )
      .map(
        (value) =>
          `<button type="button" data-placement="${value}" aria-pressed="${selection.placement === value}">${value}</button>`,
      )
      .join('')}</div></fieldset>
    <div class="control-grid">${controls
      .map(
        ([key, label, min, max, step]) =>
          `<div class="numeric-control"><div><label for="${key}-range">${label}</label><input id="${key}-number" data-override="${key}" type="number" min="${min}" max="${max}" step="${step}" value="${selection.overrides[key]}"></div><input id="${key}-range" data-override="${key}" type="range" min="${min}" max="${max}" step="${step}" value="${selection.overrides[key]}"></div>`,
      )
      .join('')}</div>
    <div class="editor-actions"><label class="check-control"><input id="compare-baseline" type="checkbox" ${compare ? 'checked' : ''}> Compare selected preset baseline</label><div class="button-row"><button class="button button--icon" type="button" id="reset-scenario" aria-label="Reset scenario" title="Reset scenario"><i data-lucide="rotate-ccw"></i></button><button class="button" type="button" id="export-selection"><i data-lucide="download"></i> Export selection</button><label class="button" for="import-selection"><i data-lucide="upload"></i> Import selection</label><input class="visually-hidden" id="import-selection" type="file" accept="application/json,.json"><button class="button button--icon" type="button" id="share-scenario" aria-label="Copy versioned scenario URL" title="Copy versioned scenario URL"><i data-lucide="share-2"></i></button></div></div>
    <p id="scenario-message" class="control-message" aria-live="polite"></p>
  </section>`
}

function baselineSelection(
  selection: DashboardScenarioV1,
  result: CalculationResult,
): DashboardScenarioV1 {
  const scenario = record(result.input_trace.scenario)
  const placement = records(scenario?.placement_presets).find(
    (item) => item.name === selection.placement,
  )
  return {
    ...selection,
    overrides: {
      demandMultiplier: 1,
      cloudShare:
        number(placement?.cloud_share) ?? DEFAULT_SYNTHETIC_SELECTION.overrides.cloudShare,
      domesticHostingShare:
        number(placement?.domestic_hosting_share) ??
        DEFAULT_SYNTHETIC_SELECTION.overrides.domesticHostingShare,
      cloudPue:
        number(record(result.input_trace.cloud_pue)?.value) ??
        DEFAULT_SYNTHETIC_SELECTION.overrides.cloudPue,
    },
  }
}

function demandView(
  result: CalculationResult,
  selection: DashboardScenarioV1 | null,
  compare: boolean,
): string {
  const country = result.countries[0]
  const coverage = record(country.occupation_coverage)
  if (result.scenario === null || selection === null) {
    return `<section class="view-section" aria-labelledby="demand-title"><div class="section-heading"><div><p class="eyebrow">Coverage before calculation</p><h2 id="demand-title">Demand & scenarios</h2></div><p>Occupation inputs remain visible even where the model cannot calculate energy.</p></div>
      <section class="finding finding--missing"><span class="finding__index">01</span><div><h3>No national AI-energy estimate</h3><p>The observed Norway baseline has no compatible broad-group annual-hours or task-profile assumptions. The national total remains unavailable, not zero.</p></div></section>
      <section class="finding finding--missing"><span class="finding__index">02</span><div><h3>No scenario configuration</h3><p>This dataset does not support adoption, placement, or override controls. Use the explicitly synthetic dataset to explore conditional outputs.</p></div></section>
      <div class="coverage-strip"><div><span>Coverage status</span><strong>${escapeHtml(text(coverage?.scope_status, text(country.scope_status)))}</strong></div><div><span>Declared cells</span><strong>${formatNumber(coverage?.declared_cell_count, 0)}</strong></div><div><span>Uncovered cells</span><strong>${formatNumber(coverage?.uncovered_cell_count, 0)}</strong></div><div><span>National total</span><strong>Unavailable</strong></div></div>${occupationTable(result)}</section>`
  }
  const source = {
    datasetId: selection.datasetId,
    inputTrace: result.input_trace,
    occupations: result.occupations,
  }
  const scenarioResult = evaluateDashboardScenario(source, selection)
  const baseline = evaluateDashboardScenario(source, baselineSelection(selection, result))
  return `<section class="view-section" aria-labelledby="demand-title"><div class="section-heading"><div><p class="eyebrow">Conditional model workspace</p><h2 id="demand-title">Demand & scenarios</h2></div><p>Outputs are synthetic conditional calculations. Presets are named assumptions, not probabilities or confidence intervals.</p></div>${scenarioEditor(selection, compare)}
    <div class="result-summary"><div><span>Known national subtotal</span><strong>${formatNumber(scenarioResult.known_national_subtotal_mwh)} MWh</strong></div><div><span>National total</span><strong>${number(scenarioResult.national_total_mwh) === null ? 'Unavailable' : `${formatNumber(scenarioResult.national_total_mwh)} MWh`}</strong></div><div><span>Scope</span><strong>${scenarioResult.scope_status}</strong></div><button class="button" type="button" id="download-scenario-csv"><i data-lucide="file-down"></i> Scenario CSV</button></div>
    <figure aria-describedby="scenario-data"><figcaption>Conditional category energy by execution location · MWh</figcaption><div id="scenario-chart" class="chart" aria-label="Stacked bar chart of synthetic scenario energy by category"></div>${scenarioTable(scenarioResult, 'scenario-data', 'Current conditional scenario results')}</figure>
    ${compare ? `<section class="comparison"><p class="eyebrow">Selected preset baseline</p><h3>${escapeHtml(selection.adoption)} · ${escapeHtml(selection.placement)} · default overrides</h3>${scenarioTable(baseline, 'baseline-data', 'Selected preset baseline results')}</section>` : ''}</section>`
}

function projectsView(result: CalculationResult): string {
  const projects = records(result.projects)
  const scenario = record(result.scenario)
  const allocations = records(scenario?.inverse_allocations)
  const ratios = records(scenario?.value_resource_ratios)
  const projectContent =
    projects.length === 0
      ? emptyState('No projects in this dataset', 'The synthetic fixture includes no project inventory.')
      : `<div class="project-list">${projects
          .map((project, index) => {
            const aliases = Array.isArray(project.aliases)
              ? project.aliases.filter((item): item is string => typeof item === 'string')
              : []
            return `<article class="project-row"><div class="project-number">${String(index + 1).padStart(2, '0')}</div><div><div class="project-title"><h3>${escapeHtml(text(project.title))}</h3><span>${escapeHtml(aliases.join(' · '))}</span></div>${records(
              project.phases,
            )
              .map((phase) => {
                const construction = records(phase.construction_status)[0]
                const grid = records(phase.grid_status)[0]
                return `<div class="phase"><strong>${escapeHtml(text(phase.title))}</strong><span>${statusBadge(construction?.status)} construction · as of ${escapeHtml(text(construction?.as_of_date))}</span><p>${escapeHtml(text(construction?.locator))} ${sourceButton(construction?.source_id)}</p><span>${statusBadge(grid?.status)} grid · as of ${escapeHtml(text(grid?.as_of_date))}</span><p>${escapeHtml(text(grid?.locator))}</p></div>`
              })
              .join('')}<p class="limitation"><strong>Completeness limit:</strong> ${escapeHtml(text(project.completeness_limitations))}</p></div></article>`
          })
          .join('')}</div>`
  const allocationContent =
    allocations.length > 0
      ? `<section class="synthetic-section"><p class="eyebrow">Synthetic inverse allocation</p><h3>Resource-to-activity calculation supplied by artifact</h3><div class="table-wrap"><table><thead><tr><th>Allocation</th><th>Activity per denominator</th><th>Facility capacity</th><th>Allocation share</th><th>Energy boundary</th><th>Denominator</th></tr></thead><tbody>${allocations
          .map(
            (item) =>
              `<tr><th>${escapeHtml(text(item.id))}</th><td>${formatNumber(item.activity_units_per_denominator)} ${escapeHtml(text(item.activity_unit))} / ${escapeHtml(text(item.denominator_unit))}</td><td>${formatNumber(item.facility_capacity_mw)} MW</td><td>${formatNumber(item.allocation_share, 3)}</td><td>${escapeHtml(text(item.energy_boundary))}</td><td>${formatNumber(item.denominator_value)} ${escapeHtml(text(item.denominator_unit))}</td></tr>`,
          )
          .join('')}</tbody></table></div></section>`
      : ''
  const ratioContent =
    ratios.length > 0
      ? `<section class="synthetic-section"><p class="eyebrow">Synthetic value-resource ratio</p><h3>Matched-boundary values supplied by artifact</h3>${ratios
          .map(
            (item) =>
              `<div class="ratio"><strong>${formatNumber(item.ratio)} ${escapeHtml(text(item.ratio_unit))}</strong><span>${escapeHtml(text(item.country_code))} · ${escapeHtml(item.year)}</span><p>${escapeHtml(text(item.value_definition))} per ${escapeHtml(text(item.resource_definition))} · boundary ${escapeHtml(text(item.boundary))}</p></div>`,
          )
          .join('')}</section>`
      : ''
  return `<section class="view-section" aria-labelledby="projects-title"><div class="section-heading"><div><p class="eyebrow">Inventory, not impact claim</p><h2 id="projects-title">Projects & resources</h2></div><p>No benefits quantities are present. Capacity is shown only where the artifact supplies a boundary-clear quantity.</p></div>${projectContent}${allocationContent}${ratioContent}</section>`
}

function sourceCard(source: DataRecord): string {
  const url = typeof source.url === 'string' ? source.url : null
  const queryUrl = typeof source.query_url === 'string' ? source.query_url : null
  return `<article class="source-record" id="source-${escapeHtml(source.id)}" tabindex="-1"><div class="source-record__head">${statusBadge(source.source_kind)}<span>${escapeHtml(text(source.publication_date, 'No publication date'))}</span></div><h3>${escapeHtml(text(source.title))}</h3><p>${escapeHtml(text(source.publisher))}</p><dl><div><dt>Retrieved</dt><dd>${escapeHtml(text(source.retrieved_date))}</dd></div><div><dt>License</dt><dd>${escapeHtml(text(source.license))}</dd></div><div><dt>Locator / limitation</dt><dd>${escapeHtml(text(source.locator))}</dd></div></dl><div class="source-actions">${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Source <i data-lucide="external-link"></i></a>` : ''}${queryUrl ? `<a href="${escapeHtml(queryUrl)}" target="_blank" rel="noreferrer">Query <i data-lucide="external-link"></i></a>` : ''}</div></article>`
}

function sourcesView(result: CalculationResult): string {
  const sources = records(result.input_trace.sources)
  const evidence = records(result.evidence)
  const benchmarks = records(result.input_trace.energy_benchmarks)
  const assumptions = sources.filter(
    (source) => source.source_kind === 'assumption' || source.source_kind === 'synthetic',
  )
  const observations = sources.filter(
    (source) => source.source_kind === 'observed' || source.source_kind === 'reported',
  )
  const evidenceContent =
    evidence.length > 0
      ? `<section class="evidence-band"><p class="eyebrow">Evidence stance</p>${evidence
          .map(
            (item) =>
              `<article class="evidence evidence--${escapeHtml(item.stance)}"><div>${statusBadge(item.stance)}</div><h3>${escapeHtml(text(item.finding))}</h3><p>${escapeHtml(text(item.applicability))}</p><p class="muted">${escapeHtml(text(item.limitations))}</p></article>`,
          )
          .join('')}</section>`
      : emptyState(
          'No evidence records',
          'This artifact contains no supporting, challenging, or mixed evidence record.',
        )
  return `<section class="view-section" aria-labelledby="sources-title"><div class="section-heading"><div><p class="eyebrow">Audit trail</p><h2 id="sources-title">Sources, assumptions & evidence</h2></div><p>Observed and reported records are separated from model assumptions and synthetic fixtures.</p></div>${evidenceContent}
    <div class="source-columns"><section><p class="eyebrow">Observed & reported</p><h3>External records</h3>${observations.map(sourceCard).join('') || '<p class="muted">None supplied.</p>'}</section><section><p class="eyebrow">Assumed & synthetic</p><h3>Model records</h3>${assumptions.map(sourceCard).join('') || '<p class="muted">None supplied.</p>'}</section></div>
    <section class="benchmark-section"><p class="eyebrow">Benchmarks</p><h3>Energy benchmark contracts</h3>${benchmarks
      .map(
        (item) =>
          `<article class="benchmark"><h4>${escapeHtml(text(item.title))}</h4><div class="benchmark-value">${formatNumber(item.kwh_per_request, 6)} <span>kWh / request</span></div><p>${escapeHtml(text(item.definition))}</p><dl><div><dt>Boundary</dt><dd>${escapeHtml(text(item.boundary))}</dd></div><div><dt>Measured period</dt><dd>${escapeHtml(text(item.measured_period))}</dd></div><div><dt>Limitations</dt><dd>${escapeHtml(text(item.limitations))}</dd></div><div><dt>Source</dt><dd>${sourceButton(item.source_id)}</dd></div></dl></article>`,
      )
      .join('') || '<p class="muted">No benchmark supplied.</p>'}</section>
    <details><summary>Calculation record</summary><dl class="calculation-record"><div><dt>Schema version</dt><dd>${escapeHtml(result.schema_version)}</dd></div><div><dt>Model version</dt><dd>${escapeHtml(result.model_version)}</dd></div><div><dt>Scope status</dt><dd>${escapeHtml(text(record(result.scope)?.scope_status))}</dd></div></dl></details></section>`
}

export function mountDashboard(root: HTMLElement, options: DashboardOptions): void {
  const initialSearch = options.initialUrl
    ? new URL(options.initialUrl).search
    : window.location.search
  const parsed = parseDashboardUrl(
    initialSearch,
    options.index.datasets.map(({ id }) => id),
  )
  let datasetId = parsed.datasetId
  let view = parsed.view
  let selection = parsed.selection
  let compare = false
  let notice = parsed.warning

  const currentDataset = (): DatasetIndexEntry =>
    options.index.datasets.find((item) => item.id === datasetId) ?? options.index.datasets[0]
  const currentResult = (): CalculationResult => {
    const result = options.results.get(datasetId)
    if (!result) throw new Error(`Result for ${datasetId} is unavailable.`)
    return result
  }
  const updateUrl = (): void => {
    const url = buildDashboardUrl(
      options.initialUrl ?? window.location.href,
      datasetId,
      view,
      selection,
    )
    if (!options.initialUrl) history.replaceState(null, '', url)
  }

  const renderCharts = (): void => {
    if (options.embedCharts === false) return
    void import('vega-embed').then(({ default: embed }) => {
      const result = currentResult()
    const electricity = records(result.national_electricity).filter(
      (item) => number(item.value) !== null,
    )
    const electricityContainer = root.querySelector<HTMLElement>('#electricity-chart')
    if (electricityContainer && electricity.length > 0) {
      void embed(
        electricityContainer,
        {
          $schema: 'https://vega.github.io/schema/vega-lite/v6.json',
          width: 'container',
          height: 220,
          data: {
            values: electricity.map((item) => ({
              measure: text(item.metric),
              value: number(item.value),
              status: text(item.evidence_status),
            })),
          },
          mark: { type: 'bar', cornerRadiusEnd: 2 },
          encoding: {
            x: { field: 'measure', type: 'nominal', axis: { title: null, labelAngle: 0 } },
            y: { field: 'value', type: 'quantitative', axis: { title: 'GWh' } },
            color: {
              field: 'status',
              type: 'nominal',
              scale: { domain: ['observed'], range: ['#245b75'] },
              legend: null,
            },
            tooltip: [
              { field: 'measure', type: 'nominal' },
              { field: 'value', type: 'quantitative', title: 'GWh', format: ',.0f' },
            ],
          },
          config: { font: 'Verdana', view: { stroke: null } },
        },
        { actions: false, renderer: 'svg' },
      )
    }
      if (selection === null) return
    const scenarioResult = evaluateDashboardScenario(
      { datasetId, inputTrace: result.input_trace, occupations: result.occupations },
      selection,
    )
    const scenarioContainer = root.querySelector<HTMLElement>('#scenario-chart')
      if (!scenarioContainer) return
    const values = scenarioResult.categories
      .flatMap((item) => [
        {
          category: CATEGORY_LABELS[item.category] ?? item.category,
          location: 'Cloud facility',
          value: item.cloud_facility_mwh,
        },
        {
          category: CATEGORY_LABELS[item.category] ?? item.category,
          location: 'Local device',
          value: item.local_device_mwh,
        },
      ])
      .filter((item) => item.value !== null)
      void embed(
      scenarioContainer,
      {
        $schema: 'https://vega.github.io/schema/vega-lite/v6.json',
        width: 'container',
        height: 300,
        data: { values },
        mark: 'bar',
        encoding: {
          y: {
            field: 'category',
            type: 'nominal',
            sort: null,
            axis: { title: null, labelLimit: 220 },
          },
          x: { field: 'value', type: 'quantitative', stack: 'zero', axis: { title: 'MWh' } },
          color: {
            field: 'location',
            type: 'nominal',
            scale: {
              domain: ['Cloud facility', 'Local device'],
              range: ['#245b75', '#487a58'],
            },
            legend: { orient: 'top' },
          },
          tooltip: [
            { field: 'category', type: 'nominal' },
            { field: 'location', type: 'nominal' },
            { field: 'value', type: 'quantitative', title: 'MWh', format: ',.3f' },
          ],
        },
        config: { font: 'Verdana', view: { stroke: null } },
      },
      { actions: false, renderer: 'svg' },
      )
    })
  }

  const rerender = (): void => {
    const dataset = currentDataset()
    const result = currentResult()
    const content =
      view === 'electricity'
        ? electricityView(result)
        : view === 'demand'
          ? demandView(result, selection, compare)
          : view === 'projects'
            ? projectsView(result)
            : sourcesView(result)
    root.innerHTML = `<a class="skip-link" href="#workspace">Skip to research workspace</a><header class="masthead"><div class="brand"><span class="brand__index">DCN / 01</span><div><h1>Datacenter Need</h1><p>Evidence-led infrastructure research</p></div></div><div class="dataset-control"><label for="dataset">Dataset</label><select id="dataset">${options.index.datasets.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === datasetId ? 'selected' : ''}>${escapeHtml(item.title)}</option>`).join('')}</select></div><div class="header-meta"><span class="badge badge--${dataset.kind === 'synthetic' ? 'synthetic' : 'observed'}">${escapeHtml(dataset.kind)}</span><span>Schema ${escapeHtml(dataset.schemaVersion)}</span><span>Model ${escapeHtml(dataset.modelVersion)}</span><a class="button button--icon" href="${escapeHtml(dataset.paths.occupationBreakdown)}" download aria-label="Download original occupation CSV" title="Download original occupation CSV"><i data-lucide="file-down"></i></a></div></header><div class="research-frame"><nav class="view-tabs" aria-label="Research views">${DASHBOARD_VIEWS.map((item, index) => `<button type="button" data-view="${item}" aria-selected="${view === item}"><span>0${index + 1}</span>${VIEW_LABELS[item]}</button>`).join('')}</nav><main id="workspace" tabindex="-1">${notice ? `<p class="notice" role="alert">${escapeHtml(notice)}</p>` : ''}<div class="dataset-line"><span>${escapeHtml(dataset.country)} · ${dataset.year}</span><span>Reference year ${dataset.year}</span><span>Artifact boundary varies by record</span></div>${content}</main></div>`
    createIcons({ icons: dashboardIcons })

    root.querySelector<HTMLSelectElement>('#dataset')?.addEventListener('change', (event) => {
      datasetId = (event.currentTarget as HTMLSelectElement).value
      selection =
        datasetId === 'synthetic' ? structuredClone(DEFAULT_SYNTHETIC_SELECTION) : null
      view = 'electricity'
      notice = null
      updateUrl()
      rerender()
    })
    root.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((button) =>
      button.addEventListener('click', () => {
        view = button.dataset.view as DashboardView
        updateUrl()
        rerender()
      }),
    )
    root.querySelectorAll<HTMLButtonElement>('[data-source]').forEach((button) =>
      button.addEventListener('click', () => {
        const sourceId = button.dataset.source
        view = 'sources'
        updateUrl()
        rerender()
        document.getElementById(`source-${sourceId}`)?.focus()
      }),
    )
    root.querySelectorAll<HTMLButtonElement>('[data-adoption]').forEach((button) =>
      button.addEventListener('click', () => {
        if (selection === null) return
        selection.adoption = button.dataset.adoption as DashboardScenarioV1['adoption']
        updateUrl()
        rerender()
      }),
    )
    root.querySelectorAll<HTMLButtonElement>('[data-placement]').forEach((button) =>
      button.addEventListener('click', () => {
        if (selection === null) return
        selection.placement = button.dataset.placement as DashboardScenarioV1['placement']
        selection = baselineSelection(selection, result)
        updateUrl()
        rerender()
      }),
    )
    root.querySelectorAll<HTMLInputElement>('[data-override]').forEach((input) =>
      input.addEventListener('change', () => {
        if (selection === null) return
        const key = input.dataset.override as keyof DashboardScenarioV1['overrides']
        try {
          selection = parseDashboardScenario({
            ...selection,
            overrides: { ...selection.overrides, [key]: Number(input.value) },
          })
          notice = null
          updateUrl()
          rerender()
        } catch (error) {
          notice = error instanceof Error ? error.message : 'Invalid scenario value.'
          rerender()
        }
      }),
    )
    root
      .querySelector<HTMLInputElement>('#compare-baseline')
      ?.addEventListener('change', (event) => {
        compare = (event.currentTarget as HTMLInputElement).checked
        rerender()
      })
    root.querySelector<HTMLButtonElement>('#reset-scenario')?.addEventListener('click', () => {
      if (selection === null) return
      selection = baselineSelection(selection, result)
      updateUrl()
      rerender()
    })
    root.querySelector<HTMLButtonElement>('#export-selection')?.addEventListener('click', () => {
      if (selection !== null) triggerTextDownload(scenarioSelectionDownload(selection))
    })
    root
      .querySelector<HTMLButtonElement>('#download-scenario-csv')
      ?.addEventListener('click', () => {
        if (selection === null) return
        const scenarioResult = evaluateDashboardScenario(
          { datasetId, inputTrace: result.input_trace, occupations: result.occupations },
          selection,
        )
        triggerTextDownload(scenarioCsvDownload(scenarioResult))
      })
    root
      .querySelector<HTMLInputElement>('#import-selection')
      ?.addEventListener('change', async (event) => {
        const input = event.currentTarget as HTMLInputElement
        const message = root.querySelector<HTMLElement>('#scenario-message')
        try {
          const file = input.files?.[0]
          if (!file) return
          const imported = parseDashboardScenario(JSON.parse(await file.text()) as unknown)
          if (imported.datasetId !== datasetId) {
            throw new Error(`Selection is for ${imported.datasetId}, not ${datasetId}.`)
          }
          selection = imported
          notice = null
          updateUrl()
          rerender()
        } catch (error) {
          if (message) {
            message.setAttribute('role', 'alert')
            message.textContent =
              error instanceof Error ? `Import rejected: ${error.message}` : 'Import rejected.'
          }
        }
      })
    root.querySelector<HTMLButtonElement>('#share-scenario')?.addEventListener('click', async () => {
      const url = buildDashboardUrl(
        options.initialUrl ?? window.location.href,
        datasetId,
        view,
        selection,
      )
      if (!options.initialUrl) history.replaceState(null, '', url)
      const message = root.querySelector<HTMLElement>('#scenario-message')
      if (options.clipboard) {
        await options.clipboard.writeText(url)
        if (message) message.textContent = 'Versioned URL copied.'
      } else if (message) {
        message.textContent = 'Versioned URL updated in the address bar.'
      }
    })
    renderCharts()
  }

  updateUrl()
  rerender()
}