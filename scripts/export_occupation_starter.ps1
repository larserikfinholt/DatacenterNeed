$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Split-Path $PSScriptRoot -Parent
$sourcePath = Join-Path $root 'data/sources/ssb/occupation-workforce-2025'
$workforce = Get-Content (Join-Path $sourcePath 'workforce.json') -Raw | ConvertFrom-Json
$factors = @(Import-Csv (Join-Path $root 'data/norway/occupation-factors-v0.csv'))
$culture = [System.Globalization.CultureInfo]::InvariantCulture

if (($workforce.id -join ',') -ne 'Kjonn,Alder,Yrke,ContentsCode,Tid' -or
    ($workforce.size -join ',') -ne '1,1,583,2,4' -or
    $workforce.value.Count -ne 4664) {
    throw 'Unexpected snapshot dimensions; review the source before exporting.'
}

$factorByCode = @{}
foreach ($factor in $factors) {
    $code = $factor.styrk08_code
    if ($factorByCode.ContainsKey($code) -or $code -notmatch '^\d{4}$' -or
        $null -eq $workforce.dimension.Yrke.category.index.PSObject.Properties[$code]) {
        throw "Duplicate or unknown occupation code: $code"
    }
    $low = [double]::Parse($factor.occupation_factor_low, $culture)
    $base = [double]::Parse($factor.occupation_factor_base, $culture)
    $high = [double]::Parse($factor.occupation_factor_high, $culture)
    if (-not ($low -ge 0 -and $low -le $base -and $base -le $high -and $high -le 1) -or
        $factor.factor_status -ne 'assumption') {
        throw "Invalid assumption factors: $code"
    }
    if ($code -eq '2512' -and ($low -ne 1 -or $base -ne 1 -or $high -ne 1)) {
        throw 'Developer reference must equal one in every factor scenario.'
    }
    $factorByCode[$code] = $factor
}
if (-not $factorByCode.ContainsKey('2512')) { throw 'Missing developer reference.' }

function Get-Observation([string]$Code, [string]$Metric, [string]$Period) {
    $occupationIndex = $workforce.dimension.Yrke.category.index.$Code
    $metricIndex = $workforce.dimension.ContentsCode.category.index.$Metric
    $periodIndex = $workforce.dimension.Tid.category.index.$Period
    $offset = ($occupationIndex * 2 + $metricIndex) * 4 + $periodIndex
    return $workforce.value[$offset]
}

$records = @(
    foreach ($code in ($workforce.dimension.Yrke.category.index.PSObject.Properties.Name |
        Where-Object { $_ -match '^\d{4}$' } | Sort-Object)) {
        $quarterValues = @(
            foreach ($period in '2025K1', '2025K2', '2025K3', '2025K4') {
                Get-Observation $code 'HeltidsEkvMnd' $period
            }
        )
        $complete = @($quarterValues | Where-Object { $null -ne $_ }).Count -eq 4
        $annualProxy = if ($complete) {
            (($quarterValues | Measure-Object -Average).Average).ToString('0.##', $culture)
        } else { $null }
        $factor = $factorByCode[$code]
        [pscustomobject][ordered]@{
            styrk08_code = $code
            occupation_label_no = $workforce.dimension.Yrke.category.label.$code
            employees_2025q4 = Get-Observation $code 'Lonsstakere' '2025K4'
            fte_2025q1 = $quarterValues[0]
            fte_2025q2 = $quarterValues[1]
            fte_2025q3 = $quarterValues[2]
            fte_2025q4 = $quarterValues[3]
            annual_fte_proxy_2025 = $annualProxy
            annual_fte_status = if ($complete) { 'derived_quarterly_mean' } else { 'unknown' }
            workforce_source_id = 'ssb-11658-occupation-workforce-2025'
            occupation_factor_low = if ($factor) { $factor.occupation_factor_low } else { $null }
            occupation_factor_base = if ($factor) { $factor.occupation_factor_base } else { $null }
            occupation_factor_high = if ($factor) { $factor.occupation_factor_high } else { $null }
            factor_status = if ($factor) { $factor.factor_status } else { 'not_assessed' }
            factor_source_id = if ($factor) { $factor.factor_source_id } else { $null }
            potential_basis = if ($factor) { $factor.potential_basis } else { $null }
            rationale = if ($factor) { $factor.rationale } else { $null }
        }
    }
)
if ($records.Count -ne 407) { throw 'Unexpected number of detailed occupations.' }
$outputPath = Join-Path $root 'data/norway/occupation-workforce-factors-2025-v0.csv'
$records | Export-Csv $outputPath -NoTypeInformation -Encoding utf8
Write-Output "Exported $($records.Count) occupations with $($factors.Count) assumption profiles."