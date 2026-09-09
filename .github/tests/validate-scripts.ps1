[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../NEIGHBOR-CIRCUIT-TOOLKIT'))
$workspaceRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$fixture=Join-Path $workspaceRoot '.development\script-fixture'
$prefix=$workspaceRoot.TrimEnd('\')+'\'
if (-not [IO.Path]::GetFullPath($fixture).StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) {throw 'Fixture escaped workspace'}
New-Item -ItemType Directory -Path (Join-Path $fixture '60_SCRIPTS\Inventory') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $fixture 'assets\js') -Force | Out-Null
Copy-Item -Path (Join-Path $root '60_SCRIPTS\Inventory\*.ps1') -Destination (Join-Path $fixture '60_SCRIPTS\Inventory') -Force
Copy-Item -LiteralPath (Join-Path $root 'assets\js\tools-data.js') -Destination (Join-Path $fixture 'assets\js\tools-data.js') -Force
Copy-Item -LiteralPath (Join-Path $root 'assets\download-manifest.json') -Destination (Join-Path $fixture 'assets\download-manifest.json') -Force
$results=New-Object 'Collections.Generic.List[string]'
function Assert-True($test,[string]$name) {if (-not $test) {throw "FAIL: $name"};$results.Add($name);Write-Host "PASS $name"}
function Fixture-File([string]$relative,[string]$content) {
 $path=Join-Path $fixture $relative
 New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($path)) -Force | Out-Null
 [IO.File]::WriteAllText($path,$content)
}
Fixture-File '20_PORTABLE_APPS\Misc\CrystalDiskInfo\Nested\DiskInfo64.exe' 'MOCK NON-EXECUTABLE TEST FILE'
Fixture-File '20_PORTABLE_APPS\Misc\HWiNFO\HWiNFO64.exe' ''
Fixture-File '00_BOOT\Windows\Win11_test_only.iso' 'MOCK NOT A BOOT IMAGE'
Fixture-File '10_WINDOWS_TOOLBOX\05_Startup-Processes\Sysinternals\procexp64.exe' 'MOCK NOT EXECUTABLE'
Fixture-File '10_WINDOWS_TOOLBOX\05_Startup-Processes\Sysinternals\SysinternalsSuite.zip' 'MOCK NOT AN ARCHIVE'
Fixture-File '30_DRIVERS\Microsoft-Surface\Surface_test_only.msi' 'MOCK NOT AN INSTALLER'
$scan=Join-Path $fixture '60_SCRIPTS\Inventory\Update-ToolkitInventory.ps1'
& $scan | Out-Null
function Read-Inventory { $text=[IO.File]::ReadAllText((Join-Path $fixture 'assets\js\local-inventory.js'));$m=[regex]::Match($text,'(?s)window.LOCAL_INVENTORY\s*=\s*(\{.*\})\s*;');return ($m.Groups[1].Value|ConvertFrom-Json) }
$inv=Read-Inventory
Assert-True $inv.tools.cdi.installed 'Recursively detects an expected extracted file'
Assert-True ($inv.tools.cdi.localPath -eq '20_PORTABLE_APPS/Misc/CrystalDiskInfo/Nested/DiskInfo64.exe') 'Stores a portable relative path'
Assert-True (-not $inv.tools.hwinfo.installed) 'Empty placeholder executable is not installed'
Assert-True $inv.tools.windows11.installed 'Wildcard ISO inventory'
Assert-True (-not $inv.tools.sysinternals.installed) 'Suite completeness requires all configured marker files'
Assert-True $inv.tools.surface.installed 'MSI driver package detection'
Assert-True (-not $inv.tools.sfc.installed) 'Host command not misreported as SSD file'
Assert-True ($inv.tools.cdi.version -eq '' -or $null -eq $inv.tools.cdi.version) 'Unknown executable version remains unknown without execution'
Fixture-File '10_WINDOWS_TOOLBOX\05_Startup-Processes\Sysinternals\Autoruns64.exe' 'MOCK NOT EXECUTABLE'
& $scan | Out-Null
$inv=Read-Inventory
Assert-True $inv.tools.sysinternals.installed 'Complete suite markers detected'
Assert-True ($inv.storage.folders.'90_TEMP' -eq 0) 'Empty or missing folders have zero measured bytes'
$before=(Get-FileHash -LiteralPath (Join-Path $fixture 'assets\js\local-inventory.js')).Hash
& $scan -WhatIf | Out-Null
$after=(Get-FileHash -LiteralPath (Join-Path $fixture 'assets\js\local-inventory.js')).Hash
Assert-True ($before -eq $after) 'Inventory WhatIf does not change output'
. (Join-Path $fixture '60_SCRIPTS\Inventory\Toolkit-Common.ps1')
$rejected=$false;try {Resolve-ToolkitPath '..\outside.txt'|Out-Null}catch{$rejected=$true}
Assert-True $rejected 'Rejects parent traversal'
$rejected=$false;try {Resolve-ToolkitPath 'C:\outside.txt'|Out-Null}catch{$rejected=$true}
Assert-True $rejected 'Rejects absolute paths'
$rejected=$false;try {Resolve-ToolkitPath '90_TEMP\file.txt:stream'|Out-Null}catch{$rejected=$true}
Assert-True $rejected 'Rejects alternate data stream paths'
& (Join-Path $fixture '60_SCRIPTS\Inventory\Download-MissingTools.ps1') -WhatIf | Out-Null
Assert-True (-not (Test-Path -LiteralPath (Join-Path $fixture '60_SCRIPTS\Inventory\download-log.jsonl'))) 'Download WhatIf does not download or log a completion'
$rejected=$false;try {& (Join-Path $fixture '60_SCRIPTS\Inventory\Download-MissingTools.ps1') -ToolId unknown -WhatIf | Out-Null}catch{$rejected=$true}
Assert-True $rejected 'Unreviewed download IDs fail closed'
& (Join-Path $fixture '60_SCRIPTS\Inventory\Update-ToolkitMetadata.ps1') -ToolId win11debloat -WhatIf | Out-Null
Assert-True (-not (Test-Path -LiteralPath (Join-Path $fixture 'assets\js\metadata.js'))) 'Metadata WhatIf does not write or contact sources'
foreach ($script in Get-ChildItem -LiteralPath (Join-Path $root '60_SCRIPTS') -Recurse -Filter '*.ps1') {
 $tokens=$null;$parseErrors=$null;[Management.Automation.Language.Parser]::ParseFile($script.FullName,[ref]$tokens,[ref]$parseErrors)|Out-Null
 Assert-True ($parseErrors.Count -eq 0) ('PowerShell syntax: '+$script.Name)
}
[IO.File]::WriteAllText((Join-Path $workspaceRoot '.development\script-results.json'),(ConvertTo-Json -InputObject @{testedAt=[DateTime]::UtcNow.ToString('o');powershell=$PSVersionTable.PSVersion.ToString();passed=$results.Count;checks=$results.ToArray()} -Depth 5))
Write-Host "$($results.Count) script checks passed. Mock fixture retained under validation/script-fixture; never copy it to your SSD."
