#!/usr/bin/env bash
# The privileged install legs, inside a unit replicating the transaction
# service, against a disk prepared by host_disk.sh as the physical /dev/sda.
set -u
REPRO=/opt/greia-repro
WORK=$REPRO/work
MNT=$WORK/mnt
POOL=$WORK/pool
PAYLOAD=$REPRO/greia-rootfs.squashfs
CG=$(awk -F: '/^[0-9]+::/{print $3}' /proc/self/cgroup)
SELF=/sys/fs/cgroup$CG
PART=$(cat "$WORK/part" 2>/dev/null); WHOLE=$(cat "$WORK/loop" 2>/dev/null)
[ -b "$PART" ] || { echo "no target block device ($PART)"; exit 1; }

unmount_all() {
  for m in greia-hardware-support run sys proc dev; do mountpoint -q "$MNT/$m" 2>/dev/null && umount -lf "$MNT/$m"; done
  mountpoint -q "$MNT" 2>/dev/null && umount -lf "$MNT"
  return 0
}
unmount_all
mkdir -p "$MNT" "$POOL"
mount "$PART" "$MNT" || { echo "mount target FAILED"; exit 1; }
unsquashfs -f -no-progress -strict-errors -processors 1 -d "$MNT" "$PAYLOAD" 2>&1 | grep -viE "^created|^Parallel mksys|^FATAL ERROR: Failed to create thread" | tail -5
[ "${PIPESTATUS[0]}" -ne 0 ] && { echo "unsquash FAILED"; exit 1; }
for n in dev proc sys run; do mkdir -p "$MNT/$n"; done
mount --rbind /dev "$MNT/dev"; mount --make-rslave "$MNT/dev"
mount -t proc proc "$MNT/proc"
mount --rbind /sys "$MNT/sys"; mount --make-rslave "$MNT/sys"
mount --rbind /run "$MNT/run"; mount --make-rslave "$MNT/run"

D=$WORK/greia-hwtest; rm -rf "$D"; mkdir -p "$D/DEBIAN" "$D/usr/share"
printf 'Package: greia-hwtest\nVersion: 1.0\nArchitecture: all\nMaintainer: Greia <dev@example.invalid>\nDescription: harness sentinel\n' > "$D/DEBIAN/control"
echo sentinel-installed > "$D/usr/share/sentinel"
dpkg-deb --build "$D" "$POOL/greia-hwtest_1.0_all.deb" >/dev/null 2>&1 || { echo "deb build FAILED"; exit 1; }
( cd "$POOL" && dpkg-scanpackages --multiversion . /dev/null 2>/dev/null > Packages ) || { echo "scanpackages FAILED"; exit 1; }
[ -s "$POOL/Packages" ] || { echo "empty Packages index"; exit 1; }
mkdir -p "$MNT/run/greia-hardware-support"
mount --bind "$POOL" "$MNT/run/greia-hardware-support"
mount -o remount,bind,ro "$MNT/run/greia-hardware-support"
echo "deb [trusted=yes] file:/run/greia-hardware-support ./" > "$MNT/run/greia-hardware-support.list"
chmod 0644 "$MNT/run/greia-hardware-support.list"

( while :; do cat "$SELF/pids.current" 2>/dev/null >> /tmp/peak.$$; sleep 0.05; done ) & MON=$!
quiet() { grep -viE 'locale|LANGUAGE|LC_ALL|LANG =|perl: warning|supported and installed|Possible missing firmware|^$'; }
OPTS="-o Dir::Etc::sourcelist=/run/greia-hardware-support.list -o Dir::Etc::sourceparts=- -o APT::Get::List-Cleanup=0 -o Acquire::Languages=none"

echo "=== leg 1: update-initramfs ==="
chroot "$MNT" /usr/sbin/update-initramfs -u -k all 2>&1 | quiet | tail -3; echo "  exit=${PIPESTATUS[0]}"
echo "=== leg 2: update-grub ==="
chroot "$MNT" /usr/sbin/update-grub 2>&1 | quiet | tail -2; echo "  exit=${PIPESTATUS[0]}"
echo "=== leg 3: apt-get update ==="
chroot "$MNT" /usr/bin/apt-get $OPTS update 2>&1 | quiet | tail -4; echo "  exit=${PIPESTATUS[0]}"
echo "=== leg 4: apt-get install ==="
chroot "$MNT" /usr/bin/env DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get $OPTS install -y --no-install-recommends greia-hwtest 2>&1 | quiet | tail -4; echo "  exit=${PIPESTATUS[0]}"
echo "=== leg 5: grub-install ==="
chroot "$MNT" /usr/sbin/grub-install --target=i386-pc --boot-directory=/boot --recheck "$WHOLE" 2>&1 | quiet | tail -4; echo "  exit=${PIPESTATUS[0]}"
echo "=== leg 6: grub-script-check ==="
chroot "$MNT" grub-script-check /boot/grub/grub.cfg 2>&1 | quiet | tail -2; echo "  exit=${PIPESTATUS[0]}"
echo "=== verify ==="
chroot "$MNT" /bin/sh -c 'cat /usr/share/sentinel 2>&1; ls -l /boot/initrd.img-* | head -2; ls -l /usr/bin/chage' 2>&1 | tail -4
kill $MON 2>/dev/null
echo "PEAK_PIDS_THIS_UNIT=$(sort -n /tmp/peak.$$ 2>/dev/null | tail -1)"; rm -f /tmp/peak.$$
unmount_all
echo "DONE"
