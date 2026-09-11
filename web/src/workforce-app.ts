import { createIcons, Download, RotateCcw, Search, ArrowUpRight, Zap } from 'lucide'
import { csvFormat } from 'd3-dsv'
import workforceUrl from '../../data/norway/occupation-workforce-factors-2025-v0.csv?url'
import factorsUrl from '../../data/norway/occupation-factors-v0.csv?url'
import methodologyUrl from '../../docs/occupation-factor-starter.md?url'
import { occupations, getReference } from './workforce-data'
import { DEFAULT_ANNUAL_HOURS, evaluateWorkforce, type FactorFallback,
  type FactorLevel } from './workforce'
import { aiShareOfCommitted, buildNationalComparison, type NationalComparisonPoint } from './national-comparison'
import { triggerTextDownload } from './dashboard'

const labels = { low: 'Lav', base: 'Base', high: 'Høy' }
const format = (value: number | null, digits = 1) => value === null ? 'Ukjent' :
  new Intl.NumberFormat('nb-NO', { maximumFractionDigits: digits }).format(value)
// Aggressive dashboard rounding: whole numbers from 10 and up, 1 decimal below 10, 2 decimals below 1.
const formatRounded = (value: number | null) => {
  if (value === null) return 'Ukjent'
  const abs = Math.abs(value)
  const digits = abs >= 10 ? 0 : abs >= 1 ? 1 : 2
  return new Intl.NumberFormat('nb-NO', { maximumFractionDigits: digits }).format(value)
}
const formatPower = (mw: number | null) =>
  mw === null ? 'Ukjent' : Math.abs(mw) < 1 ? `${formatRounded(mw * 1000)} kW` : `${formatRounded(mw)} MW`
// Picks kWh/MWh/GWh/TWh so the displayed number stays readable at any scale.
const formatEnergy = (gwh: number | null) => {
  if (gwh === null) return 'Ukjent'
  const kwh = gwh * 1e6
  const abs = Math.abs(kwh)
  if (abs < 1000) return `${formatRounded(kwh)} kWh/år`
  if (abs < 1e6) return `${formatRounded(kwh / 1000)} MWh/år`
  if (abs < 1e9) return `${formatRounded(kwh / 1e6)} GWh/år`
  return `${formatRounded(kwh / 1e9)} TWh/år`
}
const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;')

