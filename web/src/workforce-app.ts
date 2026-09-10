import { createIcons, Download, RotateCcw, Search, ArrowUpRight, Zap } from 'lucide'
import { csvFormat } from 'd3-dsv'
import workforceUrl from '../../data/norway/occupation-workforce-factors-2025-v0.csv?url'
import factorsUrl from '../../data/norway/occupation-factors-v0.csv?url'
import methodologyUrl from '../../docs/occupation-factor-starter.md?url'
import { occupations, getReference } from './workforce-data'
import { ADOPTION_PRESETS, DEFAULT_ANNUAL_HOURS, evaluateWorkforce, type FactorLevel } from './workforce'
import { triggerTextDownload } from './dashboard'

const labels = { low: 'Lav', base: 'Base', high: 'Høy' }
const format = (value: number | null, digits = 1) => value === null ? 'Ukjent' :
  new Intl.NumberFormat('nb-NO', { maximumFractionDigits: digits }).format(value)
const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;')

export function mountWorkforce(root: HTMLElement) {
  let adoption = 50
  let factorLevel: FactorLevel = 'base'
  let annualHours = DEFAULT_ANNUAL_HOURS
  let referenceId = 'baseline'
  let search = ''
  let coverage = 'assessed'
  let sort = 'energy'
  const calculate = () => evaluateWorkforce(occupations, adoption, factorLevel,
    { watts: getReference(referenceId).watts, annualHours })

  root.innerHTML = `
    <a class="skip-link" href="#analysis">Til analysen</a>
    <header class="workforce-header"><div class="workforce-brand"><i data-lucide="zap" aria-hidden="true"></i><div><h1>AI og strømbehov</h1><p>Norsk arbeidsliv · årsverksgrunnlag 2025</p></div></div>
      <nav aria-label="Seksjoner"><a href="#occupations">Yrker</a><a href="#reference">Referanse</a><a href="#sources">Kilder</a></nav></header>
    <main class="workforce-main" id="analysis">
      <div class="analysis-heading"><div><p class="eyebrow">AI-adopsjon i norsk arbeidsliv</p><h2>Estimert effekt- og energibehov</h2></div><span class="scenario-status">Betinget scenario · delvis dekning</span></div>
      <div class="analysis-grid">
        <section class="adoption-panel" aria-labelledby="adoption-title">
          <div class="panel-title"><h3 id="adoption-title">AI-adopsjon</h3><button type="button" class="icon-button" id="reset-workforce" title="Tilbakestill antakelser" aria-label="Tilbakestill antakelser"><i data-lucide="rotate-ccw"></i></button></div>
          <fieldset><legend>Andel årsverk som tar i bruk AI</legend><div class="segments">${Object.entries(ADOPTION_PRESETS).map(([level, value]) =>
            `<button type="button" data-preset="${value}" aria-pressed="${value === adoption}">${labels[level as FactorLevel]} <span>${value} %</span></button>`).join('')}</div></fieldset>
          <div class="adoption-value"><label for="adoption-number">Adopsjon</label><div><input id="adoption-number" type="number" min="0" max="100" step="1" value="50" aria-label="AI-adopsjon i prosent"><span>%</span></div></div>
          <input class="adoption-range" id="adoption-range" aria-label="Juster AI-adopsjon" type="range" min="0" max="100" step="1" value="50">
          <div class="range-labels"><span>0 %</span><span>100 %</span></div>
          <p class="assumption-note">Lik adopsjon i alle vurderte yrker, ved intensiteten yrkesfaktoren angir. Lav/base/høy er antakelser, ikke en prognose.</p>
          <div class="factor-control"><label for="factor-level">Relativ AI-intensitet</label><select id="factor-level"><option value="low">Lave yrkesfaktorer</option><option value="base" selected>Base yrkesfaktorer</option><option value="high">Høye yrkesfaktorer</option></select><p>Utvikler = 1,0 i alle faktorprofiler.</p></div>
        </section>
        <section class="estimate-panel" aria-labelledby="estimate-title">
          <div class="estimate-heading"><h3 id="estimate-title">For de vurderte yrkene</h3><span>IT-energi · aktiv arbeidstid</span></div>
          <div id="estimate-output" aria-live="polite" aria-atomic="true"></div>
          <div class="coverage-band" id="coverage-output"></div>
          <div class="uncertainty"><strong>Ikke et totalestimat for Norge.</strong><p>385 yrkeskoder mangler faktor. Selvstendig næringsdrivende er ikke med. Referansen bruker syntetiske effektantakelser og har uavklart kapasitet.</p><p>Effekt er årsgjennomsnitt, ikke topplast eller nettkapasitet. Behov knyttet til norske arbeidstakere sier ikke hvor beregningene utføres.</p></div>
        </section>
      </div>
      <section class="reference-band" id="reference" aria-labelledby="reference-title">
        <div><p class="eyebrow">Developer Reference</p><h3 id="reference-title">Utvikler = 1,0</h3><p>Normalisert AI-intensitet for et tungt AI-brukende utviklerårsverk. Betinget beregning, ikke verifisert empirisk kalibrering.</p></div>
        <div class="reference-controls"><label for="reference-profile">Effektreferanse</label><select id="reference-profile"><option value="baseline">Baseline · 220 W IT / aktiv utvikler</option><option value="low-load">Lav last · 140 W IT / aktiv utvikler</option><option value="heavy">Høy last · 270 W IT / aktiv utvikler</option></select><label for="annual-hours">Aktive timer per årsverk og år</label><input id="annual-hours" type="number" min="1" max="8760" step="1" value="1725"><p>Felles timegrunnlag for referanse og yrker. 1 725 timer er en scenarioantakelse, ikke målt av SSB.</p></div>
        <div class="calibration-output" id="calibration-output"></div>
      </section>
      <section class="occupation-section" id="occupations" aria-labelledby="occupation-title">
        <div class="occupation-heading"><div><p class="eyebrow">Årsverk × yrkesfaktor × adopsjon</p><h2 id="occupation-title">Yrkenes bidrag</h2></div><button class="export-button" id="export-workforce" type="button"><i data-lucide="download"></i>Eksporter CSV</button></div>
        <div class="occupation-toolbar"><div class="search-control"><i data-lucide="search" aria-hidden="true"></i><input type="search" id="occupation-search" aria-label="Søk etter yrke eller kode" placeholder="Søk etter yrke eller kode"></div><label>Vis<select id="coverage-filter"><option value="assessed">Vurderte yrker (22)</option><option value="all">Alle yrker (407)</option><option value="missing">Mangler faktor (385)</option></select></label><label>Sorter<select id="occupation-sort"><option value="energy">Størst energibidrag</option><option value="fte">Flest årsverk</option><option value="code">Yrkeskode</option></select></label></div>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Yrkesfordeling"><table class="occupation-data"><caption id="occupation-caption"></caption><thead><tr><th scope="col">STYRK-08 / yrke</th><th scope="col">Årsverk, proxy</th><th scope="col">AI-intensitet</th><th scope="col">Utviklerekv. årsverk</th><th scope="col">GWh / år</th><th scope="col">Andel av estimat</th></tr></thead><tbody id="occupation-rows"></tbody></table></div>
        <p class="table-note">Yrkesfaktorene er foreløpige scenarioantakelser uten faglig gjennomgang, ikke målte energiforhold eller andeler jobber som forsvinner. Ukjent er ikke null.</p>
      </section>
      <section class="sources-section" id="sources" aria-labelledby="sources-title"><p class="eyebrow">Datagrunnlag og avgrensning</p><h2 id="sources-title">Sporbart, men foreløpig</h2><div class="sources-grid">
        <div><h3>Årsverk fra SSB</h3><p>Årsverksproxyen er gjennomsnittet av kvartalsvise heltidsekvivalenter for 2025, basert på februar, mai, august og november. Dette er ikke observerte årstimer. 14 koder mangler minst ett kvartal. Selvstendig næringsdrivende mangler.</p><a href="https://www.ssb.no/statbank/table/11658" target="_blank" rel="noreferrer">SSB tabell 11658 <i data-lucide="arrow-up-right"></i></a><p>Hentet 10.09.2026 · SSB · CC BY 4.0</p><a href="${workforceUrl}" download="occupation-workforce-factors-2025-v0.csv">Årsverk og faktorer · 407 yrker</a></div>
        <div><h3>Yrkesfaktorer</h3><p>22 foreslåtte lav/base/høy-profiler, utviklet med AI-støtte og uten uavhengig validering. ILOs eksponeringsforskning gir bakgrunn for vurdering, ikke en omregning til watt. Faktorintervallet er ikke et konfidensintervall.</p><a href="${factorsUrl}" download="occupation-factors-v0.csv">Faktorprofiler og begrunnelser · CSV</a><a href="${methodologyUrl}" download="occupation-factor-starter.md">Metode og kildevurdering · Markdown</a></div>
        <div><h3>Referanse og beregningsgrense</h3><p>Årlig kWh = W per aktiv utvikler × aktive årstimer × utviklerekvivalente årsverk / 1 000. Gjennomsnittlig MW = GWh × 1 000 / 8 760 timer (2025).</p><p>IT-grensen inkluderer nodens øvrige IT-effekt. PUE er ikke lagt til. Tomgang utenfor aktive timer, sluttbrukerutstyr, trening og annet AI-forbruk er ikke inkludert.</p><a href="/artifacts/v1/developer-reference/result.json">Developer Reference · result.json</a><a href="/artifacts/v1/developer-reference/trace.json">Beregningsspor · trace.json</a><details><summary>Referansens evidensgap</summary><div id="reference-evidence"></div></details></div>
      </div></section>
      <footer class="workforce-footer"><span>Scenarioanalyse · Norge 2025 · Ikke en prognose</span><a href="?legacy=1">Tidligere forskningsvisning</a></footer>
    </main>`

  function updateTable() {
    const result = calculate()
    const filtered = result.rows.filter((row) =>
      (coverage === 'all' || (coverage === 'assessed' ? row.factors !== null : row.factors === null)) &&
      `${row.code} ${row.title}`.toLocaleLowerCase('nb-NO').includes(search.toLocaleLowerCase('nb-NO')))
    filtered.sort((first, second) => sort === 'code' ? first.code.localeCompare(second.code) :
      ((sort === 'fte' ? second.fte : second.gwh) ?? -1) -
      ((sort === 'fte' ? first.fte : first.gwh) ?? -1) || first.code.localeCompare(second.code))
    root.querySelector('#occupation-caption')!.textContent =
      `${filtered.length} yrker · ${format(adoption)} % adopsjon · ${labels[factorLevel].toLowerCase()} yrkesfaktorer · andel av beregnet delmengde`
    root.querySelector('#occupation-rows')!.innerHTML = filtered.length ? filtered.map((row) => {
      const share = row.gwh === null || !result.gwh ? null : row.gwh / result.gwh * 100
      return `<tr><th scope="row"><span class="occupation-code">${row.code}</span>${escape(row.title)}${row.rationale ? `<details><summary>Faktorbegrunnelse</summary><p>${escape(row.rationale)}</p></details>` : '<span class="unknown-label">Ikke vurdert</span>'}</th><td>${format(row.fte)}${row.fte === null ? '<small>Mangler kvartalsdata</small>' : ''}</td><td>${row.factor === null ? 'Ukjent' : `<span class="factor-number">${format(row.factor, 2)}</span><meter min="0" max="1" value="${row.factor}" aria-label="Relativ AI-intensitet for ${escape(row.title)}">${row.factor}</meter>`}</td><td>${format(row.equivalents)}</td><td>${format(row.gwh, 3)}</td><td>${share === null ? (row.gwh === null ? 'Ukjent' : 'Ikke definert') : `<span>${format(share)} %</span><div class="contribution-track"><div style="width:${share}%"></div></div>`}</td></tr>`
    }).join('') : '<tr><td colspan="6">Ingen yrker samsvarer med søket.</td></tr>'
  }

  function update() {
    const result = calculate()
    const reference = getReference(referenceId)
    const low = evaluateWorkforce(occupations, adoption, 'low', { watts: reference.watts, annualHours })
    const high = evaluateWorkforce(occupations, adoption, 'high', { watts: reference.watts, annualHours })
    root.querySelector('#estimate-output')!.innerHTML = `<div class="primary-metrics"><div><span>Gjennomsnittlig effekt</span><strong data-metric="mw">${format(result.mw, 2)} <small>MW</small></strong><p>Fordelt over årets 8 760 timer</p></div><div><span>Årlig energi</span><strong data-metric="gwh">${format(result.gwh, 2)} <small>GWh</small></strong><p>Ved ${format(adoption)} % AI-adopsjon</p></div></div><div class="equivalent-line"><span>Utviklerekvivalente årsverk</span><strong data-metric="equivalents">${format(result.equivalents, 0)}</strong></div><p class="sensitivity">Lav–høy yrkesfaktor, samme adopsjon og referanse: <strong>${format(low.mw, 2)}–${format(high.mw, 2)} MW</strong> · ${format(low.gwh, 2)}–${format(high.gwh, 2)} GWh/år. Scenariointervall, ikke konfidensintervall.</p>`
    root.querySelector('#coverage-output')!.innerHTML = `<div><strong>${result.assessedCodes} / ${occupations.length}</strong><span>yrkeskoder har faktor</span></div><div><strong>${format(result.coveragePercent)} %</strong><span>av kjente årsverksproxyer dekket</span></div><p>${format(result.coveredFte, 0)} av ${format(result.knownFte, 2)} kjente årsverk. Uvurderte yrker er ikke ekstrapolert.</p><div class="coverage-track" role="img" aria-label="${format(result.coveragePercent)} prosent av kjente årsverk dekket"><div style="width:${result.coveragePercent ?? 0}%"></div></div>`
    root.querySelector('#calibration-output')!.innerHTML = `<span>Årlig IT-energi per referanseårsverk</span><strong>${format(result.annualKwhPerFte)} <small>kWh</small></strong><p>${format(reference.watts)} W × ${format(annualHours, 0)} timer / 1 000</p><p>Ingen PUE eller tomgang utenfor aktive timer lagt til.</p><span class="reference-status">Kapasitet: uavklart</span>`
    root.querySelector('#reference-evidence')!.innerHTML = `<p>${escape(reference.referenceId)} · ${escape(reference.traceId)}</p><p>${escape(reference.capacityReason ?? '')}</p>${reference.evidenceGaps.map((gap) => `<p>${escape(gap)}</p>`).join('')}`
    for (const input of root.querySelectorAll<HTMLInputElement>('#adoption-range, #adoption-number')) input.value = String(adoption)
    for (const button of root.querySelectorAll<HTMLButtonElement>('[data-preset]')) button.setAttribute('aria-pressed', String(Number(button.dataset.preset) === adoption))
    updateTable()
  }

  for (const input of root.querySelectorAll<HTMLInputElement>('#adoption-range, #adoption-number')) {
    input.addEventListener('input', () => {
      if (input.value === '' || !input.validity.valid) return
      adoption = input.valueAsNumber
      update()
    })
    input.addEventListener('change', () => { input.value = String(adoption) })
  }
  for (const button of root.querySelectorAll<HTMLButtonElement>('[data-preset]')) {
    button.addEventListener('click', () => { adoption = Number(button.dataset.preset); update() })
  }
  root.querySelector<HTMLSelectElement>('#factor-level')!.addEventListener('change', (event) => {
    factorLevel = (event.target as HTMLSelectElement).value as FactorLevel
    update()
  })
  root.querySelector<HTMLSelectElement>('#reference-profile')!.addEventListener('change', (event) => {
    referenceId = (event.target as HTMLSelectElement).value
    update()
  })
  const hoursInput = root.querySelector<HTMLInputElement>('#annual-hours')!
  hoursInput.addEventListener('input', () => {
    if (hoursInput.value === '' || !hoursInput.validity.valid) return
    annualHours = hoursInput.valueAsNumber
    update()
  })
  hoursInput.addEventListener('change', () => { hoursInput.value = String(annualHours) })
  root.querySelector('#reset-workforce')!.addEventListener('click', () => {
    adoption = 50; factorLevel = 'base'; annualHours = DEFAULT_ANNUAL_HOURS; referenceId = 'baseline'
    root.querySelector<HTMLSelectElement>('#factor-level')!.value = factorLevel
    root.querySelector<HTMLSelectElement>('#reference-profile')!.value = referenceId
    hoursInput.value = String(annualHours)
    update()
  })
  root.querySelector('#occupation-search')!.addEventListener('input', (event) => {
    search = (event.target as HTMLInputElement).value.trim()
    updateTable()
  })
  root.querySelector('#coverage-filter')!.addEventListener('change', (event) => {
    coverage = (event.target as HTMLSelectElement).value
    updateTable()
  })
  root.querySelector('#occupation-sort')!.addEventListener('change', (event) => {
    sort = (event.target as HTMLSelectElement).value
    updateTable()
  })
  root.querySelector('#export-workforce')!.addEventListener('click', () => {
    const result = calculate()
    const reference = getReference(referenceId)
    const csv = csvFormat(result.rows.map((row) => ({
      styrk08_code: row.code, occupation: row.title, annual_fte_proxy_2025: row.fte,
      factor_status: row.factor === null ? 'not_assessed' : 'assumption',
      factor_level: factorLevel, factor: row.factor, adoption_percent: adoption,
      developer_equivalent_fte: row.equivalents, annual_it_gwh: row.gwh, annual_average_it_mw: row.mw,
      reference_id: reference.referenceId, trace_id: reference.traceId,
      reference_watts: reference.watts, annual_active_hours_assumption: annualHours,
      calendar_hours: 8760, boundary: 'node IT; active hours only; no PUE or off-hours idle',
      evidence: 'partial estimate; assumed factors; synthetic reference power; unresolved capacity; no self-employed',
    })))
    triggerTextDownload({ filename: 'ai-adopsjon-norge-2025.csv', content: csv, mediaType: 'text/csv;charset=utf-8' })
  })
  update()
  createIcons({ icons: { Download, RotateCcw, Search, ArrowUpRight, Zap }, root })
}