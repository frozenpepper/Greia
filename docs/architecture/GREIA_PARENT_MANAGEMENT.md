# Greia Parent Management Architecture

**Status:** living design synthesis subordinate to ADR 0012 and ADR 0022  
**Date:** 2026-08-17  
**Reviewed:** 2026-09-02  
**Implementation phase:** API/client foundation in progress; full privileged management remains R12

## 1. Architectural intent

Greia Parents is a client/server subsystem, not a privileged webpage.

The stable boundary is the Greia Parent API. The first client is a dependency-light responsive HTML application served locally by Greia. A future mobile or desktop application consumes the same protocol.

```text
                    same API contract
        ┌──────────────────┴──────────────────┐
        │                                     │
Greia-served HTML                       native parent app
        │                                     │
        └───────────────┬─────────────────────┘
                        ▼
                 Greia Parent API
                 (unprivileged)
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
 Profile/Progress   HAL/settings    Package/Backup/
 platform services  services        Update services
       │                │                │
       └──────────────┬─┴────────────────┘
                      ▼
          typed privileged broker
            only where required
                      │
                      ▼
               Linux adapters
```

The network API must never become a parallel implementation of profiles, package installation, backup, networking, audio, or update logic.

## 2. Process/authority boundary

`greia-parent.service` runs as `greiapanel` with a strict systemd sandbox.

This service owns:

- protocol parsing;
- authentication/paired-client identity;
- read-only status assembly;
- calls into existing unprivileged Greia stores/services;
- serving the small HTML client;
- typed requests to future privileged services.

It does not own root authority.

The installed composition is `src/greia_parent/production_api.py`. It must fail closed when a requested mutation cannot be completed under the service's actual authority. In particular, detecting a real IWD service is not by itself enough to advertise writable network management when the sandboxed process cannot persist the required IWD state.

The future privileged parent broker should be a separate root-owned service reached over a private local IPC channel. Its command vocabulary is narrow and semantic.

Good:

```text
enable_ssh(public_key)
disable_ssh()
install_activity(staged_package_handle)
set_audio_volume(0.5)
reboot()
```

Rejected:

```text
run_command("...")
run_argv([...])
write_file("/etc/...")
sudo(...)
apt(...)
```

## 3. Client identity and pairing state

Persistent parent clients are independent security principals.

Stored state contains:

```text
device_id
display_name
created_at
credential verifier/hash
```

It does not contain the raw bearer credential.

A credential is returned only when issued.

The initial store is deliberately bounded to a small maximum number of paired clients and uses atomic replacement.

Future pairing state adds bounded short-lived challenges:

```text
challenge_id
expires_at
attempt budget
requesting device label
local approval state
```

Challenges are transient and are not durable household credentials.

## 4. Discovery

`avahi-daemon` advertises:

```text
service: _greia-parent._tcp
port:    8766
TXT:     api=1
TXT:     path=/api/v1
TXT:     product=greia
```

No token, profile information, child name, machine serial, or other secret is advertised.

A future friendly device name may be advertised if it is parent-configurable and privacy-reviewed.

## 5. Protocol layering

### Discovery metadata

Unauthenticated metadata is intentionally tiny:

```text
GET /api/v1/meta
```

It tells a client that the service is Greia Parents, which API version/base it exposes, and that pairing is required.

### Authenticated resources

The versioned API exposes semantic resources for:

- system/health;
- profiles;
- Activity inventory;
- hardware/settings;
- progress;
- parent devices;
- future operations.

### Capability negotiation

The API index reports whether optional management families currently exist **and are usable under the active composition/authority**.

This provides one forward-compatible client strategy:

```text
client discovers API v1
→ authenticates
→ reads capability map
→ renders only supported controls
```

No architecture/model-specific branching is required in clients.

A capability must not become `true` merely because a lower-level Linux service can be detected. If the current Greia process cannot safely complete the semantic operation, advertise it as unavailable until the proper backend/broker exists.

## 6. HTML client

The web application is static/dependency-free HTML/CSS/JavaScript generated/served by Greia.

It uses browser `fetch()` against `/api/v1`.

The page contains no Linux-specific management implementation. This is an architectural test: if a feature cannot be represented cleanly in the Parent API, it is not ready to become a native-app feature either.

