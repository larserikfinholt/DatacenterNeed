export const DASHBOARD_SCENARIO_VERSION = '1.0' as const

export type AdoptionPresetName = 'conservative' | 'moderate' | 'high'
export type PlacementPresetName = 'cloud-heavy' | 'hybrid' | 'local-heavy'

export interface DashboardScenarioOverridesV1 {
  demandMultiplier: number
  cloudShare: number
  domesticHostingShare: number
  cloudPue: number
}

export interface DashboardScenarioV1 {
  schemaVersion: typeof DASHBOARD_SCENARIO_VERSION
  datasetId: string
  adoption: AdoptionPresetName
  placement: PlacementPresetName
  overrides: DashboardScenarioOverridesV1
}

export interface ScenarioArtifactSource {
  datasetId: string
  inputTrace: unknown
  occupations: unknown
}

export interface ScenarioProvenance {
  assumption_source_ids: string[]
  observed_source_ids: string[]
  reported_source_ids: string[]
  synthetic_source_ids: string[]
}

export interface ScenarioCategoryResult {
  category: string
  pre_rebound_activity_units: number | null
  activity_units: number | null
  rebound_activity_units: number
  cloud_it_mwh: number | null
  cloud_facility_mwh: number | null
  local_device_mwh: number | null
  known_total_mwh: number | null
  status: 'known' | 'unknown'
  missing_reason: string | null
  provenance: ScenarioProvenance
}

export interface HostingResult {
  domestic_consumption_mwh: number
  domestically_hosted_mwh: number
  imported_mwh: number
  exported_hosting_mwh: number | null
  allocated_domestic_capacity_mwh: number | null
  residual_capacity_mwh: number | null
  capacity_gap_mwh: number | null
  boundary: 'cloud_facility'
  residual_interpretation: string
  exported_hosting_missing_reason: string | null
  available_domestic_capacity_missing_reason: string | null
  provenance: ScenarioProvenance
}

export interface ScenarioCombinationResult {
  id: string
  adoption: AdoptionPresetName
  placement: PlacementPresetName
  parameters: {
    demand_multiplier: number
    cloud_share: number
    domestic_hosting_share: number
    cloud_pue: number
  }
  categories: ScenarioCategoryResult[]
  known_cloud_facility_subtotal_mwh: number | null
  known_local_device_subtotal_mwh: number | null
  known_national_subtotal_mwh: number | null
  national_total_mwh: number | null
  scope_status: 'complete' | 'incomplete'
  hosting: HostingResult | null
}

type SourceKind = 'assumption' | 'observed' | 'reported' | 'synthetic'

interface SourceRecord {
  id: string
  source_kind: SourceKind
}

interface Observation {
  id: string
  value: number | null
}

interface CoverageFrame {
  country_code: string
  year: number
  cell_observation_ids: Record<string, string>
  occupation_cell_assignments: Record<string, string[]>
  uncovered_cell_ids: string[]
}

interface OccupationRow {
  occupation_id: string
  country_code: string
  year: number
  annual_requests: number | null
  source_ids: string[]
}

interface CategoryActivity {
  category: string
  pre_rebound_activity_units: number | null
  missing_reason: string | null
  source_ids: string[]
}

interface ReboundInput {
  category: string
  baseline_activity_units: number
  additional_activity_fraction: number
  source_ids: string[]
}

interface AdoptionPreset {
  name: AdoptionPresetName
  occupation_activity_multiplier: number
  category_activities: CategoryActivity[]
  rebound: ReboundInput | null
  source_ids: string[]
}

interface PlacementPreset {
  name: PlacementPresetName
  cloud_share: number
  domestic_hosting_share: number
  source_ids: string[]
}

interface EnergyIntensity {
  category: string
  cloud_kwh_per_activity_unit: number | null
  cloud_missing_reason: string | null
  cloud_boundary: 'cloud_it' | 'cloud_facility'
  local_device_kwh_per_activity_unit: number | null
  local_device_missing_reason: string | null
  source_ids: string[]
}

