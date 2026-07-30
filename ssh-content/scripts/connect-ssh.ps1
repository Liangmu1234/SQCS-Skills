[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Target,

    [Parameter(Position = 1)]
    [string]$Command = 'hostname; id -un; uname -r; uptime -p',

    [string]$User,

    [ValidateRange(0, 65535)]
    [int]$Port = 0,

    [string]$KeyPath,

    [string]$RegistryPath,

    [ValidateRange(1, 120)]
    [int]$ConnectTimeout = 15
)

$ErrorActionPreference = 'Stop'

function Split-MarkdownRow {
    param([Parameter(Mandatory = $true)][string]$Line)

    return ,@(
        $Line.Trim().Trim('|').Split('|') |
            ForEach-Object { $_.Trim() }
    )
}

function Test-RegistryTarget {
    param(
        [AllowEmptyString()][string]$Value,
        [Parameter(Mandatory = $true)][string]$RequestedTarget
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }

    if ($Value.Equals($RequestedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    foreach ($token in ($Value -split '[,，;/；\s]+')) {
        if ($token.Equals($RequestedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Read-SshRegistry {
    param([Parameter(Mandatory = $true)][string]$Path)

    $servers = @()
    $credentials = @()
    $section = ''

    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^##\s+服务器列表\s*$') {
            $section = 'servers'
            continue
        }
        if ($line -match '^##\s+账号密码\s*$') {
            $section = 'credentials'
            continue
        }
        if ($line -match '^##\s+') {
            $section = ''
            continue
        }
        if ($line -notmatch '^\s*\|' -or $line -match '^\s*\|(?:\s*:?-+:?\s*\|)+\s*$') {
            continue
        }

        $cells = Split-MarkdownRow -Line $line
        if ($cells.Count -eq 0 -or $cells[0] -eq '#') {
            continue
        }

        if ($section -eq 'servers' -and $cells.Count -ge 5) {
            $servers += [pscustomobject]@{
                Alias = $cells[1]
                Host  = $cells[2]
                Port  = $cells[3]
                User  = $cells[4]
            }
        }
        elseif ($section -eq 'credentials' -and $cells.Count -ge 4) {
            $credentials += [pscustomobject]@{
                Host     = $cells[1]
                User     = $cells[2]
                Password = $cells[3]
            }
        }
    }

    return [pscustomobject]@{
        Servers     = $servers
        Credentials = $credentials
    }
}

if ([string]::IsNullOrWhiteSpace($RegistryPath)) {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_SSH_REGISTRY)) {
        $RegistryPath = $env:CODEX_SSH_REGISTRY
    }
    else {
        $RegistryPath = 'D:\文档\08-Obsidian\01-笔记\服务器登记.md'
    }
}

$password = $null
if (Test-Path -LiteralPath 'Env:CODEX_SSH_PASSWORD') {
    $password = (Get-Item -LiteralPath 'Env:CODEX_SSH_PASSWORD').Value
    Remove-Item -LiteralPath 'Env:CODEX_SSH_PASSWORD' -ErrorAction SilentlyContinue
}

$resolvedHost = $Target
$resolvedUser = $User
$resolvedPort = if ($Port -gt 0) { $Port } else { $null }

if (Test-Path -LiteralPath $RegistryPath -PathType Leaf) {
    $registry = Read-SshRegistry -Path $RegistryPath
    $serverMatches = @(
        $registry.Servers | Where-Object {
            (Test-RegistryTarget -Value $_.Host -RequestedTarget $Target) -or
            (Test-RegistryTarget -Value $_.Alias -RequestedTarget $Target)
        }
    )

    if ($serverMatches.Count -gt 1) {
        throw "Target '$Target' matches multiple registry entries. Use an exact IP or unique alias."
    }

    if ($serverMatches.Count -eq 1) {
        $server = $serverMatches[0]
        if (-not [string]::IsNullOrWhiteSpace($server.Host)) {
            $resolvedHost = $server.Host
        }
        if ([string]::IsNullOrWhiteSpace($resolvedUser) -and -not [string]::IsNullOrWhiteSpace($server.User)) {
            $resolvedUser = $server.User
        }
        if ($null -eq $resolvedPort -and -not [string]::IsNullOrWhiteSpace($server.Port)) {
            $parsedPort = 0
            if (-not [int]::TryParse($server.Port, [ref]$parsedPort) -or $parsedPort -lt 1 -or $parsedPort -gt 65535) {
                throw "The registered SSH port for '$Target' is invalid."
            }
            $resolvedPort = $parsedPort
        }
    }

    $credentialMatches = @(
        $registry.Credentials | Where-Object {
            $_.Host.Equals($resolvedHost, [System.StringComparison]::OrdinalIgnoreCase)
        }
    )

    if (-not [string]::IsNullOrWhiteSpace($resolvedUser)) {
        $credentialMatches = @(
            $credentialMatches | Where-Object {
                $_.User.Equals($resolvedUser, [System.StringComparison]::OrdinalIgnoreCase)
            }
        )
    }

    if ($credentialMatches.Count -gt 1 -and
        ([string]::IsNullOrWhiteSpace($resolvedUser) -or [string]::IsNullOrWhiteSpace($password))) {
        throw "Multiple credential entries match '$Target'. Specify -User."
    }

    if ($credentialMatches.Count -ge 1) {
        $credential = $credentialMatches[0]
        if ([string]::IsNullOrWhiteSpace($resolvedUser)) {
            $resolvedUser = $credential.User
        }
        if ([string]::IsNullOrWhiteSpace($password) -and -not [string]::IsNullOrWhiteSpace($credential.Password)) {
            $password = $credential.Password
        }
    }
}

if (-not [string]::IsNullOrWhiteSpace($KeyPath)) {
    $KeyPath = (Resolve-Path -LiteralPath $KeyPath -ErrorAction Stop).Path
    $password = $null
}

$sshCommand = Get-Command ssh.exe -CommandType Application -ErrorAction SilentlyContinue
if ($null -eq $sshCommand) {
    $sshCommand = Get-Command ssh -CommandType Application -ErrorAction Stop
}

$destination = if ([string]::IsNullOrWhiteSpace($resolvedUser)) {
    $resolvedHost
}
else {
    '{0}@{1}' -f $resolvedUser, $resolvedHost
}

$sshArguments = @(
    '-o', 'LogLevel=ERROR',
    '-o', "ConnectTimeout=$ConnectTimeout",
    '-o', 'ConnectionAttempts=1',
    '-o', 'StrictHostKeyChecking=accept-new'
)

if ($null -ne $resolvedPort) {
    $sshArguments += @('-p', [string]$resolvedPort)
}

if (-not [string]::IsNullOrWhiteSpace($KeyPath)) {
    $sshArguments += @('-i', $KeyPath, '-o', 'BatchMode=yes', '-o', 'PreferredAuthentications=publickey')
}
elseif ([string]::IsNullOrWhiteSpace($password)) {
    $sshArguments += @('-o', 'BatchMode=yes')
}
else {
    $sshArguments += @(
        '-o', 'NumberOfPasswordPrompts=1',
        '-o', 'PubkeyAuthentication=no',
        '-o', 'PreferredAuthentications=password,keyboard-interactive'
    )
}

$askpassPath = $null
$environmentNames = @('CODEX_SSH_ASKPASS_SECRET', 'SSH_ASKPASS', 'SSH_ASKPASS_REQUIRE', 'DISPLAY')
$savedEnvironment = @{}

foreach ($name in $environmentNames) {
    if (Test-Path -LiteralPath "Env:$name") {
        $savedEnvironment[$name] = [pscustomobject]@{ Exists = $true; Value = (Get-Item -LiteralPath "Env:$name").Value }
    }
    else {
        $savedEnvironment[$name] = [pscustomobject]@{ Exists = $false; Value = $null }
    }
}

$exitCode = 1
try {
    if (-not [string]::IsNullOrWhiteSpace($password)) {
        $askpassPath = Join-Path $env:TEMP ('codex-ssh-askpass-{0}.cmd' -f [guid]::NewGuid().ToString('N'))
        $askpassSource = "@echo off`r`npowershell.exe -NoProfile -NonInteractive -Command `"[Console]::Out.WriteLine(`$env:CODEX_SSH_ASKPASS_SECRET)`"`r`n"
        Set-Content -LiteralPath $askpassPath -Encoding ASCII -Value $askpassSource

        $env:CODEX_SSH_ASKPASS_SECRET = $password
        $env:SSH_ASKPASS = $askpassPath
        $env:SSH_ASKPASS_REQUIRE = 'force'
        $env:DISPLAY = 'codex'
    }

    $nativeErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $sshCommand.Source @sshArguments $destination $Command
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $nativeErrorPreference
}
finally {
    if ($null -ne $askpassPath) {
        Remove-Item -LiteralPath $askpassPath -Force -ErrorAction SilentlyContinue
    }

    foreach ($name in $environmentNames) {
        if ($savedEnvironment[$name].Exists) {
            Set-Item -LiteralPath "Env:$name" -Value $savedEnvironment[$name].Value
        }
        else {
            Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
        }
    }

    $password = $null
}

exit $exitCode
