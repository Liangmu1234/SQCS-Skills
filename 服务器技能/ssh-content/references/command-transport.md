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

## 多行复杂脚本（必须 Base64 传输）

复杂多行脚本（含 if/for/heredoc/管道/awk）必须整体打包成 Base64 传输，**不要**手工在 PowerShell 里转义 `$` / 引号 / 管道。

### 方式 A：PowerShell here-string 直接编码

```powershell
$script = @'
set -e
echo "=== host: $(hostname) ==="
for svc in sshd nginx docker; do
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    printf "  %-10s %s\n" "$svc" "$(systemctl is-active $svc)"
  fi
done
echo "--- top 5 disk usage ---"
df -h | awk 'NR==1 || $5+0 > 80'
echo "--- recent ssh failures ---"
grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -10
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target server-a -CommandB64 $encoded
```

### 方式 B：从本地脚本文件读取

```powershell
$script = Get-Content -LiteralPath '.\diag.sh' -Raw -Encoding UTF8
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target server-a -CommandB64 $encoded
```

### 禁止这样做

- ❌ 在 PowerShell 单行 `-Command` 里塞 `bash -c '...'`，shell 转义会出错
- ❌ 把 heredoc 或 `awk '{print $1}'` 拼到 `-Command` 字符串里，`$1` 会被 PowerShell 当变量替换
- ❌ 用反斜杠转义 `$`，不同 shell 转义规则不一致——全部 Base64 传输，不转义

## 上传/下载大文件

`upload` / `download` 使用 SFTP + SHA-256 校验，单文件超过 100 MB 时建议拆分或先在远端压缩：

```powershell
# 远端先压缩目录
$script = 'tar -czf /tmp/large_dir.tar.gz -C /var/log large_dir'
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target server-a -CommandB64 $encoded

# 下载压缩包（带 SHA-256 自动校验）
sshctl.cmd download -Target server-a -RemotePath /tmp/large_dir.tar.gz -LocalPath ".\large_dir.tar.gz"

# 下载完成后在远端清理
$script = 'rm -f /tmp/large_dir.tar.gz'
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
sshctl.cmd exec -Target server-a -CommandB64 $encoded
```

SHA-256 不匹配会返回 `CHECKSUM_MISMATCH` 错误，表示传输过程被破坏，需重传。
