# Authentication and targets

Shared state is stored under `${CODEX_HOME}/state/ssh-content`, or `~/.codex/state/ssh-content` when `CODEX_HOME` is unset. `targets.json` contains aliases, hosts, ports, users, identity paths, remote shell capability, last success time, and connection-reuse capability. It never contains passwords.

Resolution order is: shared targets, OpenSSH config, an explicitly configured legacy Markdown registry, then the raw target.

Authentication order is: explicit key, recorded dedicated key, OpenSSH-configured key, SSH agent, then process-scoped `CODEX_SSH_PASSWORD`. When password authentication succeeds, bootstrap is automatic unless `-NoBootstrap` was specified.

The dedicated key is `~/.ssh/codex_ssh_content_ed25519`. Public-key installation appends only when the exact key is absent and applies `700` to `.ssh` and `600` to `authorized_keys`.

Use `-NoBootstrap` when public-key installation is not authorized. Passwords are never persisted to Windows Credential Manager.