function comparisonChart(points: NationalComparisonPoint[]) {
  const plot = { left: 54, right: 676, top: 24, bottom: 280 }
  const maxMw = Math.ceil(Math.max(...points.map((point) => point.includingAnnouncedMw)) / 500) * 500
  const x = (index: number) => plot.left + index * (plot.right - plot.left) / (points.length - 1)
  const y = (mw: number) => plot.bottom - mw / maxMw * (plot.bottom - plot.top)
  const area = (values: number[]) => `${plot.left},${plot.bottom} ${values.map((value, index) => `${x(index)},${y(value)}`).join(' ')} ${plot.right},${plot.bottom}`
  const band = (upper: number[], lower: number[]) => `${upper.map((value, index) => `${x(index)},${y(value)}`).join(' ')} ${lower.map((_, index) => `${x(lower.length - 1 - index)},${y(lower[lower.length - 1 - index])}`).join(' ')}`
  const committed = points.map((point) => point.committedTotalMw)
  const announced = points.map((point) => point.includingAnnouncedMw)
  const existing = points.map((point) => point.existingMw)
  const ai = points.map((point) => point.aiMw ?? 0)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => ({ mw: maxMw * fraction, y: y(maxMw * fraction) }))
  const last = points.at(-1)!
  const ratio = last.aiMw !== null && last.aiMw > 0 ? last.committedTotalMw / last.aiMw : null
  const annotationX = Math.min(x(points.length - 1) - 158, plot.right - 158)
  const annotationY = Math.max(y(last.aiMw ?? 0) - 60, plot.top + 4)
  return `<svg class="comparison-chart" viewBox="0 0 700 330" role="img" aria-labelledby="chart-title chart-desc">
    <title id="chart-title">Aktiv AI-relatert IT-last og norsk datasenterkapasitet, 2025 til 2030</title>
    <desc id="chart-desc">IT-lasten i aktive arbeidstimer vises på samme lineære MW-skala som eksisterende, forpliktet og annonsert datasenterkapasitet.</desc>
    <defs><pattern id="announced-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="8" stroke="#829097" stroke-width="2" /></pattern></defs>
    ${ticks.map((tick) => `<line class="chart-grid" x1="${plot.left}" x2="${plot.right}" y1="${tick.y}" y2="${tick.y}"/><text class="chart-tick" x="${plot.left - 10}" y="${tick.y + 4}" text-anchor="end">${tick.mw}</text>`).join('')}
    <polygon class="chart-existing" points="${area(existing)}"/><polygon class="chart-committed" points="${band(committed, existing)}"/><polygon class="chart-announced" points="${band(announced, committed)}"/>
    <polyline class="chart-ai" points="${ai.map((value, index) => `${x(index)},${y(value)}`).join(' ')}"/>${ai.map((value, index) => `<circle class="chart-ai-point" cx="${x(index)}" cy="${y(value)}" r="3.5"/>`).join('')}
    ${points.map((point, index) => `<text class="chart-year" x="${x(index)}" y="${plot.bottom + 24}" text-anchor="middle">${point.year}</text>`).join('')}<text class="chart-axis-title" x="12" y="18">MW</text>
    <g class="chart-annotation" transform="translate(${annotationX},${annotationY})"><rect x="-10" y="-16" width="168" height="58" rx="4"/><text x="0" y="0">AI: ${formatPower(last.aiMw)}</text><text x="0" y="16">Forpliktet: ${formatRounded(last.committedTotalMw)} MW</text>${ratio === null ? '' : `<text x="0" y="32">≈ ${formatRounded(ratio)}× større</text>`}</g>
  </svg>`
}

