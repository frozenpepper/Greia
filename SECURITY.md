# Security policy

Greia is built for young children, so safety bugs matter even before the
first release. Thank you for taking the time to report one.

## Supported versions

Greia has no supported binary release yet. Reports against the current
`main` branch are welcome.

## How to report

Please report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/frozenpepper/Greia/security/advisories/new)
("Report a vulnerability" on the repository's Security tab). Do not open a
public issue for a security problem.

Include what you found, how to reproduce it, which commit you tested and
where it ran (desktop, Simulator, VM or which device). This is a small
project: we will acknowledge reports as soon as we can and keep you informed
while a fix is prepared.

## What we especially want to hear about

- any way for a child to reach a Linux shell, terminal, desktop, login
  prompt or file manager from the normal child path;
- an Activity escaping its sandbox, reading or writing another profile's or
  another Activity's data, or gaining raw device access;
- an Activity hiding, covering or intercepting the platform Home control;
- bypasses of Parent authentication, device pairing or Parent-only settings;
- removable media that runs code or is offered as an install target without
  verification;
- the installer writing to a disk other than the verified, confirmed target;
- system updates that apply unverified content or break rollback;
- child data leaving the device, or leaking into logs, without the parent's
  knowledge.

## Known, documented limitations

These are tracked release blockers rather than undisclosed vulnerabilities,
though details that make them worse are still welcome:

- **Developer images** deliberately enable SSH with a shared development
  login so the team can test devices remotely. Base and release images keep
  that account locked and SSH off.
- **The initial Parent password is a known development default (`greia`).**
  The browser login no longer advertises it, but a fresh technical-preview
  install will accept it until the parent changes it under This Greia. Change
  it before connecting the device to a shared or untrusted network. An
  ordinary-family release still needs a first-boot change/setup gate.
- **Parent pairing and transport** use a device-owned self-signed HTTPS
  certificate on the local network; browsers may warn on first connection.
  Browser/device click-through acceptance and ordinary-family recovery wording
  are still outstanding (see
  `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`).
- **The production display/session architecture** still runs on a
  provisional Xorg compatibility backend.
