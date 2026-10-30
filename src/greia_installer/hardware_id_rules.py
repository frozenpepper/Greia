"""Small data-driven PCI/USB ID rules for chips the generic resolvers miss.

Primary hardware selection stays with ``modinfo firmware:`` declarations of the
bound drivers and isenkram modalias metadata.  Those cannot resolve some legacy
cases reliably: a Broadcom ``brcmsmac`` chip whose driver has not bound yet, a
Radeon whose ``radeon`` module is blocked, or a chip that has no usable open
driver at all.  This table is a narrow, reviewed supplement:

* a rule adds Debian package names only; the planner still installs a name
  **only if the verified media pool provides it as firmware**, so a pool that
  omits a package simply skips the rule (it is never "missing");
* a rule may instead mark the device as *unsupported*: its Wi-Fi needs firmware
  or an out-of-tree driver Greia cannot include (Broadcom b43 firmware is not
  redistributable; ``wl`` needs DKMS compilation).  The installer then tells the
  parent plainly instead of leaving an empty Wi-Fi list unexplained.

Sources: ``2026-10-21_PRE_M1_MAC_HARDWARE_SUPPORT.md`` (archived; see git history) section 2
and ``2026-10-21_LEGACY_X86_NETBOOK_HARDWARE_RISKS.md`` (archived; see git history) section 3.
All entries are UNPROVEN on real Macs/netbooks; extend the table from user
reports, never with a Greia-owned product database of names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from greia_platform.hardware_enablement import HardwareInventory

_PCI_RE = re.compile(
    r"^pci:v([0-9A-Fa-f]{8})d([0-9A-Fa-f]{8})"
    r"sv[0-9A-Fa-f]{8}sd[0-9A-Fa-f]{8}bc([0-9A-Fa-f]{2})"
)
_USB_RE = re.compile(r"^usb:v([0-9A-Fa-f]{4})p([0-9A-Fa-f]{4})")

PCI_CLASS_NETWORK = 0x02
PCI_CLASS_DISPLAY = 0x03

#: Reason codes for hardware Greia cannot enable offline.
REASON_B43_FIRMWARE = "wifi-b43-firmware-not-redistributable"
REASON_NO_OPEN_DRIVER = "wifi-no-open-driver"
UNSUPPORTED_WIFI_REASONS = frozenset({REASON_B43_FIRMWARE, REASON_NO_OPEN_DRIVER})


@dataclass(frozen=True, slots=True)
class DeviceIdRule:
    """One vendor (and optional device/class) match with its outcome."""

    bus: str
    vendor: int
    devices: frozenset[int] | None = None
    #: PCI base class (``bc`` field); ``None`` matches any class.
    pci_class: int | None = None
    packages: tuple[str, ...] = ()
    #: One of ``UNSUPPORTED_WIFI_REASONS`` when the device cannot be enabled.
    unsupported_reason: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.bus not in {"pci", "usb"}:
            raise ValueError("rule bus must be pci or usb")
        if bool(self.packages) == bool(self.unsupported_reason):
            raise ValueError("a rule selects packages or marks unsupported, not both")
        if self.unsupported_reason is not None and (
            self.unsupported_reason not in UNSUPPORTED_WIFI_REASONS
        ):
            raise ValueError("unknown unsupported-hardware reason")

    def matches(self, bus: str, vendor: int, device: int, pci_class: int | None) -> bool:
        if bus != self.bus or vendor != self.vendor:
            return False
        if self.devices is not None and device not in self.devices:
            return False
        if self.pci_class is not None and pci_class != self.pci_class:
            return False
        return True


@dataclass(frozen=True, slots=True)
class UnsupportedDevice:
    """A device the installer must tell the parent about."""

    reason: str
    bus: str
    vendor: int
    device: int

    @property
    def diagnostic(self) -> str:
        return (
            f"{self.bus} {self.vendor:04x}:{self.device:04x} needs firmware or a "
            f"driver Greia cannot include ({self.reason}); use Ethernet or a USB Wi-Fi adapter"
        )


@dataclass(frozen=True, slots=True)
class DeviceIdRuleResult:
    packages: tuple[str, ...]
    unsupported: tuple[UnsupportedDevice, ...]

    @property
    def wifi_firmware_unavailable(self) -> bool:
        return any(item.reason in UNSUPPORTED_WIFI_REASONS for item in self.unsupported)


def _ids(*values: int) -> frozenset[int]:
    return frozenset(values)


#: Broadcom (PCI 14e4).  brcmsmac chips use redistributable firmware-brcm80211.
_BROADCOM = 0x14E4
DEFAULT_DEVICE_ID_RULES: tuple[DeviceIdRule, ...] = (
    DeviceIdRule(
        "pci",
        _BROADCOM,
        _ids(0x0576, 0x4353, 0x4357, 0x4727),
        packages=("firmware-brcm80211",),
        note="BCM43224/43225/4313: brcmsmac",
    ),
    # b43 / b43legacy chips: BCM4301/4306/4307/4309/4311/4312/4315/4318/4321/
    # 4322/4331.  Their firmware must be cut from Broadcom's proprietary
    # driver and is not redistributable (Debian ships only a downloader in
    # contrib), so an offline Greia install cannot provide it.
    DeviceIdRule(
        "pci",
        _BROADCOM,
        _ids(
            0x4301, 0x4307, 0x4311, 0x4312, 0x4315, 0x4318, 0x4320, 0x4324,
            0x4325, 0x4328, 0x4329, 0x432A, 0x432B, 0x432C, 0x432D, 0x4331,
        ),
        pci_class=PCI_CLASS_NETWORK,
        unsupported_reason=REASON_B43_FIRMWARE,
        note="b43 family",
    ),
    # Chips with no mainline driver (``wl`` / broadcom-sta only), which would
    # need DKMS compilation on the target: BCM4352/4360/43227/43228/43142.
    DeviceIdRule(
        "pci",
        _BROADCOM,
        _ids(0x43A0, 0x43B1, 0x4352, 0x4360, 0x4358, 0x4359, 0x4365),
        pci_class=PCI_CLASS_NETWORK,
        unsupported_reason=REASON_NO_OPEN_DRIVER,
        note="wl-only family",
    ),
    # Graphics microcode.  Older cores need none, but the packages are only
    # added when the pool has them and cost pool space, not target logic.
    DeviceIdRule(
        "pci", 0x1002, pci_class=PCI_CLASS_DISPLAY, packages=("firmware-amd-graphics",),
        note="Radeon R600+ / GCN (radeon, amdgpu)",
    ),
    DeviceIdRule(
        "pci", 0x10DE, pci_class=PCI_CLASS_DISPLAY, packages=("firmware-misc-nonfree",),
        note="nouveau microcode (bookworm ships it in firmware-misc-nonfree)",
    ),
    # Wi-Fi/NIC vendors whose firmware lives in a single Debian package.
    DeviceIdRule(
        "pci", 0x10EC, pci_class=PCI_CLASS_NETWORK, packages=("firmware-realtek",),
        note="r8169 NIC microcode, RTL8192CE/8188CE/8723",
    ),
    DeviceIdRule(
        "pci", 0x1814, pci_class=PCI_CLASS_NETWORK, packages=("firmware-misc-nonfree",),
        note="Ralink RT2800/RT3090 (rt2800pci)",
    ),
    DeviceIdRule(
        "pci",
        0x8086,
        _ids(
            0x4222, 0x4227,  # PRO/Wireless 3945
            0x4229, 0x4230,  # 4965AGN
            0x4232, 0x4235, 0x4236, 0x4237,  # 5100 / 5300
            0x4238, 0x4239, 0x422B, 0x422C,  # 6000 series
        ),
        packages=("firmware-iwlwifi",),
        note="Intel iwlwifi DVM-era chips",
    ),
    DeviceIdRule(
        "pci",
        0x8086,
        _ids(0x1043, 0x4220, 0x4221, 0x4223, 0x4224),
        packages=("firmware-ipw2x00",),
        note="ipw2100/ipw2200 (non-free in bookworm: normally not in the pool)",
    ),
    DeviceIdRule(
        "usb", 0x0CF3, packages=("firmware-atheros",),
        note="ath9k_htc / AR3011 dongles",
    ),
)


def parse_modalias(modalias: str) -> tuple[str, int, int, int | None] | None:
    """Return ``(bus, vendor, device, pci_class)`` for a PCI/USB modalias."""

    match = _PCI_RE.match(modalias)
    if match:
        return (
            "pci",
            int(match.group(1), 16),
            int(match.group(2), 16),
            int(match.group(3), 16),
        )
    match = _USB_RE.match(modalias)
    if match:
        return "usb", int(match.group(1), 16), int(match.group(2), 16), None
    return None


def evaluate_device_id_rules(
    inventory: HardwareInventory,
    provided_firmware: Iterable[str],
    rules: tuple[DeviceIdRule, ...] = DEFAULT_DEVICE_ID_RULES,
) -> DeviceIdRuleResult:
    """Apply the rule table to one inventory snapshot.

    Package names are returned only if present in ``provided_firmware`` (the
    verified pool); unsupported devices are reported regardless of the pool.
    """

    provided = frozenset(provided_firmware)
    packages: dict[str, None] = {}
    unsupported: dict[tuple[str, str, int, int], UnsupportedDevice] = {}
    for modalias in inventory.modaliases:
        parsed = parse_modalias(modalias)
        if parsed is None:
            continue
        bus, vendor, device, pci_class = parsed
        for rule in rules:
            if not rule.matches(bus, vendor, device, pci_class):
                continue
            if rule.unsupported_reason is not None:
                unsupported.setdefault(
                    (rule.unsupported_reason, bus, vendor, device),
                    UnsupportedDevice(rule.unsupported_reason, bus, vendor, device),
                )
                continue
            for name in rule.packages:
                if name in provided:
                    packages.setdefault(name)
    return DeviceIdRuleResult(
        tuple(sorted(packages)),
        tuple(sorted(unsupported.values(), key=lambda item: (item.reason, item.vendor, item.device))),
    )
