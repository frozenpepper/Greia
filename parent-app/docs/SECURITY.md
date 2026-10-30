# Security notes

## Current boundary

Greia Parent authentication is now a two-stage model:

1. a browser that has no device identity submits the Greia Parent password to `POST /api/v1/pairing/bootstrap`;
2. after successful local verification, Greia returns a random per-device credential used for normal API requests.

The Parent password is never persisted by the browser. Per-device credentials are scoped to the selected Greia and can be revoked independently.

The installed API uses a device-owned self-signed HTTPS certificate on the LAN and reports `transport_security = "self-signed-https"`; a loopback-only HTTP listener remains available for on-device recovery. Browsers normally warn on the self-signed certificate. Installed browser/certificate click-through and the ordinary-family identity lifecycle remain acceptance items; do not expose the port to the internet.

## Client invariants

- No third-party JavaScript executes in the application origin.
- API values are inserted with `textContent` / DOM properties, not `innerHTML`.
- No password or API credential is included in URLs.
- The Parent password is submitted only for bootstrap and is never written to browser persistence.
- The persistent device credential is scoped by Greia origin/device selection.
- The retired shared pairing token is not accepted, stored, or emulated by the client.
- There is no generic command, path, SSH, package-manager, or arbitrary-file API surface in this client.
- Device revocation is a first-class UI operation.

## Server-side bootstrap requirements

The normative Greia server must:

- verify bootstrap passwords only through the canonical `MainCredential` authority;
- persist only the password digest, with restrictive file permissions;
- rate-limit failed password attempts with bounded state;
- issue a fresh high-entropy per-device credential after successful verification;
- keep normal management endpoints bearer-device-credential-only;
- reject legacy shared-token headers/cookies/routes rather than retaining a compatibility backdoor;
- support independent device revocation.

## Production transport prerequisite

Before ordinary-family release treats remote Parent authentication as secure, the self-signed certificate lifecycle and installed browser acceptance must be completed, and the initial default Parent password must be changed or gated at first boot. The transport must prevent credential interception and endpoint impersonation without turning the Parent workflow back into a hidden-token or Linux-administration procedure.

If the future transport provides a stronger same-origin/session mechanism than browser-persisted bearer credentials, the client can migrate while preserving the API's password-bootstrap and independently revocable-device semantics.
