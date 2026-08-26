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

## 一键诊断快照（diagnose.sh）

skill 自带 `scripts/diagnose.sh`，输出 10 段只读诊断信息（系统/CPU/内存/磁盘/网络/进程/服务/内核日志/硬件/时间同步），不修改任何系统状态，适合巡检或故障首查。

```powershell
$script = Get-Content -LiteralPath "<skill-dir>\scripts\diagnose.sh" -Raw -Encoding UTF8
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target <host> -CommandB64 $encoded
```

输出分段：
1. 系统（OS / kernel / last boot）
2. CPU（型号 / 核数 / 负载 / TOP 5 CPU 进程）
3. 内存（free -h / TOP 5 内存进程）
4. 磁盘（df / lsblk / LVM / 大文件 TOP 5）
5. 网络（IP / 路由 / 监听端口 / DNS / 链路）
6. 进程与服务（失败 unit / 关键服务状态）
7. 内核（sysctl / dmesg 最近 errors/warnings）
8. 日志（messages / syslog / auth.log 最近 10 条）
9. 硬件（PCI / USB / sensors / IPMI mc info + lan print）
10. 时间同步（timedatectl / chronyc / ntpq）

## 常用诊断命令速查（Base64 传输执行）

对单条命令也必须走 Base64 传输，不能直接传 `-Command`。下面是常用只读命令，按场景分组：

```powershell
# 通用模板：把 $script 换成下表中的命令
$script = 'hostname'
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target <host> -CommandB64 $encoded
```

| 场景 | 命令 |
|---|---|
| 系统信息 | `uname -a` / `cat /etc/os-release` / `hostnamectl` |
| 运行时间 / 负载 | `uptime` / `w` |
| CPU | `lscpu` / `nproc` / `cat /proc/cpuinfo \| grep 'model name' \| head -1` |
| 内存 | `free -h` / `cat /proc/meminfo \| head -5` |
| 磁盘 | `df -h` / `lsblk` / `fdisk -l 2>/dev/null` / `du -sh /var/log` |
| 网络 IP | `ip -br addr` / `ip route` |
| 监听端口 | `ss -tulnp` / `netstat -tulnp` |
| 进程 | `ps -eo pid,pcpu,pmem,comm --sort=-pcpu \| head -10` |
| 服务 | `systemctl --failed` / `systemctl status <svc>` |
| 日志 | `journalctl -u <svc> -n 50 --no-pager` / `tail -50 /var/log/messages` |
| 登录审计 | `last -n 20` / `lastb -n 20 2>/dev/null` / `tail -50 /var/log/auth.log` |
| 内核日志 | `dmesg -T \| tail -30` / `dmesg -T \| grep -iE 'error\|warn'` |
| 时间 | `timedatectl` / `date` / `chronyc tracking` |
| 网络连通性 | `ping -c 3 8.8.8.8` / `ss -s` / `ip -s link` |
| 硬件 | `lspci` / `lsusb` / `lshw -short 2>/dev/null` / `sensors` |
| IPMI（若已装） | `ipmitool mc info` / `ipmitool sdr` / `ipmitool sel info` |
| GPU（若有） | `nvidia-smi` / `rocm-smi 2>/dev/null` |

## targets.json 管理（手动维护服务器列表）

skill 把 target 元数据存在 `${CODEX_HOME}/state/ssh-content/targets.json`（默认 `~/.codex/state/ssh-content/targets.json`），**不存密码**。

**列出已登记的 target：**

```powershell
Get-Content "$env:USERPROFILE\.codex\state\ssh-content\targets.json" -Raw | ConvertFrom-Json | Format-Table alias, host, port, user, identity_file, remote_shell
```

**手动添加一个 target（在首次 bootstrap 前预登记）：**

```powershell
$targets = "$env:USERPROFILE\.codex\state\ssh-content\targets.json"
$records = if (Test-Path $targets) { Get-Content $targets -Raw | ConvertFrom-Json } else { @() }
$records += [pscustomobject]@{
  alias = 'sqcs'
  host  = '10.12.174.79'
  port  = 22
  user  = 'root'
  identity_file = "$env:USERPROFILE\.ssh\codex_ssh_content_ed25519"
  remote_shell = 'bash'
  supports_connection_reuse = $true
  last_success_at = $null
}
$records | ConvertTo-Json -Depth 5 | Set-Content $targets -Encoding UTF8
```

**删除一个 target：**

```powershell
$targets = "$env:USERPROFILE\.codex\state\ssh-content\targets.json"
$records = Get-Content $targets -Raw | ConvertFrom-Json
$records = $records | Where-Object { $_.alias -ne 'sqcs' -and $_.host -ne '10.12.174.79' }
$records | ConvertTo-Json -Depth 5 | Set-Content $targets -Encoding UTF8
```

**注意**：手动添加的 target 仍需先跑一次 `bootstrap` 把公钥装到远端 authorized_keys，否则只能用密码登录（每次都要传 `CODEX_SSH_PASSWORD`）。

## 多行脚本执行（Base64 传输）

