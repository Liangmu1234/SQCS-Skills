[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][ValidateNotNullOrEmpty()][string]$Target,
    [Parameter(Position = 1)][string]$Command = 'hostname; id -un; uname -r; uptime -p',
    [string]$User,
    [ValidateRange(0,65535)][int]$Port = 0,
    [string]$KeyPath,
    [string]$RegistryPath,
    [ValidateRange(1,120)][int]$ConnectTimeout = 10,
    [switch]$NoBootstrap,
    [switch]$NoReuse,
    [switch]$Json
)

$commandB64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Command))
$parameters=@{Target=$Target;CommandB64=$commandB64;ConnectTimeout=$ConnectTimeout}
if ($User) { $parameters.User=$User }
if ($Port -gt 0) { $parameters.Port=$Port }
if ($KeyPath) { $parameters.KeyPath=$KeyPath }
if ($RegistryPath) { $parameters.RegistryPath=$RegistryPath }
if ($NoBootstrap) { $parameters.NoBootstrap=$true }
if ($NoReuse) { $parameters.NoReuse=$true }
if ($Json) { $parameters.Json=$true }

& (Join-Path $PSScriptRoot 'sshctl.ps1') exec @parameters
