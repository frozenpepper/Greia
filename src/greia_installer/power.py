from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PowerStatus:
    battery_present: bool
    battery_percent: int | None
    external_power_online: bool | None

    def installation_block_reason(self, *, minimum_percent: int = 40) -> str | None:
        """Block only when Linux positively reports low battery and no AC."""

        if not self.battery_present or self.external_power_online is not False:
            return None
        if self.battery_percent is None:
            return (
                "Connect the power adapter before installing "
                "(battery level could not be read)."
            )
        if self.battery_percent < minimum_percent:
            return (
                f"Connect the power adapter before installing "
                f"(battery is {self.battery_percent}%)."
            )
        return None


class PowerSupplyProbe:
    def __init__(self, root: Path = Path("/sys/class/power_supply")):
        self.root = root

    def probe(self) -> PowerStatus:
        batteries: list[int] = []
        battery_present = False
        external_states: list[bool] = []
        try:
            supplies = tuple(self.root.iterdir())
        except OSError:
            supplies = ()
        for supply in supplies:
            supply_type = self._read_text(supply / "type").lower()
            if supply_type == "battery":
                present = self._read_int(supply / "present")
                if present == 0:
                    continue
                battery_present = True
                capacity = self._read_int(supply / "capacity")
                if capacity is not None:
                    batteries.append(min(100, max(0, capacity)))
            elif supply_type in {"mains", "usb", "usb_c", "wireless"}:
                online = self._read_int(supply / "online")
                if online is not None:
                    external_states.append(bool(online))
        external: bool | None
        if external_states:
            external = any(external_states)
        else:
            external = None
        return PowerStatus(
            battery_present=battery_present,
            battery_percent=min(batteries) if batteries else None,
            external_power_online=external,
        )

    def installation_block_reason(self) -> str | None:
        return self.probe().installation_block_reason()

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeDecodeError):
            return ""

    @classmethod
    def _read_int(cls, path: Path) -> int | None:
        raw = cls._read_text(path)
        try:
            return int(raw)
        except ValueError:
            return None
