---
name: redfish
description: Operate authorized server BMCs through the Redfish REST/JSON API over HTTPS for discovery, power, sensors, inventory, virtual media, accounts, firmware, and tasks. Use for Redfish requests; use the ipmitool skill for IPMI commands.
metadata:
  short-description: Manage BMCs with Redfish
---

# Redfish

Use this skill only for systems the user is authorized to manage. Redfish credentials can control the physical server, including power, console, virtual media, accounts, and firmware.

## Safety and transport

- Keep the BMC on an isolated management network or approved jump host. Do not expose it to the public internet.
- Use HTTPS and verify the BMC certificate with its CA bundle or the operating-system trust store by default.
- Do not make `verify=False`, `-k`, weak cipher suites, or HTTP the default. A temporary legacy-TLS exception requires explicit approval, a private management path, a bounded scope, and a warning in the report. Prefer upgrading the BMC or installing its CA.
- Never put a password, token, or credential-bearing URI in a command argument, source file, committed script, terminal transcript, or report. Do not print response headers.
- Prefer one Redfish session for multiple requests and delete it in `finally`, including on errors. Do not create sessions repeatedly without cleanup.
- Read first. Before any state-changing `POST`, `PATCH`, or `DELETE`, show the exact target, request body, expected impact, and recovery plan, then obtain explicit confirmation. This is mandatory for power, accounts, virtual media, configuration, diagnostics, and firmware.
- Redact passwords, tokens, certificate material, serial numbers, and private management addresses. SDS/diagnostic archives can contain sensitive logs and inventory.

## Safe Python session pattern

Inject credentials through an approved secret store or non-echoing launcher. Do not log the request body or response headers.

```python
import os
from urllib.parse import urljoin
import requests

BMC = os.environ["REDFISH_BMC"]
USER = os.environ["REDFISH_USER"]
PASSWORD = os.environ["REDFISH_PASSWORD"]
BASE = f"https://{BMC.strip('/')}/"

session = requests.Session()
ca_bundle = os.environ.get("REDFISH_CA_BUNDLE")
if ca_bundle:
    session.verify = ca_bundle

def absolute(ref):
    if ref.startswith(("https://", "http://")):
        return ref
    return urljoin(BASE, ref.lstrip("/"))

session_url = absolute("/redfish/v1/SessionService/Sessions")
created = session.post(
    session_url,
    json={"UserName": USER, "Password": PASSWORD},
    timeout=15,
)
created.raise_for_status()
token = created.headers.get("X-Auth-Token")
location = created.headers.get("Location")
if not token or not location:
    raise RuntimeError("BMC did not return a token and Location")
session.headers["X-Auth-Token"] = token

try:
    root = session.get(absolute("/redfish/v1/"), timeout=15)
    root.raise_for_status()
    service_root = root.json()
finally:
    session.delete(absolute(location), timeout=10).raise_for_status()
```

If session creation fails, report the HTTP status and a redacted error body. If cleanup fails, report that the BMC session may remain active. Do not use `curl -u admin:password`, `curl -D -`, or any command that prints a token. In Windows PowerShell, call `curl.exe` rather than the `curl` alias.

## Discover resources; do not guess IDs

Collection member IDs and action targets vary by vendor. Do not hard-code `Systems/1`, `Managers/1`, `Chassis/1`, `CD1`, or `Tasks/1` in a generic workflow.

```python
def get_json(path_or_url):
    response = session.get(absolute(path_or_url), timeout=15)
    response.raise_for_status()
    return response.json()

def member_urls(collection):
    return [absolute(member["@odata.id"]) for member in collection.get("Members", [])]

service_root = get_json("/redfish/v1/")
system_collection = get_json(service_root["Systems"]["@odata.id"])
system_urls = member_urls(system_collection)
if not system_urls:
    raise RuntimeError("Redfish service has no ComputerSystem member")
system_url = system_urls[0]
system = get_json(system_url)
```

Follow service-root and resource links. If there are multiple systems, chassis, managers, or nodes, ask which is in scope or report all read-only members. Check `Actions`, `@Redfish.AllowableValues`, and `@odata.type` before using an action or field.

## H3C HDM/HDM2/HDM3 workflow

Use this section only for H3C. The supplied manuals are:

- G3/G5 HDM: `references/H3C-G3G5-HDM-Redfish-参考手册-6W104.pdf`
- G6/G7 HDM2/HDM3: `references/H3C-G6G7-HDM2HDM3-Redfish-参考手册-6W104.pdf`

1. Discover the manager and system links from the service root; do not assume an ID.
2. Use the explicit `FirmwareVersion`, product model, `@odata.type`, and the manual's supported-version matrix. Do not map an unlabelled numeric firmware value to HDM/HDM2/HDM3 by an arbitrary threshold.
3. For an H3C OEM operation, verify the complete URI, method, request fields, enum values, permissions, firmware support, response schema, and `If-Match` requirement from the matching manual.
4. Accept a successful HTTP status only after parsing the response. If `Oem.Public.CompletionCode` is present, require it to be `0`; do not require that vendor extension on every standard Redfish response. Preserve `@Message.ExtendedInfo` on errors.
5. For `401`/`403`, distinguish user-role permission from interface/module permission. Do not retry a denied write with a more privileged account without authorization.

