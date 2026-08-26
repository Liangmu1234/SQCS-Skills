[CmdletBinding()]
param(
    [Parameter(Position = 0)][ValidateSet('bootstrap','exec','check','upload','download','close')][string]$Action = 'exec',
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Target,
    [string]$User,
    [ValidateRange(0,65535)][int]$Port = 0,
    [string]$Alias,
    [string]$KeyPath,
    [ValidateRange(1,120)][int]$ConnectTimeout = 10,
    [string]$Command,
    [string]$CommandB64,
    [string]$ScriptPath,
    [string]$LocalPath,
    [string]$RemotePath,
    [string]$RegistryPath,
    [switch]$NoBootstrap,
    [switch]$NoReuse,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
[Console]::InputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = New-Object Text.UTF8Encoding($false)
$scriptCommandWasBound=$PSBoundParameters.ContainsKey('Command')
. (Join-Path $PSScriptRoot 'ssh-common.ps1')
$stateRoot = Initialize-SshContentState
$targetsPath = Join-Path $stateRoot 'targets.json'
$ssh = Get-SshExecutable 'ssh.exe'

function Get-TargetRecords {
    $value=Read-JsonFile $targetsPath @()
    if ($null -eq $value) { return @() }
    return @($value | Where-Object { $null -ne $_ })
}

function Get-LegacyRegistryEntry {
    param([string]$Path, [string]$Requested)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) { return $null }
    $section = ''
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^##\s+服务器列表\s*$') { $section='servers'; continue }
        if ($line -match '^##\s+') { $section=''; continue }
        if ($section -ne 'servers' -or $line -notmatch '^\s*\|') { continue }
        $cells=@($line.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() })
        if ($cells.Count -lt 5 -or $cells[0] -eq '#' -or $cells[0] -match '^-+$') { continue }
        $tokens=@($cells[1],$cells[2])
        if ($tokens -contains $Requested) {
            return [pscustomobject]@{ Alias=$cells[1]; Host=$cells[2]; Port=$cells[3]; User=$cells[4] }
        }
    }
    return $null
}

function Get-SshConfigValues {
    param([string]$Name)
    $result = Invoke-NativeCaptured $ssh @('-G',$Name)
    $values = @{}
    if ($result.ExitCode -eq 0) {
        foreach ($line in $result.StdOut -split "`r?`n") {
            if ($line -match '^(\S+)\s+(.+)$') {
                $key=$matches[1].ToLowerInvariant(); $value=$matches[2]
                if (-not $values.ContainsKey($key)) { $values[$key]=@() }
                $values[$key] += $value
            }
        }
    }
    return $values
}

function Resolve-SshTarget {
    $records=Get-TargetRecords
    $record=$records | Where-Object { $null -ne $_ -and ($_.alias -eq $Target -or $_.host -eq $Target) } | Select-Object -First 1
    if ($null -ne $record) {
        return [pscustomobject]@{
            Alias=[string]$record.alias; Host=[string]$record.host
            User=if ($User) {$User} else {[string]$record.user}
            Port=if ($Port -gt 0) {$Port} else {[int]$record.port}
            Identity=if ($KeyPath) {$KeyPath} else {[string]$record.identity_file}
            Shell=if ($record.remote_shell) {[string]$record.remote_shell} else {'bash'}
            Multiplexing=if ($null -ne $record.multiplexing) {[bool]$record.multiplexing} else {$true}
        }
    }
    $legacyPath = if ($RegistryPath) {$RegistryPath} elseif ($env:CODEX_SSH_REGISTRY) {$env:CODEX_SSH_REGISTRY} else {$null}
    $legacy=Get-LegacyRegistryEntry $legacyPath $Target
    $config=Get-SshConfigValues $Target
    $resolvedHost=if ($legacy) {$legacy.Host} elseif ($config.hostname) {$config.hostname[0]} else {$Target}
    $resolvedUser=if ($User) {$User} elseif ($legacy -and $legacy.User) {$legacy.User} elseif ($config.user) {$config.user[0]} else {$null}
    $resolvedPort=if ($Port -gt 0) {$Port} elseif ($legacy -and $legacy.Port -match '^\d+$') {[int]$legacy.Port} elseif ($config.port) {[int]$config.port[0]} else {22}
    $identity=$KeyPath
    if (-not $identity -and $config.identityfile) {
        foreach ($candidate in $config.identityfile) {
            $expanded=$candidate.Replace('~',$HOME)
            if (Test-Path -LiteralPath $expanded) { $identity=$expanded; break }
        }
    }
    return [pscustomobject]@{ Alias=if($Alias){$Alias}else{$Target}; Host=$resolvedHost; User=$resolvedUser; Port=$resolvedPort; Identity=$identity; Shell='bash'; Multiplexing=$true }
}

