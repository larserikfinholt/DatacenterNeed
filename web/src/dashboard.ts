import {
  DASHBOARD_SCENARIO_VERSION,
  dashboardScenarioToSearchParams,
  parseDashboardScenario,
  type DashboardScenarioV1,
  type ScenarioCombinationResult,
} from './scenario'

export const DASHBOARD_URL_VERSION = '1.0' as const
export const DASHBOARD_VIEWS = ['electricity', 'demand', 'reference', 'projects', 'sources'] as const
export type DashboardView = (typeof DASHBOARD_VIEWS)[number]

export interface DashboardUrlState {
  datasetId: string
  view: DashboardView
  selection: DashboardScenarioV1 | null
  warning: string | null
}

export const DEFAULT_SYNTHETIC_SELECTION: DashboardScenarioV1 = {
  schemaVersion: DASHBOARD_SCENARIO_VERSION,
  datasetId: 'synthetic',
  adoption: 'moderate',
  placement: 'hybrid',
  overrides: {
    demandMultiplier: 1,
    cloudShare: 0.6,
    domesticHostingShare: 0.6,
    cloudPue: 1.2,
  },
}

function finiteParameter(params: URLSearchParams, name: string): number {
  const raw = params.get(name)
  return raw === null || raw.trim() === '' ? Number.NaN : Number(raw)
}

export function parseDashboardUrl(
  search: string,
  datasetIds: readonly string[],
): DashboardUrlState {
  const params = new URLSearchParams(search)
  const requestedDataset = params.get('dataset')
  const datasetId =
    requestedDataset !== null && datasetIds.includes(requestedDataset)
      ? requestedDataset
      : datasetIds.includes('norway-2025')
        ? 'norway-2025'
        : (datasetIds[0] ?? '')
  const requestedView = params.get('view')
  const view = DASHBOARD_VIEWS.includes(requestedView as DashboardView)
    ? (requestedView as DashboardView)
    : 'electricity'
  const hasScenarioParameters = [
    'adoption',
    'placement',
    'demand',
    'cloud',
    'domestic',
    'pue',
  ].some((key) => params.has(key))

  if (!hasScenarioParameters) {
    const invalidVersion = params.has('v') && params.get('v') !== DASHBOARD_URL_VERSION
    return {
      datasetId,
      view,
      selection:
        datasetId === 'synthetic' ? structuredClone(DEFAULT_SYNTHETIC_SELECTION) : null,
      warning: invalidVersion
        ? `URL state ignored: Unsupported dashboard URL version ${params.get('v')}.`
        : requestedDataset !== null && requestedDataset !== datasetId
          ? 'Unknown dataset in URL; showing the default dataset.'
          : null,
    }
  }

  try {
    if (params.get('v') !== DASHBOARD_URL_VERSION) {
      throw new Error(`Unsupported dashboard URL version ${params.get('v') ?? '(missing)'}.`)
    }
    const selection = parseDashboardScenario({
      schemaVersion: params.get('v'),
      datasetId,
      adoption: params.get('adoption'),
      placement: params.get('placement'),
      overrides: {
        demandMultiplier: finiteParameter(params, 'demand'),
        cloudShare: finiteParameter(params, 'cloud'),
        domesticHostingShare: finiteParameter(params, 'domestic'),
        cloudPue: finiteParameter(params, 'pue'),
      },
    })
    return { datasetId, view, selection, warning: null }
  } catch (error) {
    return {
      datasetId,
      view,
      selection:
        datasetId === 'synthetic' ? structuredClone(DEFAULT_SYNTHETIC_SELECTION) : null,
      warning:
        error instanceof Error ? `URL state ignored: ${error.message}` : 'URL state ignored.',
    }
  }
}

export function buildDashboardUrl(
  baseUrl: string,
  datasetId: string,
  view: DashboardView,
  selection: DashboardScenarioV1 | null,
): string {
  const url = new URL(baseUrl)
  const params =
    selection === null
      ? new URLSearchParams({ v: DASHBOARD_URL_VERSION, dataset: datasetId })
      : dashboardScenarioToSearchParams(selection)
  params.set('view', view)
  url.search = params.toString()
  return url.toString()
}

function csvCell(value: string | number | null): string {
  if (value === null) return ''
  const text = String(value)
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

export function scenarioResultToCsv(result: ScenarioCombinationResult): string {
  const rows: Array<Array<string | number | null>> = [
    [
      'category',
      'cloud_facility_mwh',
      'local_device_mwh',
      'known_total_mwh',
      'status',
      'missing_reason',
    ],
    ...result.categories.map((row) => [
      row.category,
      row.cloud_facility_mwh,
      row.local_device_mwh,
      row.known_total_mwh,
      row.status,
      row.missing_reason,
    ]),
  ]
  return `${rows.map((row) => row.map(csvCell).join(',')).join('\n')}\n`
}

export interface TextDownload {
  filename: string
  mediaType: string
  content: string
}

export function scenarioSelectionDownload(selection: unknown): TextDownload {
  const parsed = parseDashboardScenario(selection)
  return {
    filename: `${parsed.datasetId}-scenario-selection-v${parsed.schemaVersion}.json`,
    mediaType: 'application/json',
    content: `${JSON.stringify(parsed, null, 2)}\n`,
  }
}

export function scenarioCsvDownload(result: ScenarioCombinationResult): TextDownload {
  return {
    filename: `${result.id}-conditional-results.csv`,
    mediaType: 'text/csv;charset=utf-8',
    content: scenarioResultToCsv(result),
  }
}

export function triggerTextDownload(download: TextDownload): void {
  const url = URL.createObjectURL(new Blob([download.content], { type: download.mediaType }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = download.filename
  anchor.click()
  URL.revokeObjectURL(url)
}