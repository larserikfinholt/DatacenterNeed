export const SUPPORTED_SCHEMA_VERSION = '1.0' as const
export const SUPPORTED_MODEL_VERSION = '1.0' as const

export type DatasetKind = 'synthetic' | 'observed-baseline'

export interface ArtifactPaths {
  result: string
  manifest: string
  occupationBreakdown: string
}

export interface DatasetIndexEntry {
  id: string
  title: string
  kind: DatasetKind
  country: string
  year: number
  schemaVersion: typeof SUPPORTED_SCHEMA_VERSION
  modelVersion: typeof SUPPORTED_MODEL_VERSION
  paths: ArtifactPaths
}

export interface ArtifactIndex {
  datasets: DatasetIndexEntry[]
}

export interface CountryResult extends Record<string, unknown> {
  country_code: string
  year: number
  national_total_mwh: number | null
}

export interface CalculationResult extends Record<string, unknown> {
  schema_version: typeof SUPPORTED_SCHEMA_VERSION
  model_version: typeof SUPPORTED_MODEL_VERSION
  countries: CountryResult[]
  scenario: Record<string, unknown> | null
  input_trace: Record<string, unknown> & {
    model_version: typeof SUPPORTED_MODEL_VERSION
  }
}

export class ArtifactValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ArtifactValidationError'
  }
}

function requireRecord(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ArtifactValidationError(`${path} must be an object`)
  }
  return value as Record<string, unknown>
}

function requireString(record: Record<string, unknown>, key: string, path: string): string {
  const value = record[key]
  if (typeof value !== 'string' || value.length === 0) {
    throw new ArtifactValidationError(`${path}.${key} must be a non-empty string`)
  }
  return value
}

function requireNumber(record: Record<string, unknown>, key: string, path: string): number {
  const value = record[key]
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new ArtifactValidationError(`${path}.${key} must be a finite number`)
  }
  return value
}

function requireSupportedVersion(
  record: Record<string, unknown>,
  key: string,
  supported: string,
  path: string,
): typeof SUPPORTED_SCHEMA_VERSION {
  const value = requireString(record, key, path)
  if (value !== supported) {
    throw new ArtifactValidationError(`${path}.${key} ${value} is not supported`)
  }
  return supported as typeof SUPPORTED_SCHEMA_VERSION
}

export function parseArtifactIndex(value: unknown): ArtifactIndex {
  const index = requireRecord(value, 'index')
  if (!Array.isArray(index.datasets)) {
    throw new ArtifactValidationError('index.datasets must be an array')
  }

  const datasets = index.datasets.map((item, position): DatasetIndexEntry => {
    const path = `index.datasets[${position}]`
    const dataset = requireRecord(item, path)
    const kind = requireString(dataset, 'kind', path)
    if (kind !== 'synthetic' && kind !== 'observed-baseline') {
      throw new ArtifactValidationError(`${path}.kind is invalid`)
    }
    const paths = requireRecord(dataset.paths, `${path}.paths`)

    return {
      id: requireString(dataset, 'id', path),
      title: requireString(dataset, 'title', path),
      kind,
      country: requireString(dataset, 'country', path),
      year: requireNumber(dataset, 'year', path),
      schemaVersion: requireSupportedVersion(
        dataset,
        'schemaVersion',
        SUPPORTED_SCHEMA_VERSION,
        path,
      ),
      modelVersion: requireSupportedVersion(
        dataset,
        'modelVersion',
        SUPPORTED_MODEL_VERSION,
        path,
      ),
      paths: {
        result: requireString(paths, 'result', `${path}.paths`),
        manifest: requireString(paths, 'manifest', `${path}.paths`),
        occupationBreakdown: requireString(paths, 'occupationBreakdown', `${path}.paths`),
      },
    }
  })

  return { datasets }
}

function requireNullableNumber(
  record: Record<string, unknown>,
  key: string,
  path: string,
): number | null {
  const value = record[key]
  if (value === null) {
    return null
  }
  return requireNumber(record, key, path)
}

