# Integration harnesses

These need root, a real block-device target, and minutes of wall clock. They are
deliberately **not** part of `make verify` or the unit suite. Run them by hand
when a change touches the privileged install path.

## `install_leg_harness.sh`

Runs the six operations the privileged half performs on `EXECUTE` — payload
unpack, `update-initramfs`, `update-grub`, the apt leg, `grub-install`, and
`grub-script-check` — inside a transient unit whose directives are taken from
the shipped `greia-install-transaction.service`, against a partitioned loop disk
standing in for the appliance's `/dev/sda`.

It exists because that whole path had never been executed end to end off
hardware. Every capability and limit in the unit was previously chosen from a
single appliance error message, which cost four hardware cycles to discover and
left two failures still unreached. Each value in the unit is now isolated by
removing it and re-running these legs, so none is granted on plausibility.

Fidelity notes, each learned from a false failure:

- The target must be prepared **outside** the sandbox and mounted **inside** it.
  `ProtectSystem=strict` remounts whatever was already mounted, so a target
  mounted beforehand is read-only; the real service mounts `/dev/sda` itself.
- The disk must be **partitioned**, so `grub-install` has a real gap to embed
  into. A whole-disk filesystem makes it refuse with a blocklist error.
- The unit's `RestrictSUIDSGID` is a mount-namespace property, and
  `SystemCallArchitectures=native` resolves against the *host* CPU. On an x86_64
  host running an i386 payload the latter kills the chroot with `SIGSYS`; the
  appliance is natively i686, where it is harmless.
- `apt` needs a real repository: a `.deb` alone is not enough, the pool needs a
  `Packages` index.
- `udev` cannot run under `RestrictAddressFamilies=AF_UNIX`, so the partition
  node is created by the host-side setup.

Prerequisites: the payload squashfs, `dpkg-scanpackages`, and permission to
create loop devices.
