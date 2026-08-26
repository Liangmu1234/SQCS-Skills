# Stable error categories

- `TARGET_NOT_FOUND`: target cannot be resolved.
- `CREDENTIAL_REQUIRED`: no usable key, agent, or process-scoped password.
- `TCP_TIMEOUT`: route or handshake timed out.
- `CONNECTION_REFUSED`: SSH port rejected the connection.
- `HOST_KEY_CHANGED`: known host identity changed; investigate manually.
- `PASSWORD_AUTH_FAILED`: supplied password was rejected.
- `PUBLIC_KEY_AUTH_FAILED`: configured key was rejected.
- `PUBLIC_KEY_INSTALL_FAILED`: password login worked but key installation failed.
- `KEY_AUTH_VERIFY_FAILED`: independent key-only verification failed.
- `REMOTE_SHELL_UNAVAILABLE`: neither Bash nor POSIX sh is usable.
- `REMOTE_COMMAND_FAILED`: remote command returned nonzero.
- `SESSION_REUSE_FAILED`: OpenSSH control connection could not be managed.
- `UPLOAD_FAILED` / `DOWNLOAD_FAILED`: transfer failed after fallback.
- `CHECKSUM_MISMATCH`: transferred file does not match SHA-256.
- `LOCAL_TOOL_MISSING`: required Windows OpenSSH executable is absent.

Use `-Json` for `ok`, `stage`, `error`, `target`, `exit_code`, `message`, `stdout`, and `stderr`.

The connector may retry once without an invalid reusable connection. It must not bypass changed host keys, repeat a rejected password, or retry a failed remote command automatically.

## 错误处理决策树

遇到错误时按下面的顺序排查：

### 网络层错误

| 错误码 | 含义 | 排查步骤 |
|---|---|---|
| `TCP_TIMEOUT` | TCP 握手超时 | 1. `Test-NetConnection <host> -Port <port>` 确认端口<br>2. 检查跳板机 / VPN 是否连上<br>3. 检查目标机 sshd 是否运行：`Get-Service sshd`（如果是 Windows 目标）或从其他机器 ssh<br>4. 检查防火墙（ufw / firewalld / iptables / 云安全组）<br>5. 如果通过跳板，检查跳板机 sshd 和 ProxyJump 配置 |
| `CONNECTION_REFUSED` | 端口拒绝连接 | 1. sshd 没启动 → 远端 `systemctl start sshd`<br>2. 端口不对 → 核对 targets.json 的 port 字段<br>3. sshd 监听地址不对（`ListenAddress 127.0.0.1` 而非 `0.0.0.0`）<br>4. xinetd / tcpwrappers 拦截 |

### 认证层错误

| 错误码 | 含义 | 排查步骤 |
|---|---|---|
| `CREDENTIAL_REQUIRED` | 没有可用凭据 | 1. 检查 `~/.ssh/codex_ssh_content_ed25519` 是否存在<br>2. 检查 ssh-agent 是否加载了密钥<br>3. 首次使用必须先 bootstrap（需设 `CODEX_SSH_PASSWORD`） |
| `PASSWORD_AUTH_FAILED` | 密码被拒 | 1. 核对密码（注意大小写 / 特殊字符）<br>2. 远端 sshd 是否允许密码登录（`PasswordAuthentication yes`）<br>3. 账号是否被锁定（`passwd -S <user>` / `pam_tally2`） |
| `PUBLIC_KEY_AUTH_FAILED` | 密钥被拒 | 1. 远端 `~/.ssh/authorized_keys` 是否含本机公钥<br>2. `~/.ssh` 权限是否 700，`authorized_keys` 是否 600<br>3. home 目录是否被 group writable（sshd 严格模式会拒绝）<br>4. SELinux 上下文：`restorecon -R ~/.ssh` |
| `PUBLIC_KEY_INSTALL_FAILED` | bootstrap 装密钥失败 | 通常是远端 `~/.ssh` 不存在或权限不对。手动 ssh 上去 `mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys`，再重试 bootstrap |
| `KEY_AUTH_VERIFY_FAILED` | 密钥装好但验证连接失败 | 1. 远端 sshd `PubkeyAuthentication` 是否 yes<br>2. `AuthorizedKeysFile` 路径是否被改<br>3. 远端 `tail -f /var/log/auth.log` 看具体拒绝原因 |

### 主机身份错误

| 错误码 | 含义 | 排查步骤 |
|---|---|---|
| `HOST_KEY_CHANGED` | host key 变了 | **硬错误，不要自动绕过**。先确认：1. 是否重装了系统（合法变更）<br>2. 是否换了网卡 / IP 复用（合法）<br>3. 是否中间人攻击（**危险**）<br>确认合法后，手动 `ssh-keygen -R <host>` 删除旧条目，再重连确认新指纹 |

### 远程执行错误

| 错误码 | 含义 | 排查步骤 |
|---|---|---|
| `REMOTE_SHELL_UNAVAILABLE` | bash 和 sh 都不可用 | 1. 远端是极简容器 / 嵌入式系统？<br>2. `/etc/shells` 是否包含 bash/sh<br>3. 用 `-Json` 看详细 message |
| `REMOTE_COMMAND_FAILED` | 命令返回非零 | 1. `-Json` 输出里的 `stderr` 看具体错误<br>2. 脚本里 `set -e` 可能导致中间命令失败就退出，调试时先去掉<br>3. 检查远端命令是否需要 root 权限 |
| `SESSION_REUSE_FAILED` | ControlMaster 复用失败 | 不影响功能，会自动回退新连接。如反复出现：1. `sshctl.cmd close -Target <host>` 清旧控制连接<br>2. 检查远端 `MaxSessions` / `MaxStartups`<br>3. 长期禁用：把 targets.json 的 `supports_connection_reuse` 改 false |

### 传输错误

| 错误码 | 含义 | 排查步骤 |
|---|---|---|
| `UPLOAD_FAILED` / `DOWNLOAD_FAILED` | SFTP + SCP 都失败 | 1. 远端是否启用 SFTP（`Subsystem sftp` 在 sshd_config）<br>2. 远端磁盘是否满（`df -h`）<br>3. 远端目标目录是否有写权限<br>4. 大文件超时 → 增大 `-ConnectTimeout` 或拆分 |
| `CHECKSUM_MISMATCH` | SHA-256 不匹配 | 传输过程被中断 / 网络不稳定。重试一次；反复出现说明网络丢包严重，换 SFTP 块大小或先在远端压缩 |

### 本地工具错误

| 错误码 | 含义 | 排查步骤 |
|---|---|---|
| `LOCAL_TOOL_MISSING` | 找不到 ssh.exe | 1. Windows 10+ 自带 OpenSSH，`Get-WindowsCapability -Online ?Name=OpenSSH.Client*` 确认<br>2. 或安装 OpenSSH：`Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0`<br>3. 确认 `ssh.exe` 在 PATH |
