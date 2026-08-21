---
name: ssh-content
description: Connect to and operate Linux or Unix SSH servers from Windows, including first-use password bootstrap, reusable key authentication, complex remote scripts, diagnostics, and verified file transfer. Use for remote server inspection, troubleshooting, commands, logs, services, containers, hardware checks, uploads, or downloads.
---

# SSH Content

Use `scripts/sshctl.cmd`. It resolves shared targets, performs secure first-use key bootstrap when a process-scoped password is available, and transports scripts without PowerShell/Bash quoting problems.

## Fast path

```powershell
$script = 'hostname'
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
& "<skill-dir>\scripts\sshctl.cmd" exec -Target "<alias-or-host>" -CommandB64 $encoded
```

First use with a password supplied by the user:

```powershell
$env:CODEX_SSH_PASSWORD = "<provided-password>"
try {
    & "<skill-dir>\scripts\sshctl.cmd" bootstrap -Target "<host>" -User "<user>" -Alias "<stable-alias>"
}
finally {
    Remove-Item Env:CODEX_SSH_PASSWORD -ErrorAction SilentlyContinue
}
```

Bootstrap installs a dedicated Ed25519 public key idempotently, verifies a fresh key-only connection, stores only non-secret target metadata, and clears temporary password state. It never changes `sshd_config`, disables password login, or restarts SSH.

## Modes

- `exec`: run a UTF-8 script supplied only through `-CommandB64` and remote stdin.
- `check`: verify authentication, remote shell, hostname, and user.
- `bootstrap`: explicitly perform first-use password-to-key enrollment.
- `upload` / `download`: atomic SFTP transfer with SCP fallback and file SHA-256 verification.
- `close`: close a reusable OpenSSH control connection when supported.

For every remote command, including a single simple command, build the complete script locally, encode its UTF-8 bytes with Base64, and pass only `-CommandB64`. Never invoke `sshctl exec` with `-Command` or `-ScriptPath`. Read [references/command-transport.md](references/command-transport.md) for examples.

Read [references/authentication.md](references/authentication.md) for target resolution and credential boundaries. Read [references/errors.md](references/errors.md) only when an operation fails.

## Operating rules

- Start with read-only checks unless the user requested a remote state change.
- Use one `sshctl` invocation per logical operation; do not recreate askpass or SCP plumbing manually.
- Use Base64 script transport for every `exec` operation. Do not place remote shell text directly on the PowerShell command line.
- Never pass passwords as command-line arguments or write them into scripts, target records, SSH config, logs, or responses.
- Changed host keys are hard failures. Do not delete `known_hosts` entries automatically.
- Automatic recovery is limited to one meaningful retry.
- Report remote state changes and preserve the remote command's exit status.

The legacy `scripts/connect-ssh.cmd -Target ... -Command ...` interface remains supported only as a compatibility wrapper; it Base64-encodes the command before delegating to `sshctl`.