export function mountWorkforce(root: HTMLElement) {
  let currentAdoption = 20
  let targetAdoption = 50
  let adoptionRampYears = 1
  let factorLevel: FactorLevel = 'base'
  let factorFallback: FactorFallback = 'fte-weighted-mean'
  let annualHours = DEFAULT_ANNUAL_HOURS
  let search = ''
  let coverage = 'assessed'
  let sort = 'energy'
  const calculate = () => evaluateWorkforce(occupations, targetAdoption, factorLevel,
    { watts: getReference().watts, annualHours }, factorFallback)

  root.innerHTML = `
    <a class="skip-link" href="#analysis">Til analysen</a>
    <header class="workforce-header"><div class="workforce-brand"><i data-lucide="zap" aria-hidden="true"></i><div><h1>AI og strømbehov</h1><p>Norsk arbeidsliv · årsverksgrunnlag 2025</p></div></div>
      <nav aria-label="Seksjoner"><a href="#comparison">Sammenligning</a><a href="#settings">Innstillinger</a><a href="#assumptions">Forutsetninger</a><a href="#occupations">Yrker</a></nav></header>
    <main class="workforce-main" id="analysis">
      <section class="comparison-hero" id="comparison" aria-labelledby="comparison-title">
        <div class="comparison-heading"><div><p class="eyebrow">Estimert AI-effekt fra norsk arbeidsliv</p><h2 id="comparison-title">Hvor stort er behovet sammenlignet med det Norge bygger?</h2></div><span class="scenario-status" id="scenario-status">Betinget scenario · delvis yrkesdekning</span></div>
        <p class="headline-claim" id="headline-claim" aria-live="polite"></p>
        <div class="headline-metrics" id="headline-output" aria-live="polite" aria-atomic="true"></div>
        <p class="interpretation" id="interpretation-output"></p>
        <figure class="comparison-figure"><figcaption><span>Estimert AI-effektbehov mot datasenterkapasitet</span><small>Samme lineære MW-skala · 2025–2030</small></figcaption><div id="comparison-chart"></div><div class="chart-legend"><span class="legend-ai">Estimert AI-effektbehov</span><span class="legend-existing">Eksisterende</span><span class="legend-committed">Under bygging / forpliktet</span><span class="legend-announced">Annonsert / planlagt, ikke garantert</span></div></figure>
        <p class="capacity-caveat"><strong>Foreløpig kapasitetsbane.</strong> Tallene er scenarioverdier for å teste sammenligningen, ikke en revidert nasjonal prosjektinventering. Kategoriene må erstattes med kildebelagte prosjektdata før konklusjonen kan leses som en prognose.</p>
      </section>
      <section class="assumptions-section" id="assumptions" aria-label="Forklaringer"><p class="eyebrow">Forklaringer</p><div class="scope-columns"><div><h2>Hva sammenligningen viser</h2><p>Vi estimerer hvor mye <strong>økt bruk av AI i norsk arbeidsliv</strong> kan øke behovet for datasenterkraft.</p><p>Dette sammenlignes med hvor mye datasenterkapasitet som finnes, bygges og planlegges i Norge.</p><p>Dersom AI-behovet fra norsk arbeidsliv bare utgjør en liten del av kapasiteten, tyder det på at <strong>utbyggingen i hovedsak drives av andre behov enn AI-bruk i norsk arbeidsliv</strong>.</p></div><div><h2>Hvordan har vi regnet ut dette?</h2><p>Vi bruker utviklere som referanseyrke, fordi vi antar at dette er blant yrkesgruppene som kan ha høyest og mest kontinuerlig nytte av AI.</p><p>Først estimerer vi hvor mye effekt en aktiv utvikler kan kreve ved omfattende AI-bruk. Deretter skaleres andre yrker relativt til denne referansen basert på yrkestype, arbeidsoppgaver og data fra SSB.</p><p>Til slutt kombineres dette med antall årsverk og forventet AI-adopsjon i norsk arbeidsliv.</p></div><div><h2>Hva er utelatt?</h2><p>Beregningen forsøker ikke å beskrive alt fremtidig datasenterbehov i Norge.</p><ul><li>trening av store AI-modeller</li><li>AI-bruk for utenlandske kunder</li><li>privat bruk av AI</li><li>tradisjonelle skytjenester og IT-drift</li><li>HPC, kryptovaluta og andre datasenterformål</li><li>eventuell overkapasitet, redundans og reservekapasitet</li><li>hvor stor del av annonserte datasentre som faktisk blir bygget</li></ul></div></div></section>
      <aside class="scenario-readout" aria-labelledby="examples-title"><p class="eyebrow">Eksempelyrker</p><h2 id="examples-title">Hva driver AI-behovet?</h2><div id="estimate-output"></div></aside>
      <section class="settings-section" id="settings" aria-labelledby="settings-title">
        <div class="settings-heading"><div><p class="eyebrow">Scenario og referanse</p><h2 id="settings-title">Innstillinger</h2></div><button type="button" class="icon-button" id="reset-workforce" title="Tilbakestill antakelser" aria-label="Tilbakestill antakelser"><i data-lucide="rotate-ccw"></i></button></div>
        <div class="settings-quick-row">
          <label for="target-adoption">Adopsjon<select id="target-adoption"><option value="20">20 %</option><option value="50" selected>50 %</option><option value="80">80 %</option><option value="100">100 %</option></select></label>
          <label for="adoption-years">Tid til full adopsjon<select id="adoption-years"><option value="1" selected>1 år</option><option value="2">2 år</option><option value="3">3 år</option><option value="5">5 år</option></select></label>
          <label for="factor-level">Yrkesfaktor<select id="factor-level"><option value="low">Lav</option><option value="base" selected>Base</option><option value="high">Høy</option></select></label>
          <p class="assumption-note">Adopsjonen øker lineært fra 20 % til målet over valgt antall år, og holder seg deretter konstant. Utvikler = 1,0 i alle faktorprofiler.</p>
        </div>
        <div class="settings-grid">
        <section class="adoption-panel" aria-labelledby="factor-title">
          <div class="factor-intro"><p class="eyebrow">Scenarioantakelse</p><h3 id="factor-title">Yrkesfaktorer</h3></div>
          <div class="factor-control"><label for="factor-fallback">Uvurderte yrker</label><select id="factor-fallback"><option value="none">Ikke ekstrapolert (delestimat)</option><option value="fte-weighted-mean" selected>Årsverksvektet snitt av vurderte</option><option value="unweighted-mean">Enkelt snitt av vurderte</option></select><p>Ekstrapolering fyller bare manglende faktorer. Vurderte yrker beholder sin egen faktor.</p></div>
        </section>
        <section class="reference-band" id="reference" aria-labelledby="reference-title">
          <div class="reference-intro"><p class="eyebrow">Developer Reference</p><h3 id="reference-title">Referansetall</h3><p>Effekt per aktiv utvikler ved antatt AI-bruk, basert på valgt modell/infrastruktur og antatt samtidighet.</p><p>Referansetallet skaleres mot andre yrker via AI-intensitetsfaktor.</p></div>
          <div class="reference-controls"><label for="reference-method">Metode for referansetall</label><select id="reference-method" title="Erfaringsbasert beregning med 8 NVIDIA H100 og GLM-5.3-Flash" disabled><option selected>Erfaringsbasert · H100 + GLM-5.3</option></select><label for="annual-hours">Aktive timer per årsverk og år</label><input id="annual-hours" type="number" min="1" max="8760" step="1" value="1725"><p>Felles timegrunnlag for referanse og yrker. 1 725 timer er en scenarioantakelse, ikke målt av SSB.</p></div>
          <div class="calibration-output" id="calibration-output"></div>
          <div class="reference-method-details" aria-labelledby="reference-method-title">
            <div><p class="eyebrow">Valgt metode</p><h4 id="reference-method-title">Slik blir 220 W beregnet</h4><p>Baseline for GLM-5.3-Flash antar 8 NVIDIA H100, 65 % GPU-utnyttelse og 20 samtidige utviklere.</p></div>
            <ol class="reference-method-steps">
              <li><span>Per GPU</span><strong>100 W + (600 W − 100 W) × 65 % = 425 W</strong><small>Lineær effekt mellom antatt tomgang og belastning.</small></li>
              <li><span>Hele noden</span><strong>8 × 425 W + 1 000 W = 4 400 W</strong><small>Øvrig IT-effekt i servernoden legges til.</small></li>
              <li><span>Per utvikler</span><strong>4 400 W ÷ 20 = 220 W</strong><small>Nodeeffekten fordeles på samtidige aktive utviklere.</small></li>
            </ol>
            <p class="reference-method-caveat"><strong>Hva modellen bidrar med:</strong> Arbeidslasten er satt til 800 output-token/s samlet og 40 per strøm, tilsvarende 20 samtidige strømmer. Kapasiteten og kompatibiliteten for GLM-5.3-Flash på denne maskinvaren er ikke verifisert. Tallene er erfaringsbaserte scenarioantakelser, ikke målte produksjonsdata.</p>
          </div>
          <p class="worked-example">Eksempel: 100 000 årsverk × 0,5 AI-intensitet × 50 % adopsjon × 220 W ≈ 5,5 MW</p>
        </section>
        </div>
      </section>
      <section class="occupation-section" id="occupations" aria-labelledby="occupation-title">
        <div class="occupation-heading"><div><p class="eyebrow">Årsverk × yrkesfaktor × adopsjon</p><h2 id="occupation-title">Yrkenes bidrag</h2></div><button class="export-button" id="export-workforce" type="button"><i data-lucide="download"></i>Eksporter CSV</button></div>
        <div class="occupation-toolbar"><div class="search-control"><i data-lucide="search" aria-hidden="true"></i><input type="search" id="occupation-search" aria-label="Søk etter yrke eller kode" placeholder="Søk etter yrke eller kode"></div><label>Vis<select id="coverage-filter"><option value="assessed">Vurderte yrker (22)</option><option value="all">Alle yrker (407)</option><option value="missing">Mangler faktor (385)</option></select></label><label>Sorter<select id="occupation-sort"><option value="energy">Størst energibidrag</option><option value="fte">Flest årsverk</option><option value="code">Yrkeskode</option></select></label></div>
        <div class="table-wrap" tabindex="0" role="region" aria-label="Yrkesfordeling"><table class="occupation-data"><caption id="occupation-caption"></caption><thead><tr><th scope="col">STYRK-08 / yrke</th><th scope="col">Årsverk, proxy</th><th scope="col">AI-intensitet</th><th scope="col">Utviklerekv. årsverk</th><th scope="col">GWh / år</th><th scope="col">Andel av estimat</th></tr></thead><tbody id="occupation-rows"></tbody></table></div>
        <p class="table-note">Yrkesfaktorene er foreløpige scenarioantakelser uten faglig gjennomgang, ikke målte energiforhold eller andeler jobber som forsvinner. Ukjent er ikke null.</p>
      </section>
      <section class="sources-section" id="sources" aria-labelledby="sources-title"><p class="eyebrow">Metode og begrensninger</p><h2 id="sources-title">Sporbart, men foreløpig</h2><div class="sources-grid">
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
      `${filtered.length} yrker · ${format(targetAdoption)} % måladopsjon · ${labels[factorLevel].toLowerCase()} yrkesfaktorer · andel av beregnet scenario`
    root.querySelector('#occupation-rows')!.innerHTML = filtered.length ? filtered.map((row) => {
      const share = row.gwh === null || !result.gwh ? null : row.gwh / result.gwh * 100
      return `<tr><th scope="row"><span class="occupation-code">${row.code}</span>${escape(row.title)}${row.code === '2512' ? '<span class="reference-badge">Referanseyrke · AI-intensitet 1,0</span>' : ''}${row.rationale ? `<details><summary>Faktorbegrunnelse</summary><p>${escape(row.rationale)}</p></details>` : '<span class="unknown-label">Ikke vurdert</span>'}</th><td>${format(row.fte)}${row.fte === null ? '<small>Mangler kvartalsdata</small>' : ''}</td><td>${row.factor === null ? 'Ukjent' : `<span class="factor-number">${format(row.factor, 2)}</span><meter min="0" max="1" value="${row.factor}" aria-label="Relativ AI-intensitet for ${escape(row.title)}">${row.factor}</meter>${row.factorIsExtrapolated ? '<small>Ekstrapolert</small>' : ''}`}</td><td>${format(row.equivalents)}</td><td>${format(row.gwh, 3)}</td><td>${share === null ? (row.gwh === null ? 'Ukjent' : 'Ikke definert') : `<span>${format(share)} %</span><div class="contribution-track"><div style="width:${share}%"></div></div>`}</td></tr>`
    }).join('') : '<tr><td colspan="6">Ingen yrker samsvarer med søket.</td></tr>'
  }

  function update() {
    const result = calculate()
    const reference = getReference()
    const comparison = buildNationalComparison(occupations, currentAdoption, targetAdoption, factorLevel,
      { watts: reference.watts, annualHours }, factorFallback, undefined, adoptionRampYears)
    const first = comparison[0]
    const last = comparison.at(-1)!
    const share = aiShareOfCommitted(last)
    const isPartial = factorFallback === 'none'
    const fallbackDescription = factorFallback === 'fte-weighted-mean' ? 'årsverksvektet snitt' : 'enkelt snitt'
    root.querySelector('#scenario-status')!.textContent = isPartial ? 'Betinget scenario · delestimat for 22 yrker' : 'Betinget scenario · ekstrapolert til uvurderte yrker'
    root.querySelector('#headline-claim')!.innerHTML = `AI-behovet tilsvarer ca. <strong>${formatRounded(share)} %</strong> av forpliktet datasenterkapasitet i 2030 <small>(${formatPower(last.aiMw)} av ${formatRounded(last.committedTotalMw)} MW)</small>`
    root.querySelector('#headline-output')!.innerHTML = `<div class="headline-ai"><span title="Aktiv IT-last: effektbehovet til IT-utstyret i de aktive arbeidstimene, uten kjøling, tomgang eller PUE.">${isPartial ? 'Estimert AI-effektbehov · 22 vurderte yrker' : 'Estimert AI-effektbehov · ekstrapolert scenario'}</span><strong data-metric="mw">${formatPower(last.aiMw)}</strong><p>${formatPower(last.aiAnnualAverageMw)} årsgjennomsnitt · ${formatEnergy(last.aiTwh === null ? null : last.aiTwh * 1000)}</p></div><div><span>Datasenterkapasitet</span><dl><div><dt>Eksisterende</dt><dd>${formatRounded(first.existingMw)} MW</dd></div><div><dt>Forpliktet/under bygging</dt><dd>${formatRounded(last.committedTotalMw)} MW</dd></div><div><dt>Annonsert</dt><dd>${formatRounded(last.includingAnnouncedMw)} MW</dd></div></dl><p>${formatEnergy(last.committedTotalMw * 8760 / 1000)} ved kontinuerlig full last</p><p class="capacity-status">Scenarioverdier – ikke offisiell nasjonal prognose</p></div><div class="headline-ratio"><span>AI-behov vs. forpliktet kapasitet</span><strong>${formatRounded(share)} <small>%</small></strong><p>2030</p></div>`
    root.querySelector('#interpretation-output')!.innerHTML = isPartial ? `De 22 vurderte yrkene gir et estimert AI-effektbehov på <strong>${formatPower(last.aiMw)}</strong>. Dette er et delestimat for 30,5 % av kjente årsverk, ikke Norges totale AI-behov.` : `Når de 385 uvurderte yrkene får ${fallbackDescription} (${format(result.fallbackFactor, 3)}), blir det estimerte AI-effektbehovet <strong>${formatPower(last.aiMw)}</strong>, tilsvarende <strong>${formatRounded(share)} %</strong> av forpliktet kapasitet.`
    root.querySelector('#comparison-chart')!.innerHTML = comparisonChart(comparison)
    const exampleRows = [
      { label: 'Programvareutviklere', detail: 'Referanseyrke · AI-intensitet 1,0', row: result.rows.find((row) => row.code === '2512') },
      { label: 'Jurister og advokater', detail: 'Eksempel', row: result.rows.find((row) => row.code === '2611') },
      { label: 'Tømrere og snekkere', detail: 'Eksempel', row: result.rows.find((row) => row.code === '7115') },
    ]
    const extrapolated = result.rows.filter((row) => row.factorIsExtrapolated)
    const extrapolatedMw = extrapolated.length
      ? extrapolated.reduce((total, row) => total + (row.activeMw ?? 0), 0) : null
    const extrapolatedGwh = extrapolated.length
      ? extrapolated.reduce((total, row) => total + (row.gwh ?? 0), 0) : null
    const metricCells = (mw: number | null, gwh: number | null) =>
      `<td>${formatPower(mw)}</td><td>${formatEnergy(gwh)}</td>`
    const calculatedCodes = result.rows.filter((row) => row.equivalents !== null).length
    const knownFte = result.rows.reduce((total, row) => total + (row.fte ?? 0), 0)
    const assessedFte = result.rows.filter((row) => row.factors !== null).reduce((total, row) => total + (row.fte ?? 0), 0)
    const fteCoveragePercent = knownFte > 0 ? assessedFte / knownFte * 100 : null
    root.querySelector('#estimate-output')!.innerHTML = `<table class="scenario-examples"><thead><tr><th scope="col">Yrke</th><th scope="col">Årsverk</th><th scope="col">AI-intensitet</th><th scope="col">Estimert effekt</th><th scope="col">Energi</th></tr></thead><tbody>${exampleRows.map(({ label, detail, row }) => `<tr><th scope="row">${label}<small>${detail}</small></th><td>${format(row?.fte ?? null, 0)}</td><td>${row?.factor === null || row?.factor === undefined ? 'Ukjent' : format(row.factor, 2)}</td>${metricCells(row?.activeMw ?? null, row?.gwh ?? null)}</tr>`).join('')}<tr><th scope="row">Andre yrker<small>${extrapolated.length ? `${extrapolated.length} ekstrapolerte yrker` : 'Ikke ekstrapolert'}</small></th><td>–</td><td>–</td>${metricCells(extrapolatedMw, extrapolatedGwh)}</tr></tbody><tfoot><tr><th scope="row">Totalt<small>Alle beregnede yrker</small></th><td>–</td><td>–</td>${metricCells(result.activeMw, result.gwh)}</tr></tfoot></table><p class="scenario-examples-note">Totalen omfatter ${calculatedCodes} av ${occupations.length} yrkeskoder${fteCoveragePercent === null ? '' : ` (${format(fteCoveragePercent, 0)} % av kjente årsverk)`}. ${result.missingFteCodes} mangler årsverksgrunnlag.</p>`
    root.querySelector('#calibration-output')!.innerHTML = `<span>Referansearbeidslast</span><strong>${formatRounded(reference.watts)} <small>W</small></strong><p>${format(annualHours, 0)} aktive timer/år</p><p>${formatRounded(reference.watts)} W × ${format(annualHours, 0)} aktive timer = <strong>${formatRounded(result.annualKwhPerFte)} kWh</strong> per utviklerårsverk og år</p><span class="reference-status">Ingen PUE eller tomgang lagt til</span>`
    root.querySelector('#reference-evidence')!.innerHTML = `<p>${escape(reference.referenceId)} · ${escape(reference.traceId)}</p><p>${escape(reference.capacityReason ?? '')}</p>${reference.evidenceGaps.map((gap) => `<p>${escape(gap)}</p>`).join('')}`
    root.querySelector<HTMLSelectElement>('#target-adoption')!.value = String(targetAdoption)
    root.querySelector<HTMLSelectElement>('#adoption-years')!.value = String(adoptionRampYears)
    updateTable()
  }

  root.querySelector<HTMLSelectElement>('#target-adoption')!.addEventListener('change', (event) => {
    targetAdoption = Number((event.target as HTMLSelectElement).value)
    update()
  })
  root.querySelector<HTMLSelectElement>('#adoption-years')!.addEventListener('change', (event) => {
    adoptionRampYears = Number((event.target as HTMLSelectElement).value)
    update()
  })
  root.querySelector<HTMLSelectElement>('#factor-level')!.addEventListener('change', (event) => {
    factorLevel = (event.target as HTMLSelectElement).value as FactorLevel
    update()
  })
  root.querySelector<HTMLSelectElement>('#factor-fallback')!.addEventListener('change', (event) => {
    factorFallback = (event.target as HTMLSelectElement).value as FactorFallback
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
    currentAdoption = 20; targetAdoption = 50; adoptionRampYears = 1; factorLevel = 'base'; factorFallback = 'fte-weighted-mean'; annualHours = DEFAULT_ANNUAL_HOURS
    root.querySelector<HTMLSelectElement>('#factor-level')!.value = factorLevel
    root.querySelector<HTMLSelectElement>('#factor-fallback')!.value = factorFallback
    root.querySelector<HTMLSelectElement>('#target-adoption')!.value = String(targetAdoption)
    root.querySelector<HTMLSelectElement>('#adoption-years')!.value = String(adoptionRampYears)
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
    const reference = getReference()
    const csv = csvFormat(result.rows.map((row) => ({
      styrk08_code: row.code, occupation: row.title, annual_fte_proxy_2025: row.fte,
      factor_status: row.factors === null ? 'not_assessed' : 'assumption',
      factor_level: factorLevel, factor: row.factor, factor_is_extrapolated: row.factorIsExtrapolated,
      factor_fallback: result.factorFallback, fallback_factor: result.fallbackFactor,
      current_adoption_percent: currentAdoption,
      target_adoption_percent: targetAdoption,
      adoption_ramp_years: adoptionRampYears,
      developer_equivalent_fte: row.equivalents, annual_it_gwh: row.gwh,
      active_it_mw: row.activeMw, annual_average_it_mw: row.mw,
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