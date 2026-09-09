<# Optional elevated repair of the RUNNING Windows installation. No automatic restart. #>
[CmdletBinding(SupportsShouldProcess=$true,ConfirmImpact='High')]
param([switch]$Repair)
$ErrorActionPreference='Stop'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {throw 'Open an elevated PowerShell after reviewing this script.'}
Write-Host 'Targets the running Windows installation. Check disk health and backup first. For WinRE/offline images, use the reference guide instead.'
if ($env:SystemDrive -eq 'X:') {throw 'Refusing automatic /Online repair in a typical WinPE/WinRE environment.'}
if ($Repair) {
    Write-Host 'Plan: DISM /Online /Cleanup-Image /RestoreHealth, then sfc /scannow. DISM may need internet or a matched source.'
    if ($PSCmdlet.ShouldProcess('Running Windows','Repair component store then protected system files')) {
        & dism.exe /Online /Cleanup-Image /RestoreHealth
        if ($LASTEXITCODE -notin @(0,3010)) {throw "DISM failed ($LASTEXITCODE). Review the DISM log before continuing."}
        & sfc.exe /scannow
        Write-Host "SFC exit: $LASTEXITCODE. Review its output and CBS.log. Restart manually if requested."
    }
} else {
    if ($PSCmdlet.ShouldProcess('Running Windows','Check existing component-store health flag')) {& dism.exe /Online /Cleanup-Image /CheckHealth}
    Write-Host 'No repair requested. Use -Repair only after reviewing the plan and confirming backup.'
}