function Save-SshTarget {
    param($Info, [string]$Identity, [string]$RemoteShell, [bool]$Multiplexing)
    $records=@(Get-TargetRecords | Where-Object { $null -ne $_ -and $_.alias -ne $Info.Alias -and $_.host -ne $Info.Host })
    $records += [pscustomobject]@{
        alias=$Info.Alias; host=$Info.Host; port=$Info.Port; user=$Info.User
        identity_file=$Identity; remote_shell=$RemoteShell
        last_success=(Get-Date).ToUniversalTime().ToString('o')
        multiplexing=$Multiplexing
    }
    Write-JsonAtomic $targetsPath $records
}

function Get-DedicatedKeyPath {
    $sshDir=Join-Path $HOME '.ssh'
    if (-not (Test-Path -LiteralPath $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }
    return Join-Path $sshDir 'codex_ssh_content_ed25519'
}

function Ensure-DedicatedKey {
    $path=Get-DedicatedKeyPath
    if (-not (Test-Path -LiteralPath $path) -or -not (Test-Path -LiteralPath "$path.pub")) {
        $keygen=Get-SshExecutable 'ssh-keygen.exe'
        $comment="codex-ssh-content@$env:COMPUTERNAME"
        $result=Invoke-NativeCaptured $keygen @('-q','-t','ed25519','-N','','-C',$comment,'-f',$path)
        if ($result.ExitCode -ne 0) { throw "PUBLIC_KEY_MISSING: $($result.StdErr)" }
    }
    return $path
}

function Get-ControlPath {
    param($Info)
    $hash=Get-ShortHash "$($Info.User)@$($Info.Host):$($Info.Port)" 20
    return ((Join-Path (Join-Path $stateRoot 'sessions') "cm-$hash") -replace '\\','/')
}

function Get-ConnectionArguments {
    param($Info, [string]$Identity, [switch]$PasswordMode, [switch]$DisableReuse)
    $args=@('-o','LogLevel=ERROR','-o',"ConnectTimeout=$ConnectTimeout",'-o','ConnectionAttempts=3','-o','StrictHostKeyChecking=accept-new','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3')
    if ($Info.Port -gt 0) { $args += @('-p',[string]$Info.Port) }
    if ($PasswordMode) {
        $args += @('-o','NumberOfPasswordPrompts=1','-o','PubkeyAuthentication=no','-o','PreferredAuthentications=password,keyboard-interactive')
    }
    else {
        $args += @('-o','BatchMode=yes','-o','PreferredAuthentications=publickey')
        if ($Identity) { $args += @('-i',$Identity,'-o','IdentitiesOnly=yes') }
        if (-not $DisableReuse -and $Info.Multiplexing) {
            $args += @('-o','ControlMaster=auto','-o','ControlPersist=600','-o',"ControlPath=$(Get-ControlPath $Info)")
        }
    }
    return $args
}

function Get-Destination { param($Info); if ($Info.User) { return "$($Info.User)@$($Info.Host)" }; return $Info.Host }

function Invoke-SshScript {
    param($Info, [string]$Identity, [string]$Script, [string]$Shell='bash', [string]$Password, [switch]$DisableReuse)
    $passwordMode=-not [string]::IsNullOrWhiteSpace($Password)
    $args=Get-ConnectionArguments $Info $Identity -PasswordMode:$passwordMode -DisableReuse:$DisableReuse
    $destination=Get-Destination $Info
    $args += @($destination, $Shell, '-s', '--')
    $environment=@{}
    $askpass=$null
    try {
        if ($passwordMode) {
            $askpass=Join-Path $env:TEMP ("codex-ssh-askpass-$([guid]::NewGuid().ToString('N')).cmd")
            '@echo off' + "`r`n" + 'powershell.exe -NoProfile -NonInteractive -Command "[Console]::Out.WriteLine($env:CODEX_SSH_ASKPASS_SECRET)"' | Set-Content -LiteralPath $askpass -Encoding ASCII
            $environment=@{CODEX_SSH_ASKPASS_SECRET=$Password; SSH_ASKPASS=$askpass; SSH_ASKPASS_REQUIRE='force'; DISPLAY='codex'}
        }
        $result=Invoke-NativeCaptured $ssh $args $Script $environment
    }
    finally { if ($askpass) { Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue } }
    if (-not $passwordMode -and -not $DisableReuse -and $result.ExitCode -ne 0 -and $result.StdErr -match 'mux|ControlPath|control socket|getsockname|Not a socket') {
        $Info.Multiplexing=$false
        $result=Invoke-SshScript $Info $Identity $Script $Shell -DisableReuse
    }
    return $result
}

function Invoke-NativeWithPassword {
    param([string]$FilePath,[string[]]$Arguments,[string]$InputText,[string]$Password)
    if ([string]::IsNullOrWhiteSpace($Password)) { return Invoke-NativeCaptured $FilePath $Arguments $InputText }
    $askpass=Join-Path $env:TEMP ("codex-ssh-askpass-$([guid]::NewGuid().ToString('N')).cmd")
    try {
        '@echo off' + "`r`n" + 'powershell.exe -NoProfile -NonInteractive -Command "[Console]::Out.WriteLine($env:CODEX_SSH_ASKPASS_SECRET)"' | Set-Content -LiteralPath $askpass -Encoding ASCII
        $environment=@{CODEX_SSH_ASKPASS_SECRET=$Password;SSH_ASKPASS=$askpass;SSH_ASKPASS_REQUIRE='force';DISPLAY='codex'}
        return Invoke-NativeCaptured $FilePath $Arguments $InputText $environment
    }
    finally { Remove-Item -LiteralPath $askpass -Force -ErrorAction SilentlyContinue }
}

function Invoke-Bootstrap {
    param($Info)
    if (-not $Info.User) { throw 'CREDENTIAL_REQUIRED: User is required for first connection' }
    $identity=if ($KeyPath) {(Resolve-Path -LiteralPath $KeyPath).Path} else {Ensure-DedicatedKey}
    $password=$null
    if (Test-Path Env:CODEX_SSH_PASSWORD) {
        $password=(Get-Item Env:CODEX_SSH_PASSWORD).Value
        Remove-Item Env:CODEX_SSH_PASSWORD -ErrorAction SilentlyContinue
    }
    if ([string]::IsNullOrWhiteSpace($password)) {
        $probe=Invoke-SshScript $Info $identity "printf '__SSH_CONTENT_KEY_AUTH_OK__\n'`n" 'sh' -DisableReuse
        if ($probe.ExitCode -eq 0 -and $probe.StdOut -match '__SSH_CONTENT_KEY_AUTH_OK__') {
            Save-SshTarget $Info $identity 'bash' $true
            return [pscustomobject]@{Info=$Info; Identity=$identity; Result=$probe; AlreadyConfigured=$true}
        }
        if ($NoBootstrap) { throw 'PUBLIC_KEY_AUTH_FAILED: key authentication failed and bootstrap is disabled' }
        throw 'CREDENTIAL_REQUIRED: set CODEX_SSH_PASSWORD for first connection'
    }
    if ($NoBootstrap) { throw 'PUBLIC_KEY_AUTH_FAILED: bootstrap is disabled' }
    try {
        $publicKey=[IO.File]::ReadAllText("$identity.pub",[Text.Encoding]::UTF8).Trim()
        $keyB64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($publicKey))
        $install=@"
set -eu
umask 077
mkdir -p "`$HOME/.ssh"
chmod 700 "`$HOME/.ssh"
key=`$(printf '%s' '$keyB64' | base64 -d)
touch "`$HOME/.ssh/authorized_keys"
grep -qxF "`$key" "`$HOME/.ssh/authorized_keys" || printf '%s\n' "`$key" >> "`$HOME/.ssh/authorized_keys"
chmod 600 "`$HOME/.ssh/authorized_keys"
printf '__SSH_CONTENT_KEY_INSTALLED__\n'
"@
        $installed=Invoke-SshScript $Info $null $install 'sh' $password -DisableReuse
    }
    finally { $password=$null }
    if ($installed.ExitCode -ne 0 -or $installed.StdOut -notmatch '__SSH_CONTENT_KEY_INSTALLED__') {
        $category=Get-SshErrorCategory ($installed.StdErr+$installed.StdOut) $installed.ExitCode
        throw "PUBLIC_KEY_INSTALL_FAILED: $category $($installed.StdErr)"
    }
    $verified=Invoke-SshScript $Info $identity "printf '__SSH_CONTENT_KEY_AUTH_OK__\n'`n" 'sh' -DisableReuse
    if ($verified.ExitCode -ne 0 -or $verified.StdOut -notmatch '__SSH_CONTENT_KEY_AUTH_OK__') { throw "KEY_AUTH_VERIFY_FAILED: $($verified.StdErr)" }
    $shellProbe=Invoke-SshScript $Info $identity "if command -v bash >/dev/null 2>&1; then printf bash; else printf sh; fi`n" 'sh' -DisableReuse
    $remoteShell=if ($shellProbe.StdOut.Trim() -eq 'bash') {'bash'} else {'sh'}
    $Info.Alias=if ($Alias) {$Alias} else {$Info.Alias}
    Save-SshTarget $Info $identity $remoteShell $true
    return [pscustomobject]@{Info=$Info; Identity=$identity; Result=$verified; AlreadyConfigured=$false}
}