export function parseCalculationResult(value: unknown): CalculationResult {
  const result = requireRecord(value, 'result')
  requireSupportedVersion(result, 'schema_version', SUPPORTED_SCHEMA_VERSION, 'result')
  requireSupportedVersion(result, 'model_version', SUPPORTED_MODEL_VERSION, 'result')

  if (!Array.isArray(result.countries) || result.countries.length === 0) {
    throw new ArtifactValidationError('result.countries must be a non-empty array')
  }
  result.countries.forEach((item, position) => {
    const path = `result.countries[${position}]`
    const country = requireRecord(item, path)
    requireString(country, 'country_code', path)
    requireNumber(country, 'year', path)
    requireNullableNumber(country, 'national_total_mwh', path)
  })

  if (result.scenario !== null) {
    requireRecord(result.scenario, 'result.scenario')
  }
  const inputTrace = requireRecord(result.input_trace, 'result.input_trace')
  requireSupportedVersion(
    inputTrace,
    'model_version',
    SUPPORTED_MODEL_VERSION,
    'result.input_trace',
  )

  return result as CalculationResult
}

async function fetchJson(url: string, fetcher: typeof fetch): Promise<unknown> {
  const response = await fetcher(url)
  if (!response.ok) {
    throw new Error(`Unable to load ${url}: ${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<unknown>
}

export async function loadArtifactIndex(
  url = '/artifacts/v1/index.json',
  fetcher: typeof fetch = fetch,
): Promise<ArtifactIndex> {
  return parseArtifactIndex(await fetchJson(url, fetcher))
}

export async function loadCalculationResult(
  dataset: DatasetIndexEntry,
  fetcher: typeof fetch = fetch,
): Promise<CalculationResult> {
  return parseCalculationResult(await fetchJson(dataset.paths.result, fetcher))
}

export interface DeveloperReferenceResult extends Record<string, unknown> {
  contract_version: string
  model_version: string
  reference_id: string
  profiles: Record<string, unknown>
  evidence_gaps: string[]
  sweeps: Record<string, unknown>
  scenarios: Array<Record<string, unknown>>
}

export function parseDeveloperReferenceResult(value: unknown): DeveloperReferenceResult {
  const result = requireRecord(value, 'developer reference result')
  requireSupportedVersion(result, 'contract_version', SUPPORTED_SCHEMA_VERSION, 'developer reference result')
  requireSupportedVersion(result, 'model_version', SUPPORTED_MODEL_VERSION, 'developer reference result')
  requireString(result, 'reference_id', 'developer reference result')
  requireRecord(result.profiles, 'developer reference result.profiles')
  requireRecord(result.sweeps, 'developer reference result.sweeps')
  if (!Array.isArray(result.evidence_gaps) || !result.evidence_gaps.every((item) => typeof item === 'string')) {
    throw new ArtifactValidationError('developer reference result.evidence_gaps must be string[]')
  }
  if (!Array.isArray(result.scenarios) || result.scenarios.length === 0) {
    throw new ArtifactValidationError('developer reference result.scenarios must be non-empty')
  }
  result.scenarios.forEach((item, position) => {
    const path = `developer reference result.scenarios[${position}]`
    const scenario = requireRecord(item, path)
    requireString(scenario, 'id', path)
    requireString(scenario, 'title', path)
    requireNumber(scenario, 'gpu_utilization', path)
    const workload = requireRecord(scenario.workload, `${path}.workload`)
    for (const key of ['concurrent_developers', 'jobs_per_developer', 'inference_duty_cycle', 'workday_hours']) {
      requireNumber(workload, key, `${path}.workload`)
    }
    requireNumber(scenario, 'node_it_w', path)
    requireNumber(scenario, 'node_it_kw', path)
    const capacity = requireRecord(scenario.capacity, `${path}.capacity`)
    const status = requireString(capacity, 'status', `${path}.capacity`)
    if (!['conditional_pass', 'overload', 'unknown'].includes(status)) {
      throw new ArtifactValidationError(`${path}.capacity.status is invalid`)
    }
    requireString(scenario, 'trace_id', path)
  })
  return result as DeveloperReferenceResult
}

export async function loadDeveloperReferenceResult(
  url = '/artifacts/v1/developer-reference/result.json',
  fetcher: typeof fetch = fetch,
): Promise<DeveloperReferenceResult> {
  return parseDeveloperReferenceResult(await fetchJson(url, fetcher))
}