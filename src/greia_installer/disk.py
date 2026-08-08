from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


class DiskProbeError(RuntimeError):
    pass


EXTERNAL_TRANSPORTS = frozenset({"usb", "ieee1394", "firewire"})
MMC_DEVICE_PREFIX = "/dev/mmcblk"
_ALLOWED_DISK_DESCENDANT_TYPES = frozenset({"part"})


@dataclass(frozen=True, slots=True)
class BlockDevice:
    name: str
    path: Path
    size_bytes: int
    device_type: str
    model: str
    serial: str
    transport: str
    removable: bool
    read_only: bool
    mountpoints: tuple[Path, ...]
    children: tuple["BlockDevice", ...] = ()
    wwn: str = ""
    major_minor: str = ""
    hotplug: bool = False

    @property
    def fingerprint(self) -> str:
        return "|".join(
            (
                str(self.path),
                str(self.size_bytes),
                self.model.strip(),
                self.serial.strip(),
                self.wwn.strip(),
                self.major_minor.strip(),
            )
        )

    @property
    def identity_digest(self) -> str:
        return hashlib.sha256(self.fingerprint.encode("utf-8")).hexdigest()

    @property
    def human_size(self) -> str:
        gib = self.size_bytes / (1024**3)
        if gib >= 1:
            return f"{gib:.1f} GiB"
        return f"{self.size_bytes / (1024**2):.0f} MiB"

    @property
    def display_name(self) -> str:
        model = self.model.strip() or self.name
        return f"{model} · {self.human_size}"

    def all_mountpoints(self) -> tuple[Path, ...]:
        collected = list(self.mountpoints)
        for child in self.children:
            collected.extend(child.all_mountpoints())
        return tuple(dict.fromkeys(collected))

    def has_active_storage_stack(self) -> bool:
        for child in self.children:
            if child.device_type.strip().lower() not in _ALLOWED_DISK_DESCENDANT_TYPES:
                return True
            if child.has_active_storage_stack():
                return True
        return False

    def is_install_target_eligible(
        self,
        *,
        minimum_bytes: int = 4 * 1024**3,
        allow_mmc: bool = False,
    ) -> bool:
        if self.device_type != "disk":
            return False
        if self.removable or self.hotplug or self.read_only or self.size_bytes < minimum_bytes:
            return False
        transport = self.transport.strip().lower()
        if transport in EXTERNAL_TRANSPORTS:
            return False
        if not allow_mmc and (transport == "mmc" or str(self.path).startswith(MMC_DEVICE_PREFIX)):
            return False
        if self.all_mountpoints() or self.has_active_storage_stack():
            return False
        return True


@dataclass(frozen=True, slots=True)
class DiskInventory:
    devices: tuple[BlockDevice, ...]

    def by_path(self, path: Path) -> BlockDevice | None:
        resolved = path.resolve()
        return next((device for device in self.devices if device.path.resolve() == resolved), None)

    def install_targets(
        self,
        *,
        minimum_bytes: int = 4 * 1024**3,
        allow_mmc: bool = False,
    ) -> tuple[BlockDevice, ...]:
        return tuple(
            device
            for device in self.devices
            if device.is_install_target_eligible(
                minimum_bytes=minimum_bytes,
                allow_mmc=allow_mmc,
            )
        )


class CommandRunner(Protocol):
    def run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            check=False,
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


class LsblkDiskProbe:
    FIELDS = "NAME,PATH,SIZE,TYPE,RM,HOTPLUG,RO,MOUNTPOINTS,MODEL,SERIAL,WWN,MAJ:MIN,TRAN"

    def __init__(self, runner: CommandRunner | None = None):
        self.runner = runner or SubprocessRunner()

    def probe(self) -> DiskInventory:
        completed = self.runner.run(
            ["lsblk", "--json", "--bytes", "--output", self.FIELDS]
        )
        if completed.returncode != 0:
            raise DiskProbeError(completed.stderr.strip() or "lsblk failed")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise DiskProbeError("lsblk returned invalid JSON") from exc
        raw_devices = payload.get("blockdevices")
        if not isinstance(raw_devices, list):
            raise DiskProbeError("lsblk response has no blockdevices array")
        devices = tuple(self._parse_device(item) for item in raw_devices if isinstance(item, dict))
        return DiskInventory(devices)

    def _parse_device(self, raw: dict[str, object]) -> BlockDevice:
        children_raw = raw.get("children")
        children = (
            tuple(
                self._parse_device(item)
                for item in children_raw
                if isinstance(item, dict)
            )
            if isinstance(children_raw, list)
            else ()
        )
        mountpoints_raw = raw.get("mountpoints")
        mountpoints: list[Path] = []
        if isinstance(mountpoints_raw, list):
            for mountpoint in mountpoints_raw:
                if isinstance(mountpoint, str) and mountpoint:
                    mountpoints.append(Path(mountpoint))
        elif isinstance(raw.get("mountpoint"), str) and raw.get("mountpoint"):
            mountpoints.append(Path(str(raw["mountpoint"])))
        try:
            return BlockDevice(
                name=str(raw.get("name", "")),
                path=Path(str(raw["path"])),
                size_bytes=int(raw.get("size", 0)),
                device_type=str(raw.get("type", "")),
                model=str(raw.get("model") or ""),
                serial=str(raw.get("serial") or ""),
                transport=str(raw.get("tran") or ""),
                removable=bool(int(raw.get("rm", 0))),
                read_only=bool(int(raw.get("ro", 0))),
                mountpoints=tuple(mountpoints),
                children=children,
                wwn=str(raw.get("wwn") or ""),
                major_minor=str(raw.get("maj:min") or raw.get("maj_min") or ""),
                hotplug=bool(int(raw.get("hotplug", 0))),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DiskProbeError(f"invalid lsblk device record: {exc}") from exc


def partition_one_path(device_path: Path) -> Path:
    name = str(device_path)
    return Path(f"{name}p1" if name[-1:].isdigit() else f"{name}1")
