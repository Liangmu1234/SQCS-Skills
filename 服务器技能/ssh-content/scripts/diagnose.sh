#!/usr/bin/env bash
# diagnose.sh - Linux 服务器一键诊断快照
# 用法（通过 ssh-content skill 的 Base64 传输执行）：
#   $script = Get-Content -LiteralPath '<skill-dir>\scripts\diagnose.sh' -Raw -Encoding UTF8
#   $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
#   sshctl.cmd exec -Target <host> -CommandB64 $encoded
#
# 输出分段：系统 / CPU / 内存 / 磁盘 / 网络 / 进程 / 服务 / 内核 / 最近日志 / 硬件
# 全部只读，不修改任何系统状态。

set +e
echo "============================================================"
echo "=== 服务器诊断快照 $(date '+%Y-%m-%d %H:%M:%S %z') ==="
echo "=== host: $(hostname)  user: $(whoami)  uptime: $(uptime -p 2>/dev/null || echo '?') ==="
echo "============================================================"

echo ""
echo "### 1. 系统"
echo "--- /etc/os-release ---"
cat /etc/os-release 2>/dev/null | grep -E '^(NAME|VERSION|PRETTY_NAME|VERSION_ID)='
echo "--- kernel ---"
uname -a
echo "--- last boot ---"
who -b 2>/dev/null

echo ""
echo "### 2. CPU"
echo "--- /proc/cpuinfo 摘要 ---"
grep -m1 'model name' /proc/cpuinfo 2>/dev/null
echo "物理核数: $(grep -c ^processor /proc/cpuinfo 2>/dev/null)"
echo "插槽: $(grep -m1 'physical id' /proc/cpuinfo 2>/dev/null | awk '{print $4}' || echo '?')"
echo "--- 负载 ---"
uptime
echo "--- TOP 5 CPU 进程 ---"
ps -eo pid,pcpu,pmem,comm --sort=-pcpu 2>/dev/null | head -6

echo ""
echo "### 3. 内存"
echo "--- free -h ---"
free -h 2>/dev/null || free
echo "--- TOP 5 内存进程 ---"
ps -eo pid,pcpu,pmem,comm --sort=-pmem 2>/dev/null | head -6

echo ""
echo "### 4. 磁盘"
echo "--- df -h ---"
df -h -x tmpfs -x devtmpfs -x squashfs 2>/dev/null || df -h
echo "--- 块设备 ---"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL 2>/dev/null || lsblk
echo "--- LVM ---"
lvs 2>/dev/null && echo "--- vgs ---" && vgs 2>/dev/null
echo "--- 大文件 top 5 (/var/log, /tmp, /home) ---"
du -ah /var/log /tmp /home 2>/dev/null | sort -rh | head -5

echo ""
echo "### 5. 网络"
echo "--- IP 地址 ---"
ip -br addr 2>/dev/null || ip addr 2>/dev/null | grep -E '^[0-9]+:|inet '
echo "--- 路由 ---"
ip route 2>/dev/null | head -10
echo "--- 监听端口 ---"
ss -tulnp 2>/dev/null | head -20 || netstat -tulnp 2>/dev/null | head -20
echo "--- DNS ---"
cat /etc/resolv.conf 2>/dev/null | grep -v '^#'
echo "--- 网卡链路 ---"
ip -br link 2>/dev/null

echo ""
echo "### 6. 进程 / 服务"
echo "--- systemd 失败服务 ---"
systemctl --failed --no-legend --no-pager 2>/dev/null | head -20
echo "--- 关键服务状态 ---"
for svc in sshd nginx apache2 docker containerd firewalld NetworkManager chronyd ntpd; do
  if systemctl is-enabled "$svc" >/dev/null 2>&1; then
    printf "  %-16s %s\n" "$svc" "$(systemctl is-active $svc 2>/dev/null)"
  fi
done

echo ""
echo "### 7. 内核 / dmesg"
echo "--- 内核参数 ---"
sysctl kernel.hostname kernel.osrelease kernel.version 2>/dev/null
echo "--- dmesg 最近 20 条（errors/warnings）---"
dmesg -T 2>/dev/null | grep -iE 'error|warn|fail|crit|emerg' | tail -20 || dmesg 2>/dev/null | tail -20

echo ""
echo "### 8. 最近日志"
echo "--- /var/log/messages 最近 10 条 ---"
tail -10 /var/log/messages 2>/dev/null || journalctl -n 10 --no-pager 2>/dev/null
echo "--- /var/log/syslog 最近 10 条 ---"
tail -10 /var/log/syslog 2>/dev/null
echo "--- auth.log 最近 10 条（登录/失败）---"
tail -10 /var/log/auth.log 2>/dev/null || journalctl -u ssh -n 10 --no-pager 2>/dev/null

echo ""
echo "### 9. 硬件（若可用）"
echo "--- PCI（GPU/HBA/网卡）---"
lspci 2>/dev/null | grep -iE 'vga|nvidia|amd|raid|sata|ethernet|infiniband|fibre' | head -10
echo "--- USB ---"
lsusb 2>/dev/null | head -5
echo "--- 传感器（温度/风扇，需 lm-sensors）---"
sensors 2>/dev/null | head -30 || echo "  (lm-sensors 未安装)"
echo "--- IPMI（若有 ipmitool）---"
which ipmitool >/dev/null 2>&1 && ipmitool mc info 2>/dev/null | head -8 || echo "  (无 ipmitool 或无 IPMI 设备)"
echo "--- BMC 网络配置（若有 ipmitool）---"
which ipmitool >/dev/null 2>&1 && ipmitool lan print 1 2>/dev/null | head -15 || true

echo ""
echo "### 10. 时间同步"
echo "--- timedatectl ---"
timedatectl 2>/dev/null || date
echo "--- chrony ---"
chronyc tracking 2>/dev/null || echo "  (无 chrony)"
echo "--- NTP ---"
ntpq -p 2>/dev/null || echo "  (无 ntpd)"

echo ""
echo "============================================================"
echo "=== 诊断完成 $(date '+%Y-%m-%d %H:%M:%S %z') ==="
echo "============================================================"
