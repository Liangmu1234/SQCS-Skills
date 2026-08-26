---
name: ipmitool
description: Operate authorized server BMCs with ipmitool for IPMI power, sensors, SEL, FRU, SOL, user, LAN, and H3C HDM OEM workflows. Use for IPMI requests; use the redfish skill for Redfish REST requests.
metadata:
  short-description: Manage BMCs with ipmitool
---

# ipmitool

Use this skill only for systems the user is authorized to manage. A BMC session has physical-server-level privilege: it can power-cycle the host, expose the console, mount media, change accounts, and alter management networking.

## Safety and secret handling

- Keep BMCs on an isolated management network or approved jump host. Do not expose IPMI or a BMC to the public internet.
- Prefer `lanplus` (IPMI 2.0) over `lan`. Use an explicitly supported, non-zero cipher suite. Do not use cipher suite 0. Cipher IDs are device-specific; do not assume cipher 17 works on every vendor.
- Never put a password, token, or new user password in a command argument, source file, committed script, or chat transcript. Use the user's approved secret store or a non-echoing prompt. `-E` reads the existing session password from `IPMI_PASSWORD`; it does not safely supply a new account password.
- Clean up secrets even when a command fails or is interrupted. In Bash, use a trap around the whole operation:

```bash
read -r -s -p 'BMC password: ' IPMI_PASSWORD
printf '\n'
export IPMI_PASSWORD
cleanup() { unset IPMI_PASSWORD; }
trap cleanup EXIT INT TERM
```

- Do not print the environment, command line, or verbose output containing credentials. Redact passwords, tokens, and private management addresses from reports.
- Before any write, show the exact target, command, and expected impact and obtain explicit confirmation. This applies to power changes, SEL clearing, SOL disconnect, account changes, cipher/network changes, BMC reset, RAID, BIOS, firmware, and OEM raw commands. For a fleet, confirm the complete host list and action scope.

## Locate the bundled Windows binary

The package contains `scripts/ipmitool-win/`. Resolve that path relative to the installed skill directory; never use a user-specific path such as `C:\Users\...\.workbuddy\...`.

```text
<skill-root>/scripts/ipmitool-win/ipmitool.exe
```

Prefer a centrally managed, signed/system-packaged ipmitool. The bundled executable and DLLs are a fallback only: verify their provenance and SHA-256 before production use. Do not treat an unsigned binary or its legacy crypto DLLs as trusted merely because it is inside the skill ZIP.

## Connection preflight

First confirm the intended BMC address and that the management path is approved. Check TCP/UDP reachability with the tool available on the execution host:

```powershell
# Windows PowerShell 5+; one bounded check
Test-NetConnection -ComputerName <bmc-ip> -Port 623 -InformationLevel Quiet
```

```bash
# Linux or Bash with a working timeout utility
timeout 3 bash -c 'cat < /dev/null > /dev/tcp/<bmc-ip>/623'
```

Do not loop indefinitely on a failed network check. A failed probe is a network/authentication problem to report, not a reason to retry without a bound.

For a normal read-only request, start with:

```bash
ipmitool -I lanplus -H <bmc-ip> -U <user> -E -C <supported-cipher> -N 5 -R 2 mc info
```

Check the exit status and distinguish network failure, authentication failure, unsupported cipher, and BMC completion-code errors.

## H3C platform and HDM identification

Apply this section only when the target is H3C. Do not infer a generation from a numeric firmware revision alone.

1. Run both read-only commands and verify they succeed:

   ```bash
   ipmitool -I lanplus -H <bmc-ip> -U <user> -E -C <supported-cipher> mc info
   ipmitool -I lanplus -H <bmc-ip> -U <user> -E -C <supported-cipher> fru print
   ```

2. Confirm the H3C manufacturer ID and inspect `Firmware Revision`/BMC product version from `mc info` and `fru print`. Use the explicit HDM/HDM2/HDM3 label when the device reports one.

3. Use the platform model from the built-in FRU as a cross-check, but treat blank or inconsistent FRU data as untrusted. If the platform and firmware family disagree, stop and inspect the asset record and the device manually.

