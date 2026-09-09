<# Checks official pages and GitHub release metadata; no installers or boot images are downloaded. #>
[CmdletBinding(SupportsShouldProcess=$true)]
param([string[]]$ToolId, [int]$TimeoutSec=20)
. (Join-Path $PSScriptRoot 'Toolkit-Common.ps1')
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$manifest=Get-ToolkitManifest
if ($ToolId) {
    foreach ($id in $ToolId) { if ($id -notin $manifest.id) { throw "Unknown tool ID: $id" } }
    $manifest=@($manifest | Where-Object {$_.id -in $ToolId})
}
$result=@{}
$existing=Resolve-ToolkitPath 'assets/js/metadata.js'
if (Test-Path -LiteralPath $existing) {
    $m=[regex]::Match([IO.File]::ReadAllText($existing),'(?s)window\.TOOLKIT_METADATA\s*=\s*(\{.*\})\s*;?\s*$')
    if ($m.Success) { $old=$m.Groups[1].Value | ConvertFrom-Json; foreach ($p in $old.PSObject.Properties) {$result[$p.Name]=$p.Value} }
}
$pageCache=@{}
foreach ($tool in $manifest) {
    if ($tool.kind -in @('Built-in','Documentation','Script')) { continue }
    if (-not $PSCmdlet.ShouldProcess($tool.officialWebsite,"Check source for $($tool.name)")) { continue }
    $now=[DateTime]::UtcNow.ToString('o')
    $previous=$result[$tool.id]
    $entry=[ordered]@{latestVersion=(Get-OptionalProperty $previous 'latestVersion' $tool.latestVersion);lastChecked=(Get-OptionalProperty $previous 'lastChecked' $tool.lastChecked);sourceCheckedAt=$now;sourceStatus='unconfirmed';manualVersionCheck=$true;updateStatus='unknown';error=''}
    try {
        $uri=[uri]$tool.officialWebsite
        if ($uri.Scheme -ne 'https') { throw 'Only HTTPS official sources are supported.' }
        if (-not $pageCache.ContainsKey($tool.officialWebsite)) {
            try { $response=Invoke-WebRequest -Uri $uri -Method Head -UseBasicParsing -TimeoutSec $TimeoutSec; $pageCache[$tool.officialWebsite]=[string]$response.StatusCode }
            catch { $pageCache[$tool.officialWebsite]=$_.Exception.Message }
        }
        if ($pageCache[$tool.officialWebsite] -eq '200') {$entry.sourceStatus='Official page reachable'} else {$entry.error=$pageCache[$tool.officialWebsite]}
        $repo=Get-OptionalProperty $tool 'githubRepo'
        if ($repo) {
            if ($repo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { throw 'Invalid GitHub repository ID.' }
            $release=Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers @{'User-Agent'='NeighborCircuitToolkit-Metadata';'Accept'='application/vnd.github+json'} -TimeoutSec $TimeoutSec
            if ($release.tag_name -and -not $release.draft -and -not $release.prerelease) {
                $entry.latestVersion=$release.tag_name
                $entry.lastChecked=$now
                $entry.manualVersionCheck=$false
                $entry.sourceStatus='Official GitHub release checked'
            }
        }
        # A page-only success never invents a version or advances lastChecked.
    } catch { $entry.error=$_.Exception.Message }
    $result[$tool.id]=$entry
    Write-Host "$($tool.name): $($entry.sourceStatus); latest version: $($entry.latestVersion)"
}
if (-not $WhatIfPreference) { Write-ToolkitJson 'assets/js/metadata.js' $result 'TOOLKIT_METADATA'; Write-Host 'Metadata saved. Reload the dashboard; review manual checks and errors.' }