function Ensure-AuthenticatedTarget {
    $info=Resolve-SshTarget
    if ($Alias) { $info.Alias=$Alias }
    $identity=$info.Identity
    if ($identity -and (Test-Path -LiteralPath $identity)) { return [pscustomobject]@{Info=$info; Identity=$identity; Password=$null} }
    if($NoBootstrap){
        $oneTimePassword=$null
        if(Test-Path Env:CODEX_SSH_PASSWORD){$oneTimePassword=(Get-Item Env:CODEX_SSH_PASSWORD).Value;Remove-Item Env:CODEX_SSH_PASSWORD -ErrorAction SilentlyContinue}
        if([string]::IsNullOrWhiteSpace($oneTimePassword)){throw 'CREDENTIAL_REQUIRED: no usable key or process-scoped password'}
        return [pscustomobject]@{Info=$info;Identity=$null;Password=$oneTimePassword}
    }
    if(Test-Path Env:CODEX_SSH_PASSWORD){
        $boot=Invoke-Bootstrap $info
        return [pscustomobject]@{Info=$boot.Info;Identity=$boot.Identity;Password=$null}
    }
    $agentProbe=Invoke-SshScript $info $null "printf '__SSH_CONTENT_AGENT_OK__\n'`n" 'sh' -DisableReuse
    if($agentProbe.ExitCode -eq 0 -and $agentProbe.StdOut -match '__SSH_CONTENT_AGENT_OK__'){
        return [pscustomobject]@{Info=$info;Identity=$null;Password=$null}
    }
    $boot=Invoke-Bootstrap $info
    return [pscustomobject]@{Info=$boot.Info; Identity=$boot.Identity; Password=$null}
}

