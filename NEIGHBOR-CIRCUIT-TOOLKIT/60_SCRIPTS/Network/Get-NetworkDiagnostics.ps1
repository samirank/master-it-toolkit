[CmdletBinding()]
param()
# Read-only local configuration; no scan, credentials export, or network reset.
Get-NetAdapter | Format-Table Name,Status,LinkSpeed,InterfaceDescription
Get-NetIPConfiguration
Get-DnsClientServerAddress | Format-Table InterfaceAlias,AddressFamily,ServerAddresses
Write-Host 'Compare link, DHCP address, gateway and DNS. Review the local Networking reference for targeted tests.'
