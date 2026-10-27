# Old-release A/B stage refusal — analysis and next path

Date: 2026-10-27 · Status: **ANALYSIS ONLY; no new runtime evidence; do not
retry the frozen guest; Session 04 OPEN**

Input result:
[`2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md`](2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md)
Evidence root:
`/var/tmp/greia-ab-old-release-stage-78f07861c0ddfad6ed51fb2e1c564d3f95e70115-20261027T004919Z/`

## Observed facts

- The one `update-stage` boot was executed from reviewed host source
  `78f07861` against the frozen `1275` guest and verified accepted-A/bundle.
- The installed updater returned `ERROR`/`REFUSED`:
  `inactive-slot filesystem is unavailable: block topology observation failed:
  slot device capacity is unobservable: sda2`.
- `phase-result.json` captured the response and an empty `cause_chain`; the
  service remained active with no other journal error. A stayed accepted
  0.13.0; B has no release identity; PERSIST status is still `received`.
- Input/bundle hashes were unchanged; collector cleanup was ok; no arm or B
  boot ran. `command.exit`/`final.exit` are 1 because staging was refused.

## Code path from the captured reason

In the reviewed `src/greia_platform/system_updates.py`:

1. `_production_filesystem_factory` resolves the inactive slot and calls
   `observe_topology()`. Any `BlockSlotError` is wrapped as
   `inactive-slot filesystem is unavailable: …`.
2. `block_slots.resolve_slot_device` calls `observe_topology()` and wraps a
   failure as `block topology observation failed: …`.
3. `_observe_production_topology` / `_probe_role_fact` probes **both** layout
   roles and calls `_block_node_size_bytes(node)` for each.
4. `_block_node_size_bytes` first tries a hard-coded `fcntl.ioctl` request
   `0x80081272` with an 8-byte buffer, then falls back to
   `blockdev --getsize64 -- <node>`. If both fail it raises
   `slot device capacity is unobservable: <node.name>`.

`sda2` is the active A partition; the refusal is raised while probing that
role, before the inactive B device write. The code path has two independent
failure points, so the captured reason alone does not distinguish them.

## Hypotheses to test, cheapest first

1. **i386 ioctl width (strong candidate).** `BLKGETSIZE64` is
   `_IOR(0x12,114,size_t)`. On i386, `size_t` is 4 bytes; `0x80081272` is the
   64-bit encoding. If the guest kernel does not compat-translate that request,
   the primary probe raises and falls through. The fallback may then fail
   because `blockdev` is absent/blocked. This is plausible because the source
   tests run on x86_64 hosts, where `0x80081272` is correct.
2. **`blockdev` fallback unavailable.** The service runs as root with
   `PrivateDevices=no`, but the minimized image may not contain the
   `blockdev` executable, or the subprocess/PATH/sandbox may fail. The primary
   ioctl would then be the only working path.
3. **Device/sandbox denial.** The unit has `PrivateDevices=no`,
   `ProtectSystem=strict`, `ProtectKernelTunables=yes`, and a capability set
   without `CAP_SYS_RAWIO`; `blockdev`/ioctl may be denied even though the
   nodes exist. The error is on the active A node, not the inactive B, so a
   device-policy restriction is possible but would not by itself explain why
   the layout PARTUUID map resolved `sda2`.
4. **The topology proof is over-broad.** Only the inactive B slot is written;
   probing active A capacity may be unnecessary. Do not weaken the layout
   proof without review.

## Recommended probe (read-only; no stage boot)

Run on the **frozen clone** or an equivalent guest, before another stage
attempt, and preserve the output:

```bash
id
ls -l /dev/sda /dev/sda2 /dev/sda3
readlink -f /dev/sda2 /dev/sda3
cat /sys/class/block/sda2/size /sys/class/block/sda3/size
command -v blockdev || true
blockdev --getsize64 /dev/sda2 /dev/sda3; echo "blockdev_rc=$?"
lsblk -b -o NAME,SIZE,TYPE,PARTUUID,MOUNTPOINTS
systemctl show greia-system-update.service -p \
  User,Group,PrivateDevices,DevicePolicy,DeviceAllow,CapabilityBoundingSet,AmbientCapabilities,ProtectSystem,ProtectKernelTunables,NoNewPrivileges
python3 - <<'PY'
import fcntl, os, struct
for node in ("/dev/sda2", "/dev/sda3"):
    for req in (0x80081272, 0x80041272):
        try:
            fd = os.open(node, os.O_RDONLY)
            raw = fcntl.ioctl(fd, req, b"\0" * 8)
            print(node, hex(req), "OK", struct.unpack("Q", raw)[0])
        except OSError as exc:
            print(node, hex(req), type(exc).__name__, exc)
        finally:
            try: os.close(fd)
            except Exception: pass
    with open("/sys/class/block/%s/size" % os.path.basename(node)) as f:
        print(node, "sysfs", int(f.read()) * 512)
PY
```

This distinguishes the i386 ioctl encoding, the `blockdev` fallback, and the
service device policy without another stage request.

## Fix direction after the probe

- Prefer a bounded **sysfs capacity fallback** in `_block_node_size_bytes`
  (`/sys/class/block/<name>/size` × 512, with a missing/zero result failing
  closed). It is read-only, works on i386 and x86_64, and avoids adding a
  broader device capability.
- If the probe proves the ioctl encoding is wrong, derive the request from the
  platform `size_t` (or use `blockdev`/sysfs) rather than hard-coding the
  64-bit value.
- Do **not** patch the frozen `1275` guest. Apply the correction in current
  `main`, add i386/fallback unit tests, then build a **current** fixture/image
  and run install → first-A → stage → arm → B health. The old diagnostic
  proves only 1275-era behavior.
- Keep the language `.greia_update` acceptance route separate; it does not
  test A/B staging.

## Review boundary

No new boot, install, stage, arm, B boot, rollback or physical/USB operation was
performed for this analysis. It is a source-path reading plus a proposed probe.
Healthy B, current-language image acceptance and Session 04 remain OPEN.