function Get-RequestedScript {
    if ($scriptCommandWasBound -or $ScriptPath) {
        throw 'BASE64_COMMAND_REQUIRED: exec accepts only -CommandB64; encode the complete UTF-8 script locally'
    }
    if ([string]::IsNullOrWhiteSpace($CommandB64)) {
        throw 'BASE64_COMMAND_REQUIRED: exec requires -CommandB64'
    }
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($CommandB64))
}

function Quote-Sh {
    param([string]$Value)
    $quote = [string][char]39
    $replacement = $quote + '"' + $quote + '"' + $quote
    return $quote + $Value.Replace($quote, $replacement) + $quote
}

try {
    if ($Action -eq 'bootstrap') {
        $info=Resolve-SshTarget; if ($Alias){$info.Alias=$Alias}
        $boot=Invoke-Bootstrap $info
        $msg=if($boot.AlreadyConfigured){'Key authentication already configured'}else{'Password bootstrap completed; key authentication verified'}
        $null=Write-SshResult $true 'bootstrap' $null $boot.Info.Alias 0 $msg $boot.Result.StdOut $boot.Result.StdErr -Json:$Json
        exit 0
    }
    $auth=Ensure-AuthenticatedTarget; $info=$auth.Info; $identity=$auth.Identity; $operationPassword=$auth.Password
    if ($Action -eq 'exec' -or $Action -eq 'check') {
        $script=if($Action -eq 'check'){"printf '__SSH_CONTENT_OK__\n'`nhostname`nid -un`n"}else{Get-RequestedScript}
        $result=Invoke-SshScript $info $identity $script $info.Shell $operationPassword -DisableReuse:$NoReuse
        if ($result.ExitCode -eq 127 -and $info.Shell -eq 'bash') { $info.Shell='sh'; $result=Invoke-SshScript $info $identity $script 'sh' $operationPassword -DisableReuse:$NoReuse }
        if ($result.ExitCode -eq 0 -and -not $operationPassword) { Save-SshTarget $info $identity $info.Shell $info.Multiplexing }
        $errorName=Get-SshErrorCategory ($result.StdErr+$result.StdOut) $result.ExitCode
        if($result.ExitCode -eq 255 -and $errorName -eq 'REMOTE_COMMAND_FAILED' -and [string]::IsNullOrWhiteSpace($result.StdErr+$result.StdOut)){
            $errorName=Get-TcpFailureCategory $info.Host $info.Port
            if(-not $errorName){$errorName='PUBLIC_KEY_AUTH_FAILED'}
        }
        $null=Write-SshResult ($result.ExitCode -eq 0) $Action $errorName $info.Alias $result.ExitCode '' $result.StdOut $result.StdErr -Json:$Json
        exit $result.ExitCode
    }
    if ($Action -eq 'close') {
        if(-not $info.Multiplexing){
            $null=Write-SshResult $true 'close' $null $info.Alias 0 'Connection reuse is disabled for this OpenSSH client' '' '' -Json:$Json
            exit 0
        }
        $args=Get-ConnectionArguments $info $identity -DisableReuse
        $args += @('-o',"ControlPath=$(Get-ControlPath $info)",'-O','exit',(Get-Destination $info))
        $result=Invoke-NativeCaptured $ssh $args
        $ok=($result.ExitCode -eq 0 -or $result.StdErr -match 'No such file|Control socket connect')
        $null=Write-SshResult $ok 'close' $(if($ok){$null}else{'SESSION_REUSE_FAILED'}) $info.Alias $(if($ok){0}else{$result.ExitCode}) '' $result.StdOut $result.StdErr -Json:$Json
        exit $(if($ok){0}else{$result.ExitCode})
    }
    if (-not $LocalPath -or -not $RemotePath) { throw 'LocalPath and RemotePath are required for upload/download' }
    $sftp=Get-SshExecutable 'sftp.exe'
    $scp=Get-SshExecutable 'scp.exe'
    $sftpArgs=@('-q','-o','StrictHostKeyChecking=accept-new','-o',"ConnectTimeout=$ConnectTimeout")
    if($operationPassword){$sftpArgs+=@('-o','NumberOfPasswordPrompts=1','-o','PubkeyAuthentication=no','-o','PreferredAuthentications=password,keyboard-interactive')}else{$sftpArgs+=@('-o','BatchMode=yes')}
    if ($info.Port -gt 0) { $sftpArgs += @('-P',[string]$info.Port) }
    if ($identity) { $sftpArgs += @('-i',$identity,'-o','IdentitiesOnly=yes') }
    if (-not $NoReuse -and $info.Multiplexing) { $sftpArgs += @('-o',"ControlPath=$(Get-ControlPath $info)") }
    $sftpDestination=Get-Destination $info
    $sftpArgs += @($sftpDestination)
    if ($Action -eq 'upload') {
        $resolved=(Resolve-Path -LiteralPath $LocalPath).Path
        $localItem=Get-Item -LiteralPath $resolved
        $remoteTemp="$RemotePath.codex-partial-$([guid]::NewGuid().ToString('N'))"
        $recursive=if($localItem.PSIsContainer){'-r '}else{''}
        $batch="put $recursive`"$($resolved -replace '\\','/')`" `"$remoteTemp`"`n"
        $transfer=Invoke-NativeWithPassword $sftp $sftpArgs $batch $operationPassword
        if ($transfer.ExitCode -ne 0) {
            $scpArgs=@('-q','-o','StrictHostKeyChecking=accept-new','-o',"ConnectTimeout=$ConnectTimeout")
            if($operationPassword){$scpArgs+=@('-o','NumberOfPasswordPrompts=1','-o','PubkeyAuthentication=no','-o','PreferredAuthentications=password,keyboard-interactive')}else{$scpArgs+=@('-o','BatchMode=yes')}
            if($localItem.PSIsContainer){$scpArgs+='-r'}; if($info.Port -gt 0){$scpArgs+=@('-P',[string]$info.Port)}; if($identity){$scpArgs+=@('-i',$identity,'-o','IdentitiesOnly=yes')}
            $scpArgs+=@($resolved,"$(Get-Destination $info):$remoteTemp")
            $transfer=Invoke-NativeWithPassword $scp $scpArgs $null $operationPassword
        }
        if ($transfer.ExitCode -eq 0) {
            $move="mv -- $(Quote-Sh $remoteTemp) $(Quote-Sh $RemotePath)`n"
            $moveResult=Invoke-SshScript $info $identity $move $info.Shell $operationPassword -DisableReuse:$NoReuse
            if ($moveResult.ExitCode -ne 0) { $transfer=$moveResult }
        }
        if ($transfer.ExitCode -eq 0 -and -not $localItem.PSIsContainer) {
            $localHash=Get-FileSha256 $resolved
            $hashResult=Invoke-SshScript $info $identity "sha256sum -- $(Quote-Sh $RemotePath) | awk '{print `$1}'`n" $info.Shell $operationPassword -DisableReuse:$NoReuse
            if ($hashResult.ExitCode -ne 0 -or $hashResult.StdOut.Trim().ToLowerInvariant() -ne $localHash) {
                $transfer=[pscustomobject]@{ExitCode=1;StdOut=$hashResult.StdOut;StdErr='SHA-256 mismatch after upload'}
            }
        }
        $name=if($transfer.ExitCode -eq 0){$null}elseif($transfer.StdErr -match 'SHA-256'){'CHECKSUM_MISMATCH'}else{'UPLOAD_FAILED'}
        $null=Write-SshResult ($transfer.ExitCode -eq 0) 'upload' $name $info.Alias $transfer.ExitCode '' $transfer.StdOut $transfer.StdErr -Json:$Json
        exit $transfer.ExitCode
    }
    $remoteHashResult=Invoke-SshScript $info $identity "if [ -f $(Quote-Sh $RemotePath) ]; then sha256sum -- $(Quote-Sh $RemotePath) | awk '{print `$1}'; fi`n" $info.Shell $operationPassword -DisableReuse:$NoReuse
    $expectedHash=$remoteHashResult.StdOut.Trim().ToLowerInvariant()
    $localFull=[IO.Path]::GetFullPath($LocalPath); $localTemp="$localFull.partial"
    $parent=Split-Path -Parent $localFull; if($parent -and -not(Test-Path $parent)){New-Item -ItemType Directory -Path $parent -Force|Out-Null}
    $batch="get -r `"$RemotePath`" `"$($localTemp -replace '\\','/')`"`n"
    $transfer=Invoke-NativeWithPassword $sftp $sftpArgs $batch $operationPassword
    if ($transfer.ExitCode -ne 0) {
        $scpArgs=@('-q','-r','-o','StrictHostKeyChecking=accept-new','-o',"ConnectTimeout=$ConnectTimeout")
        if($operationPassword){$scpArgs+=@('-o','NumberOfPasswordPrompts=1','-o','PubkeyAuthentication=no','-o','PreferredAuthentications=password,keyboard-interactive')}else{$scpArgs+=@('-o','BatchMode=yes')}
        if($info.Port -gt 0){$scpArgs+=@('-P',[string]$info.Port)}; if($identity){$scpArgs+=@('-i',$identity,'-o','IdentitiesOnly=yes')}
        $scpArgs+=@("$(Get-Destination $info):$RemotePath",$localTemp)
        $transfer=Invoke-NativeWithPassword $scp $scpArgs $null $operationPassword
    }
    if ($transfer.ExitCode -eq 0) { Move-Item -LiteralPath $localTemp -Destination $localFull -Force }
    else { Remove-Item -LiteralPath $localTemp -Recurse -Force -ErrorAction SilentlyContinue }
    $name=if($transfer.ExitCode -eq 0){$null}else{'DOWNLOAD_FAILED'}
    if ($transfer.ExitCode -eq 0 -and $expectedHash -and (Test-Path -LiteralPath $localFull -PathType Leaf)) {
        $actualHash=Get-FileSha256 $localFull
        if($actualHash -ne $expectedHash){$transfer=[pscustomobject]@{ExitCode=1;StdOut='';StdErr='SHA-256 mismatch after download'};$name='CHECKSUM_MISMATCH'}
    }
    $null=Write-SshResult ($transfer.ExitCode -eq 0) 'download' $name $info.Alias $transfer.ExitCode '' $transfer.StdOut $transfer.StdErr -Json:$Json
    exit $transfer.ExitCode
}
catch {
    $message=$_.Exception.Message
    if ($_.ScriptStackTrace) { $message += " | $($_.ScriptStackTrace)" }
    $name=if($message -match '^([A-Z_]+):'){ $matches[1] }else{'REMOTE_COMMAND_FAILED'}
    $null=Write-SshResult $false $Action $name $Target 1 $message '' '' -Json:$Json
    exit 1
}