interface HostingInput {
  exported_hosting_mwh: number | null
  exported_hosting_missing_reason: string | null
  available_domestic_capacity_mwh: number | null
  available_domestic_capacity_missing_reason: string | null
  source_ids: string[]
}

interface ScenarioConfiguration {
  country_code: string
  year: number
  adoption_presets: AdoptionPreset[]
  placement_presets: PlacementPreset[]
  energy_intensities: EnergyIntensity[]
  hosting: HostingInput
}

interface InputTrace {
  sources: SourceRecord[]
  observations: Observation[]
  occupation_coverage: CoverageFrame[]
  cloud_pue: { value: number; source_ids: string[] }
  scenario: ScenarioConfiguration | null
}

const CATEGORY_ORDER = [
  'occupation_human_inference',
  'autonomous_background_inference',
  'consumer_ai',
  'foundation_training',
  'fine_tuning',
  'retrieval_embeddings',
  'non_ai',
] as const

const ADOPTIONS = new Set<AdoptionPresetName>(['conservative', 'moderate', 'high'])
const PLACEMENTS = new Set<PlacementPresetName>(['cloud-heavy', 'hybrid', 'local-heavy'])

export class ScenarioValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ScenarioValidationError'
  }
}

export class ScenarioUnavailableError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ScenarioUnavailableError'
  }
}

function requireRecord(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ScenarioValidationError(`${path} must be an object`)
  }
  return value as Record<string, unknown>
}

function requireExactKeys(record: Record<string, unknown>, keys: string[], path: string): void {
  const actual = Object.keys(record).sort()
  const expected = [...keys].sort()
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new ScenarioValidationError(`${path} must contain exactly ${keys.join(', ')}`)
  }
}

function requireFiniteNumber(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new ScenarioValidationError(`${path} must be a finite number`)
  }
  return value
}

function requireRange(value: unknown, path: string, minimum: number, maximum?: number): number {
  const number = requireFiniteNumber(value, path)
  if (number < minimum || (maximum !== undefined && number > maximum)) {
    const range = maximum === undefined ? `at least ${minimum}` : `between ${minimum} and ${maximum}`
    throw new ScenarioValidationError(`${path} must be ${range}`)
  }
  return number
}

export function parseDashboardScenario(value: unknown): DashboardScenarioV1 {
  const selection = requireRecord(value, 'selection')
  requireExactKeys(
    selection,
    ['schemaVersion', 'datasetId', 'adoption', 'placement', 'overrides'],
    'selection',
  )
  if (selection.schemaVersion !== DASHBOARD_SCENARIO_VERSION) {
    throw new ScenarioValidationError('selection.schemaVersion must be 1.0')
  }
  if (
    typeof selection.datasetId !== 'string' ||
    !/^[a-z0-9][a-z0-9._-]*$/.test(selection.datasetId)
  ) {
    throw new ScenarioValidationError('selection.datasetId must be a valid dataset identifier')
  }
  if (!ADOPTIONS.has(selection.adoption as AdoptionPresetName)) {
    throw new ScenarioValidationError('selection.adoption is invalid')
  }
  if (!PLACEMENTS.has(selection.placement as PlacementPresetName)) {
    throw new ScenarioValidationError('selection.placement is invalid')
  }

  const overrides = requireRecord(selection.overrides, 'selection.overrides')
  requireExactKeys(
    overrides,
    ['demandMultiplier', 'cloudShare', 'domesticHostingShare', 'cloudPue'],
    'selection.overrides',
  )

  return {
    schemaVersion: DASHBOARD_SCENARIO_VERSION,
    datasetId: selection.datasetId,
    adoption: selection.adoption as AdoptionPresetName,
    placement: selection.placement as PlacementPresetName,
    overrides: {
      demandMultiplier: requireRange(
        overrides.demandMultiplier,
        'selection.overrides.demandMultiplier',
        0,
      ),
      cloudShare: requireRange(overrides.cloudShare, 'selection.overrides.cloudShare', 0, 1),
      domesticHostingShare: requireRange(
        overrides.domesticHostingShare,
        'selection.overrides.domesticHostingShare',
        0,
        1,
      ),
      cloudPue: requireRange(overrides.cloudPue, 'selection.overrides.cloudPue', 1),
    },
  }
}