4. Select the matching manual before any H3C OEM command:

   - G3/G5 with HDM: `references/H3C-G3G5-HDM-IPMI-基础命令参考手册-6W104.pdf`
   - G6 with HDM2: `references/H3C-G6-HDM2-IPMI-基础命令参考手册-6W104.pdf`
   - G6/G7 with HDM3: `references/H3C-G7-HDM3-IPMI-基础命令参考手册-6W103.pdf`

5. In the selected manual, verify NetFn, command, subcommand, byte order, request length, response layout, supported firmware, and permission module. Copy a documented example rather than reconstructing a raw command from memory. Do not assume the LAN channel or interface number is 1.

6. After execution, validate the IPMI completion code and any H3C manufacturer-ID response exactly as defined by that manual. A familiar-looking response is not proof that a write succeeded.

## Common read-only operations

Use the connection options appropriate to the target and keep the output bounded:

```bash
ipmitool ... chassis power status
ipmitool ... mc info
ipmitool ... sensor list
ipmitool ... sdr
ipmitool ... sel info
ipmitool ... sel list
ipmitool ... fru print
ipmitool ... user list <channel>
ipmitool ... lan print <channel>
ipmitool ... sol info
ipmitool ... sol payload status
```

Discover the active LAN channel and SOL channel from the device instead of assuming channel 1. For in-band Linux access, confirm the required `ipmi_*` kernel modules are present; do not hide a failed `modprobe` with `|| true`.

## Mutating operations

Treat these as change operations, not examples to run automatically:

```bash
# Require explicit confirmation first.
ipmitool ... chassis power soft
ipmitool ... chassis power off
ipmitool ... chassis power cycle
ipmitool ... chassis power reset
ipmitool ... mc reset cold
ipmitool ... chassis bootdev pxe
ipmitool ... sol deactivate
ipmitool ... sel clear
```

Use graceful shutdown before a hard power action where possible. Before clearing SEL, export or summarize the relevant entries. Before changing LAN settings, record the current configuration and warn that the session may be disconnected. Before changing accounts or privileges, verify a replacement administrator works and preserve a recovery path.

For cipher hardening, first query the supported cipher suites and the current privilege mapping:

```bash
ipmitool ... channel getciphers ipmi <channel>
```

`channel setcipher ... readonly` is not equivalent to disabling cipher 0. Use the vendor-supported disable operation, then re-query the mapping and report the result. If the BMC cannot disable cipher 0, stop and report the residual risk instead of claiming hardening succeeded.

## H3C OEM raw commands

Use OEM raw commands only after the H3C identification and manual lookup above. The manual is authoritative for the command family, manufacturer ID bytes, subcommand, reserved fields, length encoding, data layout, response parsing, firmware support, and permissions. The following is only a shape reminder, not a command template:

```text
ipmitool ... raw <netfn> <cmd> <manual-defined-data-bytes...>
```

Important H3C differences include G3 versus G5+ management-interface enumerations, HDM2 versus HDM3 support, AMD versus Intel BIOS enumerations, permission modules, and raw-message size/transport limits. Never guess a byte or copy a command from another generation. Require a second confirmation for any OEM write, RAID, BIOS, power, firmware, virtual-media, or network operation.

## Reporting

Summarize rather than dumping raw output. Include session result and failure class, BMC/IPMI version, power state, out-of-threshold sensors, recent SEL severity/timestamps, and every configuration or control change. Explicitly flag any power, reset, SEL, account, network, firmware, or OEM action. Redact passwords, tokens, and sensitive inventory values.

## References

- H3C manuals: `references/`
- ipmitool source: <https://github.com/ipmitool/ipmitool>
- ipmitool man page: <https://man.archlinux.org/man/extra/ipmitool/ipmitool.1.en>
- IPMI v2.0 specification: <https://www.intel.com/content/www/us/en/products/docs/servers/ipmi/ipmi-second-gen-interface-spec-v2-rev1-1.html>
- CVE-2013-4782: <https://nvd.nist.gov/vuln/detail/CVE-2013-4782>