Do not globally install a `CERT_NONE`/SECLEVEL-0 adapter, silently downgrade the endpoint to HTTP, or send credentials in an image/transfer URL. Firmware and diagnostics should use an approved, integrity-checked HTTPS/SFTP path.

## Power operations

Read the current state first:

```python
system = get_json(system_url)
print(system.get("PowerState"))
```

For a reset, discover the action target and allowable values, then ask for confirmation before posting:

```python
action = (system.get("Actions") or {}).get("#ComputerSystem.Reset")
if not action or "target" not in action:
    raise RuntimeError("ComputerSystem.Reset is not advertised")
allowed = action.get("ResetType@Redfish.AllowableValues")
reset_type = "GracefulRestart"
if allowed and reset_type not in allowed:
    raise RuntimeError(f"ResetType not allowed: {reset_type}")

# Obtain confirmation for this exact system_url and reset_type here.
response = session.post(
    absolute(action["target"]),
    json={"ResetType": reset_type},
    timeout=30,
)
response.raise_for_status()
```

Prefer graceful actions. Treat `ForceOff`, `ForceRestart`, `PowerCycle`, and `Nmi` as disruptive and flag them explicitly. Do not PATCH a guessed boot path; inspect the resource and allowable values first.

## Sensors, thermal, and power

Discover the links exposed by the selected chassis. Modern implementations may expose `Sensors`, `ThermalSubsystem`, and `PowerSubsystem`; older implementations may expose `Thermal` and `Power`. `Thermal` and `Power` are deprecated in favor of the subsystem resources, not because every sensor is replaced by one universal `Sensors` schema.

```python
chassis = get_json(chassis_url)
for key in ("Sensors", "ThermalSubsystem", "PowerSubsystem", "Thermal", "Power"):
    link = chassis.get(key)
    if isinstance(link, dict) and "@odata.id" in link:
        print(key, absolute(link["@odata.id"]))
```

Follow each collection's `Members` links and use the fields advertised by that resource. Do not assume every sensor has `Reading`; vendors may expose `ReadingCelsius`, `ReadingVolts`, `ReadingWatts`, thresholds, or only `Status`.

If using jq, quote the OData key correctly:

```bash
jq -r '.Members[]["@odata.id"]'
```

## Inventory and virtual media

Follow `Processors`, `Memory`, `Drives`, `Storage`, `NetworkInterfaces`, and `VirtualMedia` links from the selected resource. The link may be under `ComputerSystem` or `Manager`; use the advertised link rather than a guessed path.

For virtual media, discover the collection and selected member, check `Inserted`, current `Image`, `Actions`, and allowable values, verify the image source and integrity, and obtain confirmation before insert, eject, boot override, or reset. Never put credentials in the image URI. Eject media and clear one-time boot override when the approved task is complete.

## Accounts, configuration, and firmware

Treat account creation, role changes, deletion, network changes, BIOS changes, and firmware operations as high-risk writes. Before execution:

- confirm the exact resource and current configuration;
- use least privilege and verify a tested recovery/admin path;
- for firmware, verify vendor signature/hash, compatibility, maintenance window, and rollback plan;
- inspect the advertised action target and request schema instead of guessing `UpdateService.SimpleUpdate` or a task URI;
- obtain explicit confirmation immediately before the write.

For `202 Accepted`, use the response `Location` or task reference, normalize absolute versus relative URIs, and poll with a bounded deadline. Stop on `Completed`, `Cancelled`, `Exception`, or `Killed`; report the final state and status. Do not assume task ID 1.

Never delete a default administrator merely because a replacement was created. Authenticate successfully with the replacement, verify permissions, record the change, and obtain explicit confirmation for deletion.

## H3C SDS diagnostic collection

Use the exact URI, path restrictions, role, and fields from the H3C manual. A safe implementation must check the initial response, capture the task reference and file name without printing headers, poll with a bounded deadline, download with `raise_for_status()` and `iter_content()`, reduce `Content-Disposition` to a basename, reject path traversal and unsafe archive members, verify size/hash when available, and protect/redact/delete the archive according to the retention policy.

`PercentComplete` may be absent or unknown on H3C devices. Use `TaskState` as the completion signal and do not mark collection successful merely because the response was `202`.

## Batch and reporting

For multiple BMCs, use a bounded worker count, per-host timeout, explicit host allowlist, and separate result records. Never pass a fleet password as a positional shell argument. Abort or pause on repeated authentication failures, unexpected models, or write errors unless a recovery policy was approved.

Report HTTPS/authentication result, selected resource identifiers, firmware version, power state, sensor abnormalities, inventory differences, virtual-media state, task state, and every account/configuration/firmware change. Redact all credentials and tokens.

## References

- H3C manuals: `references/`
- DMTF Redfish specification: <https://redfish.dmtf.org/schemas/DSP0266_1.15.0.html>
- DMTF resource and schema guide: <https://redfish.dmtf.org/schemas/v1/DSP2046_2025.3.html>
- DMTF session authentication: <https://www.dmtf.org/sites/default/files/standards/documents/DSP2060_1.0.0.pdf>
- NVIDIA DGX Redfish supplement: <https://docs.nvidia.com/dgx/dgxh100-user-guide/redfish-api-supp.html>
