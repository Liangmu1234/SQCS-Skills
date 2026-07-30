---
name: ssh-content
description: Connect to arbitrary SSH servers from Windows, resolve optional credentials from a Markdown server registry, run remote commands and diagnostics, and inspect Linux files, processes, ports, services, containers, or hardware state. Use when Codex is asked to connect to, inspect, troubleshoot, or operate a remote server over SSH without exposing credentials.
---

# SSH Content

Use the bundled connector for the shortest deterministic path. Keep this skill generic: never add hostnames, IP addresses, usernames, ports, passwords, server state, or server-specific recovery procedures to skill files.

## Connect

Run:

```powershell
& "<skill-dir>\scripts\connect-ssh.cmd" -Target "<IP-or-alias>" -Command "<remote-command>"
```

For a connection-only request, omit `-Command`; the connector returns the remote hostname, user, kernel, and uptime. Prefer one connector invocation per user operation.

The `.cmd` entry point bypasses restrictive local PowerShell execution policy and invokes the connector once. The connector:

- resolves an IP or alias from the configured Markdown registry when available;
- reads credentials only in memory and never prints the matched credential row;
- supports direct hostnames/IPs, `-User`, `-Port`, and `-KeyPath` overrides;
- uses key or SSH-agent authentication when no registered password is available;
- accepts new host keys but rejects changed keys;
- deletes temporary askpass state and returns the native SSH exit code.

Set `CODEX_SSH_REGISTRY` or pass `-RegistryPath` to override the default registry location. If required connection data is unavailable, ask only for the missing value. Never request a password in a command-line argument; accept it through a temporary environment variable or other ephemeral secret channel.

When the user provides credentials for an unregistered target, pass the username with `-User` and place the password in the process-only `CODEX_SSH_PASSWORD` variable for that invocation:

```powershell
$env:CODEX_SSH_PASSWORD = "<provided-password>"
try {
    & "<skill-dir>\scripts\connect-ssh.cmd" -Target "<host>" -User "<username>" -Command "<remote-command>"
}
finally {
    Remove-Item Env:CODEX_SSH_PASSWORD -ErrorAction SilentlyContinue
}
```

Do not print, persist, or pass the password as a CLI argument. The connector consumes and removes `CODEX_SSH_PASSWORD` in its child process before starting SSH.

## Operate

Start with read-only checks. Run only checks relevant to the request. A useful generic baseline is:

```bash
hostname
date
uname -a
uptime
free -h
df -hT -x tmpfs -x devtmpfs
ps -eo pid,ppid,user,stat,pcpu,pmem,comm,args --sort=-pcpu | head -n 25
ss -tulpen 2>/dev/null | head -n 120
systemctl --type=service --state=running --no-pager --no-legend 2>/dev/null | head -n 80
docker ps -a 2>/dev/null || true
```

For complex commands, pass a single quoted remote command to the connector. Keep credentials out of remote commands, scripts, logs, and responses.

Before changing packages, services, boot configuration, firewall rules, storage, accounts, or rebooting, explain the intended change and follow the user's authorization scope. Verify changes after applying them.

## Report

Summarize:

- whether SSH succeeded;
- the resolved target only when it is useful and non-secret;
- important command results and exact failures;
- every remote state change made.

Do not reproduce passwords, credential rows, askpass contents, or secret-bearing environment variables.