复杂多行脚本（含 if/for/heredoc/管道）必须整体打包成 Base64 传输，**不要**手工在 PowerShell 里转义 `$` / 引号 / 管道——全部留在脚本内部，编码后传输。

**方式 A：脚本字符串直接编码**

```powershell
$script = @'
set -e
echo "=== host: $(hostname) ==="
for svc in sshd nginx docker; do
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    printf "  %-10s %s\n" "$svc" "$(systemctl is-active $svc)"
  fi
done
echo "--- disk usage ---"
df -h | awk 'NR==1 || $5+0 > 80'
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target <host> -CommandB64 $encoded
```

**方式 B：从本地脚本文件读取**

```powershell
$script = Get-Content -LiteralPath '.\diag.sh' -Raw -Encoding UTF8
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target <host> -CommandB64 $encoded
```

**坑（禁止这样做）：**
- ❌ 在 PowerShell 单行 `-Command` 里塞 `bash -c '...'`，shell 转义会出错
- ❌ 把 heredoc 或 `awk '{print $1}'` 拼到 `-Command` 字符串里，`$1` 会被 PowerShell 当变量替换
- ❌ 用反斜杠转义 `$`，不同 shell 转义规则不一致——全部 Base64 传输，不转义

## 密码安全设置（首次 bootstrap）

首次 bootstrap 时需要密码，通过 `CODEX_SSH_PASSWORD` 环境变量传入，**绝不能**用 `-Password` 参数（不存在）或写进脚本。

**推荐方式（SecureString 转 Plain，仅当前进程可见）：**

```powershell
$secure = Read-Host 'Enter password' -AsSecureString
$ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $env:CODEX_SSH_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
}
finally {
  [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}
try {
  sshctl.cmd bootstrap -Target 10.12.174.79 -User root -Alias sqcs
}
finally {
  Remove-Item Env:CODEX_SSH_PASSWORD -ErrorAction SilentlyContinue
}
```

不提供明文密码示例。若无法使用密码管理器，请沿用上面的 `Read-Host -AsSecureString` 方式，并确保在 `finally` 中清理环境变量。

**禁止这样做：**
- ❌ 把密码作为参数传给 sshctl（不存在该参数，也不允许加）
- ❌ 写进 targets.json / ~/.ssh/config / 任何脚本文件 / 日志
- ❌ 跑完 bootstrap 后不清理环境变量

bootstrap 成功后，后续 `exec`/`check`/`upload`/`download` 都走密钥认证，不再需要密码。

## 连接复用控制（ControlMaster）

sshctl 默认尝试复用 OpenSSH ControlMaster 控制连接（`supports_connection_reuse=true` 的 target），减少每次 SSH 握手开销。

**默认行为：**
- `exec` / `check` / `upload` / `download` 自动尝试复用已存在的控制连接
- 复用失败不影响功能，会回退到新连接
- 任务跑完后控制连接**保持打开**（直到 `close` 或超时）

**何时手动 close：**
- 跑完大批量任务，确认后续一段时间不再访问该 host → 释放远端 sshd 会话槽
- target 即将变更（换密码 / 换密钥 / 重装系统）→ 避免旧连接干扰
- 排查连接问题时 → 先 close 清状态

```powershell
sshctl.cmd close -Target <host>
```

**禁用复用（一次性，调试用）：**

```powershell
sshctl.cmd exec -Target <host> -CommandB64 <encoded> -NoReuse
```

**长期禁用复用**：编辑 targets.json 把对应 target 的 `supports_connection_reuse` 改为 `false`。

## 跳板机访问（ProxyJump）

sshctl 内部调用 OpenSSH `ssh.exe`，**完全兼容 OpenSSH `~/.ssh/config` 的 ProxyJump 配置**。在 `~/.ssh/config` 里配好跳板：

```sshconfig
# 跳板机
Host jump
  HostName 10.12.1.1
  User jumpuser
  Port 22

# 通过跳板访问的内网机器
Host sqcs-internal
  HostName 10.12.174.79
  User root
  ProxyJump jump
```

之后直接 `sshctl.cmd exec -Target sqcs-internal ...`，OpenSSH 会自动走跳板，无需 sshctl 特殊处理。

**坑：**
- 跳板机必须能用密钥登录（不能交互式输密码），因为 sshctl 是非交互的
- 跳板机的 host key 必须在 known_hosts 里（首次连接前先用 ssh 手动确认一次）

## 端口转发 / 隧道

sshctl 目前**不直接支持**端口转发模式（`ssh -L` / `ssh -R` / `ssh -D`）。如果需要端口转发，直接调用系统 ssh.exe：

```powershell
# 本地端口转发（访问远端数据库/Web UI）
ssh.exe -N -L 8080:localhost:80 -i $env:USERPROFILE\.ssh\codex_ssh_content_ed25519 <user>@<host>

# 远程端口转发
ssh.exe -N -R 9090:localhost:80 -i $env:USERPROFILE\.ssh\codex_ssh_content_ed25519 <user>@<host>

# SOCKS 代理
ssh.exe -N -D 1080 -i $env:USERPROFILE\.ssh\codex_ssh_content_ed25519 <user>@<host>
```

