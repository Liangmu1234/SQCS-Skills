#!/usr/bin/env python3
"""
network_device_ssh.py - 网络设备（交换机/路由器/BMC）SSH 命令执行模板

适用场景：
- H3C Comware 7 交换机（如 S6850/S9850/S5560 等，只支持 ssh-rsa + 密码认证）
- Cisco IOS / 华为 VRP（同理，老固件只支持 ssh-rsa）
- BMC 带外管理口（H3C HDM / Dell iDRAC 等，定制 shell）

用法：
  先按 SKILL.md 的 SecureString 示例设置 SW_SSH_PASSWORD
  python network_device_ssh.py --host 10.12.180.201 --user admin --cmd "display version"

环境变量（必需，避免密码出现在进程列表）：
  SW_SSH_PASSWORD=<password> python network_device_ssh.py --host ... --user ... --cmd ...

关键点：
1. OpenSSH 10+ 默认禁用 ssh-rsa，本脚本通过 -o HostKeyAlgorithms=+ssh-rsa 启用
2. Windows 无 sshpass，本脚本用 SSH_ASKPASS + SSH_ASKPASS_REQUIRE=force 自动喂密码
3. 每条命令单独 ssh 执行（网络设备是交互式 CLI，不支持 bash -s）
4. 提供 --paging-cmd 时，它与目标命令在同一个交互式 SSH 会话中执行
5. askpass 脚本用完即删，脚本文件本身不包含密码
"""
import argparse, os, subprocess, sys, tempfile

def run_on_device(host, user, password, commands, port=22, timeout=30, paging_cmd=''):
    """在网络设备上执行一条或多条命令，返回 stdout 列表"""
    # 1. 写不包含密码的 askpass 脚本；密码只通过子进程环境变量传递
    fd, askpass_path = tempfile.mkstemp(prefix='ssh_askpass_', suffix='.cmd')
    os.close(fd)
    try:
        with open(askpass_path, 'w', encoding='ascii', newline='\r\n') as f:
            f.write('@echo off\r\n')
            f.write('powershell.exe -NoProfile -NonInteractive -Command "[Console]::Out.WriteLine($env:SW_SSH_PASSWORD)"\r\n')

        env = os.environ.copy()
        env['SW_SSH_PASSWORD'] = password
        env['SSH_ASKPASS'] = askpass_path
        env['SSH_ASKPASS_REQUIRE'] = 'force'
        env['DISPLAY'] = 'dummy'

        results = []
        for cmd in commands:
            ssh_args = [
                'ssh',
                '-o', f'HostKeyAlgorithms=+ssh-rsa',
                '-o', f'PubkeyAcceptedAlgorithms=+ssh-rsa',
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=accept-new',
                '-o', 'PreferredAuthentications=password',
                '-o', 'NumberOfPasswordPrompts=1',
                '-p', str(port),
            ]
            if paging_cmd:
                # 分页设置必须与目标命令处于同一个交互式 SSH 会话。
                ssh_args.extend(['-tt', f'{user}@{host}'])
                stdin_data = paging_cmd + '\n' + cmd + '\n'
            else:
                ssh_args.extend([f'{user}@{host}', cmd])
                stdin_data = None
            try:
                r = subprocess.run(ssh_args, env=env, capture_output=True,
                                   input=stdin_data, timeout=timeout, text=True,
                                   encoding='utf-8', errors='replace')
                results.append({'cmd': cmd, 'rc': r.returncode,
                                'stdout': r.stdout, 'stderr': r.stderr})
            except subprocess.TimeoutExpired:
                results.append({'cmd': cmd, 'rc': -1, 'stdout': '',
                                'stderr': f'TIMEOUT after {timeout}s'})
        return results
    finally:
        if os.path.exists(askpass_path):
            os.remove(askpass_path)

def main():
    p = argparse.ArgumentParser(description='网络设备 SSH 命令执行')
    p.add_argument('--host', required=True, help='设备 IP')
    p.add_argument('--user', required=True, help='用户名')
    p.add_argument('--port', type=int, default=22)
    p.add_argument('--cmd', action='append', required=True, help='要执行的命令（可多次指定）')
    p.add_argument('--paging-cmd', default='',
                   help='禁用分页命令（会与每条目标命令在同一 SSH 会话中执行；Comware 用 "screen-length disable"，Cisco 用 "terminal length 0"）')
    p.add_argument('--timeout', type=int, default=30)
    args = p.parse_args()

    password = os.environ.get('SW_SSH_PASSWORD')
    if not password:
        print('ERROR: 请通过 SW_SSH_PASSWORD 环境变量提供密码；不支持 --password 参数', file=sys.stderr)
        sys.exit(1)

    results = run_on_device(args.host, args.user, password, args.cmd,
                            args.port, args.timeout, args.paging_cmd)
    for r in results:
        print(f'>>> {r["cmd"]}  (rc={r["rc"]})')
        print(r['stdout'])
        if r['stderr']:
            for line in r['stderr'].splitlines():
                if line.strip() and 'post-quantum' not in line and 'openssh.com/pq' not in line:
                    print(f'  [stderr] {line}')
        print()

if __name__ == '__main__':
    main()
