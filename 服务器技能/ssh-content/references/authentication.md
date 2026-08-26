# Authentication and targets

Shared state is stored under `${CODEX_HOME}/state/ssh-content`, or `~/.codex/state/ssh-content` when `CODEX_HOME` is unset. `targets.json` contains aliases, hosts, ports, users, identity paths, remote shell capability, last success time, and connection-reuse capability. It never contains passwords.

Resolution order is: shared targets, OpenSSH config, an explicitly configured legacy Markdown registry, then the raw target.

Authentication order is: explicit key, recorded dedicated key, OpenSSH-configured key, SSH agent, then process-scoped `CODEX_SSH_PASSWORD`. When password authentication succeeds, bootstrap is automatic unless `-NoBootstrap` was specified.

The dedicated key is `~/.ssh/codex_ssh_content_ed25519`. Public-key installation appends only when the exact key is absent and applies `700` to `.ssh` and `600` to `authorized_keys`.

Use `-NoBootstrap` when public-key installation is not authorized. Passwords are never persisted to Windows Credential Manager.

## targets.json 手动管理

`targets.json` 是普通 JSON 数组，每个元素结构：

```json
{
  "alias": "sqcs",
  "host": "10.12.174.79",
  "port": 22,
  "user": "root",
  "identity_file": "C:\\Users\\z62875\\.ssh\\codex_ssh_content_ed25519",
  "remote_shell": "bash",
  "supports_connection_reuse": true,
  "last_success_at": "2026-08-21T14:30:00+08:00"
}
```

字段说明：
- `alias` / `host`：`-Target` 可以匹配任意一个
- `port`：0 表示用 OpenSSH 默认 22
- `identity_file`：通常就是 bootstrap 装好的 `~/.ssh/codex_ssh_content_ed25519`
- `remote_shell`：`bash`（默认）或 `sh`，影响 `exec` 时的远程 shell 选择
- `supports_connection_reuse`：是否尝试 ControlMaster 复用
- `last_success_at`：上次成功连接时间（bootstrap / check / exec 成功时自动更新）

**列出已登记 target：**

```powershell
Get-Content "$env:USERPROFILE\.codex\state\ssh-content\targets.json" -Raw | ConvertFrom-Json |
  Format-Table alias, host, port, user, remote_shell, supports_connection_reuse
```

**手动添加 target（bootstrap 前预登记）：**

```powershell
$targets = "$env:USERPROFILE\.codex\state\ssh-content\targets.json"
$records = if (Test-Path $targets) { Get-Content $targets -Raw | ConvertFrom-Json } else { @() }
$records += [pscustomobject]@{
  alias = 'sqcs'; host = '10.12.174.79'; port = 22; user = 'root'
  identity_file = "$env:USERPROFILE\.ssh\codex_ssh_content_ed25519"
  remote_shell = 'bash'; supports_connection_reuse = $true; last_success_at = $null
}
$records | ConvertTo-Json -Depth 5 | Set-Content $targets -Encoding UTF8
```

**删除 target：**

```powershell
$targets = "$env:USERPROFILE\.codex\state\ssh-content\targets.json"
$records = Get-Content $targets -Raw | ConvertFrom-Json
$records = $records | Where-Object { $_.alias -ne 'sqcs' -and $_.host -ne '10.12.174.79' }
$records | ConvertTo-Json -Depth 5 | Set-Content $targets -Encoding UTF8
```

**注意**：手动添加的 target 仍需先跑一次 `bootstrap` 把公钥装到远端 authorized_keys，否则只能用密码登录。
