param([Parameter(Mandatory=$true)][string]$Plan,[Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{64}$')][string]$PlanSha256)
$ErrorActionPreference = 'Stop'
foreach ($module in 'Management','Utility','Security') {
    Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.$module/Microsoft.PowerShell.$module.psd1") -ErrorAction Stop
}
$ToolkitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
function Assert-ToolkitPath([string]$Value) {
    $full = [IO.Path]::GetFullPath($Value)
    if (-not $full.StartsWith($ToolkitRoot.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Path must stay inside this toolkit.' }
    $item = Get-Item -LiteralPath $full -Force
    while ($item -and $item.FullName -ne $ToolkitRoot) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked paths are not supported.' }
        $item = if ($item.PSIsContainer) { $item.Parent } else { $item.Directory }
        if (-not $item) { break }
    }
    return $full
}
$Plan = Assert-ToolkitPath $Plan
if ($Plan -notlike '*\70_DOCUMENTATION\Service-Notes\Install-History\*.plan.json') { throw 'Invalid install plan location.' }
if ((Get-FileHash -LiteralPath $Plan -Algorithm SHA256).Hash -ne $PlanSha256) { throw 'Installation plan changed after approval.' }
$request = Get-Content -LiteralPath $Plan -Raw | ConvertFrom-Json
$resultPath = $Plan.Replace('.plan.json','.result.json')
$record = [ordered]@{tool=$request.tool;host=$env:COMPUTERNAME;started=(Get-Date).ToString('o');package=$request.package;sha256=$request.sha256;status='preparing';message='Preparing installation';restorePoint=$null;before=@();after=@();exitCode=$null}
function Save-Record { $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding UTF8 }
function Programs {
    @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*') |
        ForEach-Object { Get-ItemProperty $_ -ErrorAction SilentlyContinue } |
        Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher,PSChildName | Sort-Object DisplayName,DisplayVersion
}
try {
    Save-Record
    $package = Assert-ToolkitPath $request.package
    if ($request.host -ne $env:COMPUTERNAME) { throw 'This plan belongs to another computer.' }
    if ([IO.Path]::GetExtension($package) -notin '.exe','.msi') { throw 'Only application EXE/MSI installers are supported.' }
    if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $request.sha256) { throw 'Installer changed after review.' }
    $signature = Get-AuthenticodeSignature -LiteralPath $package
    if ($signature.Status -ne 'Valid' -and -not ($signature.Status -eq 'NotSigned' -and $request.acceptUnsigned -eq $true)) { throw 'Installer signature is invalid, or this unsigned file has not been explicitly approved after source review.' }
    $record.signatureStatus = [string]$signature.Status
    $record.unsignedSourceConfirmed = $request.acceptUnsigned -eq $true
    $record.publisher = [string]$signature.SignerCertificate.Subject
    $record.before = @(Programs)
    $description = 'Master IT Toolkit '+[IO.Path]::GetFileNameWithoutExtension($Plan)
    $existing = @(Get-ComputerRestorePoint -ErrorAction Stop)
    $latest = ($existing | Measure-Object SequenceNumber -Maximum).Maximum
    Write-Host 'Creating a recovery checkpoint before installation...'
    Checkpoint-Computer -Description $description -RestorePointType APPLICATION_INSTALL -ErrorAction Stop
    $checkpoint = Get-ComputerRestorePoint | Where-Object { $_.Description -eq $description -and $_.SequenceNumber -gt $latest } | Select-Object -Last 1
    if (-not $checkpoint) { throw 'A new restore point could not be verified. Installation was not started. Check System Protection and restore-point frequency limits.' }
    $record.restorePoint = @{sequence=$checkpoint.SequenceNumber;description=$checkpoint.Description;created=$checkpoint.CreationTime}
    $record.status = 'installer-running';$record.message = 'Recovery checkpoint verified; interactive installer running.';Save-Record
    if ((Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash -ne $request.sha256) { throw 'Installer changed before launch.' }
    if ([IO.Path]::GetExtension($package) -eq '.msi') {
        $msiLog = $Plan.Replace('.plan.json','.msi.log')
        $process = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" -ArgumentList "/i `"$package`" /norestart /L*v `"$msiLog`"" -PassThru -Wait
    } else { $process = Start-Process -FilePath $package -PassThru -Wait }
    $record.exitCode = $process.ExitCode
    $record.after = @(Programs)
    $record.status = if ($process.ExitCode -in 0,1641,3010) { 'review-required' } else { 'stopped' }
    $record.message = "Installer exited with code $($process.ExitCode). Verify the application; open installation history for the program lists and recovery checkpoint."
    $record.finished = (Get-Date).ToString('o');Save-Record
    Write-Host $record.message
} catch {
    $record.status='stopped';$record.message=$_.Exception.Message;$record.errorLocation=$_.ScriptStackTrace;$record.after=@(Programs);Save-Record
    Write-Host $record.message -ForegroundColor Red
    exit 1
}
