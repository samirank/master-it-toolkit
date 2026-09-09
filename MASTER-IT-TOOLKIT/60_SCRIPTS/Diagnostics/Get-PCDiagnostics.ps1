<# Read-only system observations. Creates a report only at the specified output path. #>
[CmdletBinding(SupportsShouldProcess=$true)]
param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
if (Test-Path -LiteralPath $OutputPath) {throw 'Output already exists. Choose a new filename.'}
$report=[ordered]@{createdAt=[DateTime]::UtcNow.ToString('o')}
foreach ($class in @('Win32_ComputerSystem','Win32_BIOS','Win32_OperatingSystem','Win32_DiskDrive')) {
    try {
        $report[$class]=@(Get-CimInstance $class | Select-Object Manufacturer,Model,Caption,Version,BuildNumber,SerialNumber,Size,TotalPhysicalMemory)
    } catch {$report[$class]=@{error=$_.Exception.Message}}
}
try {$report.adapters=@(Get-NetAdapter | Select-Object Name,Status,LinkSpeed,InterfaceDescription)}catch{$report.adapters=@()}
Write-Host 'Report contains device identifiers. Do not store passwords or recovery keys with it.'
if ($PSCmdlet.ShouldProcess($OutputPath,'Write diagnostic report')) {
    $json=ConvertTo-Json -InputObject $report -Depth 8
    $stream=[IO.File]::Open([IO.Path]::GetFullPath($OutputPath),[IO.FileMode]::CreateNew)
    $writer=New-Object IO.StreamWriter($stream,(New-Object Text.UTF8Encoding($false)))
    try {$writer.Write($json)}finally{$writer.Dispose()}
}
