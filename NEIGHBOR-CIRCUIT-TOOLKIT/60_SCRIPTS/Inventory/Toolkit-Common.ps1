# Shared helpers. Compatible with Windows PowerShell 5.1 and PowerShell 7.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:ToolkitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Resolve-ToolkitPath {
    param([Parameter(Mandatory=$true)][string]$RelativePath)
    if ([IO.Path]::IsPathRooted($RelativePath) -or $RelativePath -match '(^|[\\/])\.\.([\\/]|$)' -or $RelativePath.Contains(':')) { throw "Unsafe toolkit-relative path: $RelativePath" }
    $full = [IO.Path]::GetFullPath((Join-Path $script:ToolkitRoot $RelativePath))
    $prefix = $script:ToolkitRoot.TrimEnd('\','/') + [IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw "Path escapes toolkit: $RelativePath" }
    # Reject junctions/symlinks at every existing component, including output parents.
    $part = $script:ToolkitRoot
    foreach ($segment in $RelativePath.Split(@('/','\'), [StringSplitOptions]::RemoveEmptyEntries)) {
        $part = Join-Path $part $segment
        if (Test-Path -LiteralPath $part) {
            if ((Get-Item -LiteralPath $part -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point is not allowed: $part" }
        }
    }
    return $full
}
function Get-ToolkitManifest {
    # tools-data.js uses an assignment followed by a JSON array. Parse JSON, never execute JavaScript.
    $raw = [IO.File]::ReadAllText((Resolve-ToolkitPath 'assets/js/tools-data.js'))
    $match = [regex]::Match($raw, '(?s)window\.TOOLKIT_DATA\s*=\s*(\[.*\])\s*;?\s*$')
    if (-not $match.Success) { throw 'tools-data.js must assign a JSON array to window.TOOLKIT_DATA.' }
    return @($match.Groups[1].Value | ConvertFrom-Json)
}
function Write-ToolkitJson {
    param([string]$RelativePath, $Value, [string]$Assignment = '')
    $path = Resolve-ToolkitPath $RelativePath
    $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))
    $json = ConvertTo-Json -InputObject $Value -Depth 30
    if ($Assignment) { $json = '// Generated maintenance data; do not execute downloaded software.' + "`r`nwindow.$Assignment = $json;`r`n" }
    $temp = $path + '.tmp'
    $null = Resolve-ToolkitPath ($RelativePath + '.tmp')
    [IO.File]::WriteAllText($temp, $json, (New-Object Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $temp -Destination $path -Force
}
function Get-SafeToolkitFiles {
    param([string]$Folder)
    $dir = Resolve-ToolkitPath $Folder
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) { return }
    $stack = New-Object 'Collections.Generic.Stack[string]'
    $stack.Push($dir)
    while ($stack.Count -gt 0) {
        foreach ($item in Get-ChildItem -LiteralPath $stack.Pop() -Force -ErrorAction Stop) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
            if ($item.PSIsContainer) { $stack.Push($item.FullName) }
            else { $item }
        }
    }
}
function Get-ToolkitRelativePath {
    param([string]$FullName)
    return $FullName.Substring($script:ToolkitRoot.Length + 1).Replace('\','/')
}
function Get-OptionalProperty {
    param($Object,[string]$Name,$Default=$null)
    if ($null -ne $Object -and $Object.PSObject.Properties.Name -contains $Name) { return $Object.$Name }
    return $Default
}
