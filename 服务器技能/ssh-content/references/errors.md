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