export function dashboardScenarioToSearchParams(value: unknown): URLSearchParams {
  const selection = parseDashboardScenario(value)
  return new URLSearchParams({
    v: selection.schemaVersion,
    dataset: selection.datasetId,
    adoption: selection.adoption,
    placement: selection.placement,
    demand: String(selection.overrides.demandMultiplier),
    cloud: String(selection.overrides.cloudShare),
    domestic: String(selection.overrides.domesticHostingShare),
    pue: String(selection.overrides.cloudPue),
  })
}

function provenance(
  sourceKinds: Map<string, SourceKind>,
  sourceIds: Iterable<string>,
): ScenarioProvenance {
  const ids = [...new Set(sourceIds)]
  const byKind = (kind: SourceKind) =>
    ids.filter((sourceId) => sourceKinds.get(sourceId) === kind).sort()
  return {
    assumption_source_ids: byKind('assumption'),
    observed_source_ids: byKind('observed'),
    reported_source_ids: byKind('reported'),
    synthetic_source_ids: byKind('synthetic'),
  }
}

function sum(values: number[]): number {
  let total = 0
  let compensation = 0
  for (const value of values) {
    const next = total + value
    compensation +=
      Math.abs(total) >= Math.abs(value) ? total - next + value : value - next + total
    total = next
  }
  return total + compensation
}

function requireScenarioSource(source: ScenarioArtifactSource): {
  trace: InputTrace
  scenario: ScenarioConfiguration
  occupationRows: OccupationRow[]
} {
  const trace = requireRecord(source.inputTrace, 'source.inputTrace') as unknown as InputTrace
  if (trace.scenario === null || trace.scenario === undefined) {
    throw new ScenarioUnavailableError(`Dataset ${source.datasetId} has no scenario configuration`)
  }
  if (!Array.isArray(source.occupations)) {
    throw new ScenarioValidationError('source.occupations must be an array')
  }
  return {
    trace,
    scenario: trace.scenario,
    occupationRows: source.occupations as OccupationRow[],
  }
}

