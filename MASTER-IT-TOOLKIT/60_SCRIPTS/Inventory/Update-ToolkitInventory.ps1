<#
.SYNOPSIS
Scans predefined toolkit folders and records file presence without launching any tool.
.EXAMPLE
.\60_SCRIPTS\Inventory\Update-ToolkitInventory.ps1
#>
[CmdletBinding(SupportsShouldProcess=$true)]
param()
. (Join-Path $PSScriptRoot 'Toolkit-Common.ps1')
$manifest = Get-ToolkitManifest
$result = [ordered]@{}
$folderCache = @{}
$scanErrors = New-Object 'Collections.Generic.List[string]'
foreach ($tool in $manifest) {
    $record = [ordered]@{ installed=$false; localPath=''; files=@(); sizeBytes=0; lastModified=''; version=''; scanError='' }
    if ($tool.localFolder -and @($tool.inventoryPatterns).Count -gt 0) {
        try {
            if (-not $folderCache.ContainsKey($tool.localFolder)) { $folderCache[$tool.localFolder] = @(Get-SafeToolkitFiles $tool.localFolder) }
            $allFiles = $folderCache[$tool.localFolder]
            $matches = @($allFiles | Where-Object {
                $file = $_
                $matched = $false
                foreach ($pattern in $tool.inventoryPatterns) { if ($file.Name -like $pattern -and $file.Length -gt 0) { $matched=$true; break } }
                $matched
            } | Sort-Object FullName -Unique)
            $complete = $matches.Count -gt 0
            if ((Get-OptionalProperty $tool 'inventoryMatch') -eq 'all') {
                foreach ($pattern in $tool.inventoryPatterns) {
                    if (@($matches | Where-Object { $_.Name -like $pattern }).Count -eq 0) { $complete=$false }
                }
            }
            if ($matches.Count -gt 0) {
                # Deterministic selection; prefer exact configured executable over newest wildcard package.
                $selected = $matches | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
                if ($tool.localExecutable) {
                    $expected = Resolve-ToolkitPath $tool.localExecutable
                    $exact = $matches | Where-Object { $_.FullName -eq $expected } | Select-Object -First 1
                    if ($exact) { $selected=$exact }
                }
                $record.installed=$complete
                $record.localPath=Get-ToolkitRelativePath $selected.FullName
                $record.sizeBytes=($matches | Measure-Object Length -Sum).Sum
                $record.lastModified=$selected.LastWriteTimeUtc.ToString('o')
                $record.files=@($matches | ForEach-Object { [ordered]@{path=(Get-ToolkitRelativePath $_.FullName);sizeBytes=$_.Length;lastModified=$_.LastWriteTimeUtc.ToString('o')} })
                if ($selected.Extension -in @('.exe','.dll')) {
                    try { $record.version=[Diagnostics.FileVersionInfo]::GetVersionInfo($selected.FullName).ProductVersion } catch { $record.version='' }
                }
            }
        } catch { $record.scanError=$_.Exception.Message; $scanErrors.Add($tool.id + ': ' + $_.Exception.Message) }
    }
    $result[$tool.id]=$record
}
$sizes=[ordered]@{}
foreach ($folder in @('00_BOOT','10_WINDOWS_TOOLBOX','20_PORTABLE_APPS','30_DRIVERS','40_INSTALLERS','50_FIRMWARE','60_SCRIPTS','70_DOCUMENTATION','80_LICENSED_TOOLS','90_TEMP')) {
    try { $folderFiles=@(Get-SafeToolkitFiles $folder); $sum=0; if ($folderFiles.Count) { $sum=($folderFiles | Measure-Object Length -Sum).Sum }; $sizes[$folder]=[long]$sum }
    catch { $sizes[$folder]=$null; $scanErrors.Add($folder + ': ' + $_.Exception.Message) }
}
$volume=$null
try { $drive=New-Object IO.DriveInfo([IO.Path]::GetPathRoot($script:ToolkitRoot)); $volume=[ordered]@{totalBytes=$drive.TotalSize;freeBytes=$drive.AvailableFreeSpace} } catch {}
$inventory=[ordered]@{schemaVersion=1;generatedAt=[DateTime]::UtcNow.ToString('o');tools=$result;storage=[ordered]@{folders=$sizes;volume=$volume};errors=@($scanErrors.ToArray())}
$found=@($result.Values | Where-Object {$_.installed}).Count
Write-Host "Inventory: $found of $($manifest.Count) records have expected files. $($scanErrors.Count) scan errors."
if ($PSCmdlet.ShouldProcess('assets/js/local-inventory.js','Write inventory snapshot')) {
    Write-ToolkitJson 'assets/js/local-inventory.js' $inventory 'LOCAL_INVENTORY'
    Write-ToolkitJson 'assets/toolkit-manifest.json' $manifest
    Write-Host 'Saved. Reload index.html. Presence is not signature, license or compatibility verification.'
}
if ($scanErrors.Count) { Write-Warning ($scanErrors -join "`n") }
