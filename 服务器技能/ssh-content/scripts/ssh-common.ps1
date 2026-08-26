Set-StrictMode -Version 2.0

function Get-SshContentStateRoot {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        return Join-Path $env:CODEX_HOME 'state\ssh-content'
    }
    return Join-Path $HOME '.codex\state\ssh-content'
}

function Initialize-SshContentState {
    $root = Get-SshContentStateRoot
    foreach ($path in @($root, (Join-Path $root 'sessions'), (Join-Path $root 'locks'))) {
        if (-not (Test-Path -LiteralPath $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
    $targets = Join-Path $root 'targets.json'
    $capabilities = Join-Path $root 'capabilities.json'
    if (-not (Test-Path -LiteralPath $targets)) { '[]' | Set-Content -LiteralPath $targets -Encoding UTF8 }
    if (-not (Test-Path -LiteralPath $capabilities)) { '{}' | Set-Content -LiteralPath $capabilities -Encoding UTF8 }
    return $root
}

function Get-ShortHash {
    param([Parameter(Mandatory = $true)][string]$Text, [int]$Length = 16)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
        $hash = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
        return $hash.Substring(0, [Math]::Min($Length, $hash.Length))
    }
    finally { $sha.Dispose() }
}

function Get-FileSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    $stream=[IO.File]::OpenRead($Path)
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return (($sha.ComputeHash($stream) | ForEach-Object { $_.ToString('x2') }) -join '') }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function ConvertTo-NativeArgument {
    param([AllowEmptyString()][string]$Value)
    if ($null -eq $Value -or $Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    $builder = New-Object Text.StringBuilder
    [void]$builder.Append('"')
    $slashes = 0
    foreach ($char in $Value.ToCharArray()) {
        if ($char -eq '\') { $slashes++; continue }
        if ($char -eq '"') {
            [void]$builder.Append(('\' * ($slashes * 2 + 1)))
            [void]$builder.Append('"')
            $slashes = 0
            continue
        }
        if ($slashes -gt 0) { [void]$builder.Append(('\' * $slashes)); $slashes = 0 }
        [void]$builder.Append($char)
    }
    if ($slashes -gt 0) { [void]$builder.Append(('\' * ($slashes * 2))) }
    [void]$builder.Append('"')
    return $builder.ToString()
}

function Invoke-NativeCaptured {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [AllowNull()][string]$InputText = $null,
        [hashtable]$Environment = @{}
    )
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = (($Arguments | ForEach-Object { ConvertTo-NativeArgument ([string]$_) }) -join ' ')
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
    $psi.StandardErrorEncoding = New-Object Text.UTF8Encoding($false)
    foreach ($key in $Environment.Keys) { $psi.EnvironmentVariables[[string]$key] = [string]$Environment[$key] }
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    if (-not $process.Start()) { throw "Failed to start $FilePath" }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if ($null -ne $InputText) { $process.StandardInput.Write($InputText) }
    $process.StandardInput.Close()
    $process.WaitForExit()
    $stdout = $stdoutTask.Result
    $stderr = $stderrTask.Result
    $code = $process.ExitCode
    $process.Dispose()
    return [pscustomobject]@{ ExitCode = $code; StdOut = $stdout; StdErr = $stderr }
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path, $Default)
    if (-not (Test-Path -LiteralPath $Path)) { return $Default }
    try {
        $raw = Get-Content -Raw -LiteralPath $Path -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) { return $Default }
        return $raw | ConvertFrom-Json
    }
    catch { return $Default }
}

function Write-JsonAtomic {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)]$Value)
    $lockName = 'Local\CodexSshContent_' + (Get-ShortHash $Path 24)
    $mutex = New-Object Threading.Mutex($false, $lockName)
    $acquired = $false
    try {
        $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds(15))
        if (-not $acquired) { throw "Timed out waiting for state lock: $Path" }
        $temp = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
        $json = ConvertTo-Json -InputObject $Value -Depth 8
        [IO.File]::WriteAllText($temp, $json, (New-Object Text.UTF8Encoding($false)))
        Move-Item -LiteralPath $temp -Destination $Path -Force
    }
    finally {
        if ($acquired) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}

function Get-SshExecutable {
    param([Parameter(Mandatory = $true)][string]$Name)
    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $command) { throw "LOCAL_TOOL_MISSING: $Name" }
    return $command.Source
}

function Get-SshErrorCategory {
    param([string]$Text, [int]$ExitCode)
    if ($Text -match 'REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed') { return 'HOST_KEY_CHANGED' }
    if ($Text -match 'Permission denied.*password|Permission denied.*keyboard-interactive') { return 'PASSWORD_AUTH_FAILED' }
    if ($Text -match 'Permission denied.*publickey') { return 'PUBLIC_KEY_AUTH_FAILED' }
    if ($Text -match 'Connection timed out|Operation timed out|No route to host') { return 'TCP_TIMEOUT' }
    if ($Text -match 'Connection refused') { return 'CONNECTION_REFUSED' }
    if ($Text -match 'Could not resolve hostname|Name or service not known') { return 'TARGET_NOT_FOUND' }
    if ($ExitCode -ne 0) { return 'REMOTE_COMMAND_FAILED' }
    return $null
}

function Get-TcpFailureCategory {
    param([string]$HostName,[int]$Port,[int]$TimeoutMilliseconds=2000)
    $client=New-Object Net.Sockets.TcpClient
    try {
        $async=$client.BeginConnect($HostName,$Port,$null,$null)
        if(-not $async.AsyncWaitHandle.WaitOne($TimeoutMilliseconds)){return 'TCP_TIMEOUT'}
        try{$client.EndConnect($async);return $null}
        catch [Net.Sockets.SocketException]{
            if($_.Exception.SocketErrorCode -eq [Net.Sockets.SocketError]::ConnectionRefused){return 'CONNECTION_REFUSED'}
            return 'TCP_TIMEOUT'
        }
    }
    catch{return 'TCP_TIMEOUT'}
    finally{$client.Dispose()}
}

function Write-SshResult {
    param(
        [bool]$Ok, [string]$Stage, [string]$ErrorName, [string]$Target,
        [int]$ExitCode, [string]$Message, [string]$StdOut, [string]$StdErr, [switch]$Json
    )
    $result = [ordered]@{
        ok = $Ok; stage = $Stage; error = $ErrorName; target = $Target
        exit_code = $ExitCode; message = $Message; stdout = $StdOut; stderr = $StdErr
    }
    if ($Json) { [Console]::Out.WriteLine(($result | ConvertTo-Json -Depth 5 -Compress)) }
    else {
        if (-not [string]::IsNullOrEmpty($StdOut)) { [Console]::Out.Write($StdOut) }
        if (-not [string]::IsNullOrEmpty($StdErr)) { [Console]::Error.Write($StdErr) }
        if (-not $Ok -and -not [string]::IsNullOrWhiteSpace($Message)) { [Console]::Error.WriteLine("[$Stage/$ErrorName] $Message") }
    }
    return [pscustomobject]$result
}
