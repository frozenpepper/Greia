# Privacy

Greia is designed to work without an account, advertising, analytics or a
cloud service. This page describes the current source and the intended
ordinary-family behaviour. It is not a substitute for testing a specific
release image.

## Child and family data

- Profiles, saves, creations, settings, progression and Parent policy live on
  the Greia computer under `/var/lib/greia-profiles` and the profile-scoped
  Activity-data roots. They are not uploaded by the platform.
- The Greia Shell and built-in Activities do not include telemetry, a general
  web browser, advertising identifiers or engagement tracking.
- Logs and caches stay on the device, are bounded, and are not a remote
  analytics channel.

## Greia Parents

Greia Parents is served by the Greia computer on the local network and uses a
self-signed HTTPS certificate. Pairing credentials are stored by the browser
you use for that device and are scoped to that device origin. The Parent app
does not send management data to a Greia cloud service.

The current HTML client and its local development/discovery host are part of
the Greia Parents source repository. A standalone local host searches the LAN
for Greia devices; it does not proxy arbitrary destinations.

## Updates and optional network use

An installed Greia may contact a configured update source to check for or
download a system or application update. Release images must state the active
update source. Activities may declare optional network capability, but access
is denied by default and mediated by the platform; ordinary Activities do not
receive unrestricted network or device access.

## Website and project source

The Greia project website is static: it sets no analytics, advertising or
tracking cookies and loads no third-party font or script service. GitHub hosts
the source repository and its own metadata under GitHub's policies.

## Questions

Privacy questions and reports can use the repository's issue tracker for
non-sensitive matters. Security-sensitive reports should follow
[SECURITY.md](SECURITY.md).