export function evaluateDashboardScenario(
  source: ScenarioArtifactSource,
  value: unknown,
): ScenarioCombinationResult {
  const selection = parseDashboardScenario(value)
  if (selection.datasetId !== source.datasetId) {
    throw new ScenarioValidationError(
      `selection.datasetId ${selection.datasetId} does not match ${source.datasetId}`,
    )
  }
  const { trace, scenario, occupationRows } = requireScenarioSource(source)
  const adoption = scenario.adoption_presets.find((item) => item.name === selection.adoption)
  const placement = scenario.placement_presets.find((item) => item.name === selection.placement)
  if (adoption === undefined || placement === undefined) {
    throw new ScenarioUnavailableError('Selected scenario preset is unavailable')
  }

  const { demandMultiplier, cloudShare, domesticHostingShare, cloudPue } = selection.overrides
  const intensities = new Map(scenario.energy_intensities.map((item) => [item.category, item]))
  const activities = new Map(adoption.category_activities.map((item) => [item.category, item]))
  const countryRows = occupationRows.filter(
    (row) => row.country_code === scenario.country_code && row.year === scenario.year,
  )
  const coverageFrame = trace.occupation_coverage.find(
    (frame) => frame.country_code === scenario.country_code && frame.year === scenario.year,
  )
  const assignedOccupationIds =
    coverageFrame === undefined
      ? null
      : new Set(Object.keys(coverageFrame.occupation_cell_assignments))
  const relevantRows =
    assignedOccupationIds === null
      ? countryRows
      : countryRows.filter((row) => assignedOccupationIds.has(row.occupation_id))
  const rowsByOccupation = new Map(relevantRows.map((row) => [row.occupation_id, row]))
  const observations = new Map(trace.observations.map((item) => [item.id, item]))
  let coverageComplete = coverageFrame !== undefined
  if (coverageFrame !== undefined) {
    coverageComplete =
      coverageFrame.uncovered_cell_ids.length === 0 &&
      Object.values(coverageFrame.cell_observation_ids).every(
        (observationId) => observations.get(observationId)?.value != null,
      ) &&
      Object.keys(coverageFrame.occupation_cell_assignments).every(
        (occupationId) => rowsByOccupation.get(occupationId)?.annual_requests != null,
      )
  }
  const humanActivity =
    relevantRows.length === 0 || relevantRows.some((row) => row.annual_requests === null)
      ? null
      : sum(relevantRows.map((row) => row.annual_requests as number)) *
        adoption.occupation_activity_multiplier
  const humanSources = relevantRows.flatMap((row) => row.source_ids)
  const sourceKinds = new Map(trace.sources.map((item) => [item.id, item.source_kind]))
  const categoryRows: ScenarioCategoryResult[] = []
  const cloudCategorySourceIds = new Set<string>()

  for (const category of CATEGORY_ORDER) {
    const intensity = intensities.get(category)
    if (intensity === undefined) {
      throw new ScenarioUnavailableError(`Scenario intensity ${category} is unavailable`)
    }
    const commonSourceIds = new Set([
      ...adoption.source_ids,
      ...placement.source_ids,
      ...intensity.source_ids,
    ])
    if (cloudShare > 0 && intensity.cloud_boundary === 'cloud_it') {
      trace.cloud_pue.source_ids.forEach((sourceId) => commonSourceIds.add(sourceId))
    }

    let preReboundActivityUnits: number | null
    let missingReason: string | null
    let sourceIds: Set<string>
    let reboundActivityUnits = 0
    if (category === 'occupation_human_inference') {
      preReboundActivityUnits = humanActivity
      missingReason =
        humanActivity === null
          ? 'Occupation-linked annual requests are incomplete for the scenario country/year.'
          : null
      sourceIds = new Set([...humanSources, ...commonSourceIds])
    } else {
      const activity = activities.get(category)
      if (activity === undefined) {
        throw new ScenarioUnavailableError(`Scenario activity ${category} is unavailable`)
      }
      preReboundActivityUnits = activity.pre_rebound_activity_units
      missingReason = activity.missing_reason
      sourceIds = new Set([...activity.source_ids, ...commonSourceIds])
      if (adoption.rebound?.category === category) {
        reboundActivityUnits =
          adoption.rebound.baseline_activity_units * adoption.rebound.additional_activity_fraction
        adoption.rebound.source_ids.forEach((sourceId) => sourceIds.add(sourceId))
      }
    }

    const activityUnits =
      preReboundActivityUnits === null
        ? null
        : preReboundActivityUnits + reboundActivityUnits
    if (activityUnits === null) {
      categoryRows.push({
        category,
        pre_rebound_activity_units: null,
        activity_units: null,
        rebound_activity_units: reboundActivityUnits,
        cloud_it_mwh: null,
        cloud_facility_mwh: null,
        local_device_mwh: null,
        known_total_mwh: null,
        status: 'unknown',
        missing_reason: missingReason,
        provenance: provenance(sourceKinds, sourceIds),
      })
      continue
    }

    const scaledActivity = activityUnits * demandMultiplier
    const cloudUsed = cloudShare > 0
    const localUsed = cloudShare < 1
    const missingReasons: (string | null)[] = []
    let cloudKwh: number | null
    if (cloudUsed && intensity.cloud_kwh_per_activity_unit === null) {
      cloudKwh = null
      missingReasons.push(intensity.cloud_missing_reason)
    } else {
      cloudKwh = scaledActivity * cloudShare * (intensity.cloud_kwh_per_activity_unit ?? 0)
    }
    let localKwh: number | null
    if (localUsed && intensity.local_device_kwh_per_activity_unit === null) {
      localKwh = null
      missingReasons.push(intensity.local_device_missing_reason)
    } else {
      localKwh =
        scaledActivity * (1 - cloudShare) * (intensity.local_device_kwh_per_activity_unit ?? 0)
    }
    const cloudItMwh =
      cloudKwh === null || intensity.cloud_boundary === 'cloud_facility'
        ? null
        : cloudKwh / 1_000
    const cloudFacilityMwh =
      cloudKwh === null
        ? null
        : intensity.cloud_boundary === 'cloud_it'
          ? (cloudKwh / 1_000) * cloudPue
          : cloudKwh / 1_000
    const localDeviceMwh = localKwh === null ? null : localKwh / 1_000
    const knownTotalMwh =
      cloudFacilityMwh === null || localDeviceMwh === null
        ? null
        : cloudFacilityMwh + localDeviceMwh
    if (cloudUsed && cloudFacilityMwh !== null) {
      sourceIds.forEach((sourceId) => cloudCategorySourceIds.add(sourceId))
    }
    categoryRows.push({
      category,
      pre_rebound_activity_units: preReboundActivityUnits! * demandMultiplier,
      activity_units: scaledActivity,
      rebound_activity_units: reboundActivityUnits * demandMultiplier,
      cloud_it_mwh: cloudItMwh,
      cloud_facility_mwh: cloudFacilityMwh,
      local_device_mwh: localDeviceMwh,
      known_total_mwh: knownTotalMwh,
      status: knownTotalMwh === null ? 'unknown' : 'known',
      missing_reason: missingReasons.length === 0 ? null : missingReasons.join('; '),
      provenance: provenance(sourceKinds, sourceIds),
    })
  }

  const complete =
    categoryRows.filter((item) => item.known_total_mwh !== null).length ===
      CATEGORY_ORDER.length && coverageComplete
  const knownCloudValues = categoryRows.flatMap((item) =>
    item.cloud_facility_mwh === null ? [] : [item.cloud_facility_mwh],
  )
  const knownLocalValues = categoryRows.flatMap((item) =>
    item.local_device_mwh === null ? [] : [item.local_device_mwh],
  )
  const knownCloud = sum(knownCloudValues)
  const knownLocal = sum(knownLocalValues)
  let hosting: HostingResult | null = null
  if (complete) {
    const domesticallyHosted = knownCloud * domesticHostingShare
    const imported = knownCloud - domesticallyHosted
    const exports = scenario.hosting.exported_hosting_mwh
    const available = scenario.hosting.available_domestic_capacity_mwh
    const allocated = exports === null || available === null ? null : domesticallyHosted + exports
    hosting = {
      domestic_consumption_mwh: knownCloud,
      domestically_hosted_mwh: domesticallyHosted,
      imported_mwh: imported,
      exported_hosting_mwh: exports,
      allocated_domestic_capacity_mwh: allocated,
      residual_capacity_mwh:
        allocated === null || available === null ? null : Math.max(available - allocated, 0),
      capacity_gap_mwh:
        allocated === null || available === null ? null : Math.max(allocated - available, 0),
      boundary: 'cloud_facility',
      residual_interpretation: 'Unallocated capacity; not inferred export or waste.',
      exported_hosting_missing_reason: scenario.hosting.exported_hosting_missing_reason,
      available_domestic_capacity_missing_reason:
        scenario.hosting.available_domestic_capacity_missing_reason,
      provenance: provenance(sourceKinds, [
        ...scenario.hosting.source_ids,
        ...placement.source_ids,
        ...cloudCategorySourceIds,
      ]),
    }
  }

  return {
    id: `${adoption.name}__${placement.name}`,
    adoption: adoption.name,
    placement: placement.name,
    parameters: {
      demand_multiplier: demandMultiplier,
      cloud_share: cloudShare,
      domestic_hosting_share: domesticHostingShare,
      cloud_pue: cloudPue,
    },
    categories: categoryRows,
    known_cloud_facility_subtotal_mwh:
      knownCloudValues.length === 0 ? null : knownCloud,
    known_local_device_subtotal_mwh: knownLocalValues.length === 0 ? null : knownLocal,
    known_national_subtotal_mwh:
      knownCloudValues.length === 0 && knownLocalValues.length === 0
        ? null
        : knownCloud + knownLocal,
    national_total_mwh: complete ? knownCloud + knownLocal : null,
    scope_status: complete ? 'complete' : 'incomplete',
    hosting,
  }
}