The legacy server-rendered page may remain temporarily as `/legacy` during migration and troubleshooting.

## 7. Long-running operations

Simple profile/settings mutations are synchronous.

Operations with meaningful time/failure/recovery phases must use operation resources, for example:

```text
POST /api/v1/activities/install
→ 202
{
  "operation_id": "op_...",
  "state": "validating"
}

GET /api/v1/operations/op_...
→ {
  "state": "installing",
  "progress": ...
}
```

The operation object is owned by the corresponding Greia platform service. The Parent API only represents it.

This is required for:

- Activity install/update;
- backup/restore;
- OS/runtime update;
- potentially network transitions where disconnect is expected.

## 8. Activity management boundary

The current Parent source lists installed Activities through the trusted Activity Registry and includes bounded package install/remove composition behind explicit owner/developer capability enablement.

That does not make the HTTP server a package authority. Package validation/activation remains owned by the Greia platform package service, and provisional Parent transport/capability policy remains fail closed by default.

The intended boundary is:

```text
Parent API upload/import
→ bounded staging
→ Activity package verifier/manager
→ typed operation/state boundary as the lifecycle matures
→ atomic activation/rollback
```

The HTTP server does not unpack arbitrary archives directly into `/opt/greia-os/activities`.

Full ecosystem/release acceptance remains tracked by the active architecture/release plans; presence of the source path is not itself closure evidence.

## 9. Settings boundary

The Parent API talks in semantics:

```text
mouse_speed
touchpad_speed
tap_to_click
natural_scrolling
resolution
volume
mute
network identity
```

The HAL/current adapter determines how those settings reach the machine.

No client sees `xinput`, `xrandr`, ALSA, iwd, sysfs, or future direct-graphics backend details.

## 10. SSH boundary

SSH is a maintenance capability, not a dependency of Greia Parents.

Normal image:

```text
openssh-server absent/off
SSH host keys absent until deliberately enabled
Parent API available independently
```

Future explicit enable:

```text
parent client
→ maintenance.ssh capability
→ typed Parent API request
→ privileged maintenance broker
→ validate key/policy
→ create host keys if needed
→ install/enable constrained sshd state
→ return semantic connection status
```

Developer remote SSH remains a separate image/profile feature.

## 11. Secure transport migration

Current HTTP is development-only.

The protocol intentionally avoids coupling API semantics to HTTP plaintext so authenticated TLS can replace the transport without changing resources.

Production design must address:

- device certificate/key generation;
- how pairing authenticates the Greia endpoint;
- certificate rotation/recovery;
- browser trust UX for the local HTML client;
- native-client pinning;
- reinstall/device-identity reset behavior.

No production credential should traverse an unauthenticated plaintext channel.

## 12. Resource budget

The parent service runs on the C0 floor. Initial design therefore keeps:

- stdlib HTTP server;
- single request thread;
- bounded JSON requests;
- bounded credential file;
- static small web client;
- no database solely for pairing;
- no write on every authenticated request;
- no frontend framework dependency.

These are implementation choices, not API requirements. A future implementation may change them only with measured benefit and acceptable resource/security cost.

## 13. Incremental implementation map

Foundation now:

```text
protocol constants/resource index
per-device credential store
API-v1 facade over profile/hardware/package/update/settings services
explicit installed production composition with fail-closed capabilities
on-device Parent Settings Panel via held key chord (s+t for 5s)
real-IWD discovery/backend with management advertised only when current authority can use it
bounded Activity package install/remove path behind explicit capability policy
SSH maintenance API surface through current platform service boundary
Activity inventory
mDNS advertisement
HTML API client
```

Still required / not yet ordinary-family release complete:

```text
Greia-screen pairing challenge + QR/code + Allow/Deny
authenticated encrypted transport
typed privileged broker for operations requiring Linux/root authority
ordinary-family Wi-Fi mutation through that typed authority boundary where direct unprivileged IWD is insufficient
full Activity ecosystem/package release acceptance
backup/restore through the planned platform service
complete privileged audio/maintenance operations through typed services
operation resources for long-running mutations
native client if/when justified
```

This foundation does not close R12 and does not change R7 as the primary blocking platform phase.
