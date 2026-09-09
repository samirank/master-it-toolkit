[CmdletBinding(SupportsShouldProcess=$true)]
param()
. (Join-Path $PSScriptRoot 'Toolkit-Common.ps1')
$manifest=Get-ToolkitManifest
if ($PSCmdlet.ShouldProcess('assets/toolkit-manifest.json','Export central catalog')) { Write-ToolkitJson 'assets/toolkit-manifest.json' $manifest }
