---
name: sqcsagent
description: Control and diagnose Linux servers connected through the SQCS reverse agent. Use when the user asks to inspect a server, check whether an agent is online, run Linux commands, inspect files, check CPU, memory, disks, GPUs, services, processes, ports, logs, Docker, models, or upload small files through sqcsagent.
---

# SQCS Agent

Use `scripts/sqcsctl.py` for all operations. It automatically starts the bundled local controller when necessary; do not ask the user to open PowerShell or manually start `controller.py`.

## Workflow

1. List connected agents:

   ```bash
   python scripts/sqcsctl.py agents
   ```

2. If exactly one agent is online, omit `--agent`. If multiple are online, select the requested name with `--agent NAME`.

3. Run diagnostics:

   ```bash
   python scripts/sqcsctl.py exec "hostname && uptime"
   python scripts/sqcsctl.py exec "df -hT" --agent NAME
   python scripts/sqcsctl.py read /etc/os-release --agent NAME
   ```

4. Upload small text files only when needed:

   ```bash
   python scripts/sqcsctl.py write /tmp/example.txt "content" --agent NAME
   python scripts/sqcsctl.py upload LOCAL_FILE /tmp/remote-file --agent NAME
   ```

Prefer read-only diagnostic commands first. The remote agent normally runs as root, so do not run destructive commands unless the user explicitly requests them.

## Linux Installer

The deployable single file is `scripts/sqcsagent.py`. Install it on Linux with only the controller address and port:

```bash
sudo python3 sqcsagent.py install CONTROLLER_HOST CONTROLLER_PORT
systemctl status sqcsagent
```
