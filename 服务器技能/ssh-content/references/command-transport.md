# Command and transfer interfaces

Every `exec` operation must use Base64 transport, even for a single command. Construct the complete remote script locally, encode its UTF-8 bytes, and pass the encoded value as one `-CommandB64` argument.

```powershell
$script = 'hostname'
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target server-a -CommandB64 $encoded
```

For a local script file, read and encode it before invoking `sshctl`:

```powershell
$script = Get-Content -LiteralPath '.\diagnose.sh' -Raw -Encoding UTF8
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target server-a -CommandB64 $encoded
```

`sshctl exec` rejects `-Command`, `-ScriptPath`, and missing `-CommandB64` input. The decoded script is sent through SSH standard input to `bash -s --`, with `sh -s --` fallback. Do not manually escape remote `$`, pipes, JSON, heredocs, or quoting for PowerShell; keep them inside the script before encoding.

```powershell
sshctl.cmd upload -Target server-a -LocalPath ".\input file" -RemotePath "/tmp/input file"
sshctl.cmd download -Target server-a -RemotePath "/tmp/result.tar.gz" -LocalPath ".\result.tar.gz"
```

Uploads use a remote partial name followed by atomic rename. Downloads use a local `.partial` name. Ordinary files are checked with SHA-256. Directories use recursive transfer.