sshctl bootstrap 装好的密钥（`~/.ssh/codex_ssh_content_ed25519`）可以直接被 `ssh.exe` 复用，不需要重新配认证。

## 网络设备（交换机/路由器/BMC）SSH 访问

**sshctl 不适用于网络设备**——sshctl 设计为基于密钥认证的 Linux 主机操作工具，而网络设备（H3C Comware / Cisco IOS / 华为 VRP / BMC 带外管理口）通常：
- 只支持密码认证（不接受公钥，bootstrap 装不进去）
- 只支持 ssh-rsa host key 算法（OpenSSH 10+ 默认禁用）
- 命令是交互式 CLI（不是 `bash -s`），`exec_command` 走的不是 shell

### 坑1：OpenSSH 10+ 默认禁用 ssh-rsa（最常见障碍）

OpenSSH 8.7+ 默认禁用 `ssh-rsa`（SHA-1 不安全），但 Comware 7 / 老 IOS / 老 BMC **只支持 ssh-rsa**。连接时报错：

```
Unable to negotiate with <ip> port 22: no matching host key type found. Their offer: ssh-rsa
```

**修复**：连接时显式启用 ssh-rsa：

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa <user>@<ip>
```

### 坑2：OpenSSH 不从 stdin 读密码

Linux 的 `sshpass` 在 Windows 上没有。`echo pass | ssh ...` 不行——OpenSSH 密码必须从 tty 读。

**修复（使用 skill 自带的 SSH_ASKPASS 模板）**：

`scripts/network_device_ssh.py` 只接受 `SW_SSH_PASSWORD` 环境变量，不接受 `--password` 参数；临时 askpass 文件只读取环境变量，本身不写入密码。密码应在交互式会话中输入，并在执行后清理：

```powershell
$secure = Read-Host 'Enter device password' -AsSecureString
$ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $env:SW_SSH_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
  python .\scripts\network_device_ssh.py --host 10.12.180.201 --user admin --cmd "display version"
}
finally {
  [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  Remove-Item Env:SW_SSH_PASSWORD -ErrorAction SilentlyContinue
}
```

### 坑3：paramiko 5.0+ 也默认禁用 ssh-rsa

paramiko 5.0 起 `disabled_algorithms` 参数救不回来（代码层面拒绝），不要浪费时间试 paramiko。

### 坑4：交互式 CLI 设备（Comware / IOS）的命令执行

网络设备不是 `bash -s`，是交互式 CLI shell。`exec_command` 对 Comware 设备：
- 单条命令 OK（如 `display version` / `display cpu-usage` / `display interface brief`）
- 多条命令用 `;` 或 `\n` 分隔可能不工作——设备有自己的 CLI 上下文（user-view / system-view）
- 需要临时禁用分页，否则输出会被 `---- More ----` 截断

**推荐流程**：每条命令单独建立 SSH 会话。非交互 SSH 默认不分页（无 tty 设备不会出现 `---- More ----`），通常不需要预先禁用分页。如果个别设备仍分页，给脚本传 `--paging-cmd`；脚本会在同一个交互式 SSH 会话中先执行分页设置，再执行目标命令：

- H3C Comware 7: `screen-length disable`（注意不是 `screen-length 0`，Comware 7 不认 0）
- Cisco IOS: `terminal length 0`
- 华为 VRP: `screen-length 0 temporary`

```python
# 一次性跑多条命令的模板（用 scripts/network_device_ssh.py）
# 先按上面的方式设置 SW_SSH_PASSWORD，再执行：
# python network_device_ssh.py --host 10.12.180.201 --user admin \
#   --paging-cmd "screen-length disable" \
#   --cmd "display version" --cmd "display cpu-usage" --cmd "display interface brief"
```

### 坑5：BMC 带外管理口

BMC（如 H3C HDM / Dell iDRAC / Supermicro IPMI）的 SSH 通常是 Linux BusyBox 或定制 shell：
- 支持密码认证，**部分支持公钥**（H3C HDM 不支持 SSH 公钥，只能密码）
- 同样可能只支持 ssh-rsa（老固件）
- shell 是 BusyBox，可以跑 `cat /proc/cpuinfo` 这类命令，但不是完整 Linux

按本节「坑1+坑2」方式处理，用 askpass 方案。

### 网络设备 SSH 速查命令表

| 设备类型 | 常用命令 |
|---|---|
| H3C Comware | `display version` / `display cpu-usage` / `display memory` / `display interface brief` / `display vlan` / `display current-configuration` / `display arp` / `display mac-address` / `display link-aggregation summary` / `display irf` |
| Cisco IOS | `show version` / `show ip interface brief` / `show running-config` / `show interfaces status` / `show vlan` / `show mac address-table` / `show cdp neighbors` / `show env power` |
| 华为 VRP | `display version` / `display cpu-usage` / `display memory` / `display interface brief` / `display vlan` / `display current-configuration` |

执行前使用 `--paging-cmd`：Comware 发 `screen-length disable`，VRP 发 `screen-length 0 temporary`，Cisco 发 `terminal length 0`，由脚本保证它与目标命令在同一 SSH 会话中执行。
