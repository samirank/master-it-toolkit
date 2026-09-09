<#
.SYNOPSIS
Preview and download an explicitly reviewed subset. Never launches or extracts packages.
.EXAMPLE
.\60_SCRIPTS\Inventory\Download-MissingTools.ps1 -WhatIf
.EXAMPLE
.\60_SCRIPTS\Inventory\Download-MissingTools.ps1 -ToolId sysinternals
#>
[CmdletBinding(SupportsShouldProcess=$true, ConfirmImpact='High')]
param([string[]]$ToolId, [switch]$Replace)
. (Join-Path $PSScriptRoot 'Toolkit-Common.ps1')
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$entries=@([IO.File]::ReadAllText((Resolve-ToolkitPath 'assets/download-manifest.json')) | ConvertFrom-Json)
if ($ToolId) {foreach ($id in $ToolId) {if ($id -notin $entries.id) {throw "No reviewed automatic download for '$id'. Use Missing Downloads in index.html."}}; $entries=@($entries | Where-Object {$_.id -in $ToolId})}
$plan=@()
foreach ($entry in $entries) {
    if ($entry.licenseRequired) {Write-Warning "Skipping licensed package $($entry.id). Obtain it from your vendor account.";continue}
    $uri=[uri]$entry.url
    if ($uri.Scheme -ne 'https' -or $uri.Host -notin $entry.allowedHosts) {throw "Unapproved HTTPS host for $($entry.id)"}
    if ($entry.checksumPublished -and $entry.sha256 -notmatch '^[A-Fa-f0-9]{64}$') {throw "Vendor checksum required for $($entry.id). Enter the reviewed SHA256 first."}
    if ($entry.sha256 -and $entry.sha256 -notmatch '^[A-Fa-f0-9]{64}$') {throw 'Malformed SHA256 in download manifest.'}
    $dest=Resolve-ToolkitPath $entry.destination
    if ((Test-Path -LiteralPath $dest) -and -not $Replace) {Write-Host "Skipping existing: $dest";continue}
    $plan+=@{entry=$entry;dest=$dest}
    Write-Host "`n$($entry.name)`nURL: $($entry.url)`nDestination: $dest`n$($entry.notes)"
}
if ($plan.Count -eq 0) {Write-Host 'Nothing to download.';return}
if ($WhatIfPreference) {foreach ($item in $plan) {$null=$PSCmdlet.ShouldProcess($item.dest,'Download only; never execute')};return}
# Explicit confirmation is required even if caller suppresses ShouldProcess confirmation.
if ((Read-Host "Type DOWNLOAD to download $($plan.Count) reviewed package(s)") -cne 'DOWNLOAD') {Write-Host 'Cancelled.';return}
Add-Type -AssemblyName System.Net.Http
$handler=New-Object Net.Http.HttpClientHandler
$handler.AllowAutoRedirect=$false
$client=New-Object Net.Http.HttpClient($handler)
$client.Timeout=[TimeSpan]::FromMinutes(30)
try {
    foreach ($item in $plan) {
        $entry=$item.entry;$dest=$item.dest
        if (-not $PSCmdlet.ShouldProcess($dest,'Download only; never execute')) {continue}
        $temp=Resolve-ToolkitPath ($entry.destination+'.partial')
        if (Test-Path -LiteralPath $temp) {throw "Partial download exists: $temp. Inspect and remove it manually before retrying."}
        $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dest))
        $response=$null
        try {
            $uri=[uri]$entry.url
            for ($hop=0;$hop -lt 6;$hop++) {
                if ($uri.Scheme -ne 'https' -or $uri.Host -notin $entry.allowedHosts) {throw 'Redirect left the reviewed official host allowlist.'}
                $response=$client.GetAsync($uri,[Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
                $code=[int]$response.StatusCode
                if ($code -ge 300 -and $code -lt 400) {
                    $next=$response.Headers.Location
                    if (-not $next) {throw 'Redirect did not specify a destination.'}
                    if (-not $next.IsAbsoluteUri) {$next=New-Object Uri($uri,$next)}
                    $uri=$next;$response.Dispose();$response=$null;continue
                }
                $null=$response.EnsureSuccessStatusCode();break
            }
            if ($null -eq $response) {throw 'Too many redirects.'}
            $contentType=$response.Content.Headers.ContentType
            if ($contentType -and $contentType.MediaType -match 'text/html') {throw 'Server returned HTML instead of a package.'}
            $stream=$response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
            $output=[IO.File]::Open($temp,[IO.FileMode]::CreateNew)
            try {$stream.CopyTo($output)} finally {$output.Dispose();$stream.Dispose()}
            if ((Get-Item -LiteralPath $temp).Length -eq 0) {throw 'Empty download.'}
            $hash=(Get-FileHash -LiteralPath $temp -Algorithm SHA256).Hash
            if ($entry.sha256 -and $hash -ne $entry.sha256) {throw 'SHA256 mismatch. Download retained as .partial for inspection; destination untouched.'}
            if ((Test-Path -LiteralPath $dest) -and -not $Replace) {throw 'Destination appeared during download; refusing overwrite.'}
            Move-Item -LiteralPath $temp -Destination $dest -Force:$Replace
            $log=[ordered]@{time=[DateTime]::UtcNow.ToString('o');id=$entry.id;url=$uri.AbsoluteUri;destination=$entry.destination;sha256=$hash;vendorHashVerified=[bool]$entry.sha256}
            $logPath=Resolve-ToolkitPath '60_SCRIPTS/Inventory/download-log.jsonl'
            [IO.File]::AppendAllText($logPath,($log|ConvertTo-Json -Compress)+"`r`n",(New-Object Text.UTF8Encoding($false)))
            Write-Host "Downloaded only. SHA256: $hash. Extract and inspect manually, then run inventory."
        } catch {Write-Warning "$($entry.id): $($_.Exception.Message)"} finally {if ($response) {$response.Dispose()}}
    }
} finally {$client.Dispose();$handler.Dispose()}
