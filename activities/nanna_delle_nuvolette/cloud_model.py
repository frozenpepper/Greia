"""Domain model and calm bedtime state for Nanna delle Nuvolette."""

from __future__ import annotations

from typing import Final, Sequence

if __package__:
    from .cloud_content import BLANKETS_BY_ID, VALID_BLANKET_IDS, Blanket
else:
    from cloud_content import BLANKETS_BY_ID, VALID_BLANKET_IDS, Blanket


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
MAX_STARS_PER_CLOUD: Final = 3
TOTAL_CLOUDS: Final = 3
INITIAL_STARS: Final = 9


class CloudFriend:
    """One sweet little cloud friend that can receive a blanket and stars."""

    def __init__(
        self,
        cloud_id: str,
        name_key: str,
        center_x: int,
        center_y: int,
        *,
        blanket_id: str | None = None,
        star_ids: Sequence[str] = (),
        asleep: bool = False,
    ) -> None:
        self.cloud_id = cloud_id
        self.name_key = name_key
        self.center_x = center_x
        self.center_y = center_y
        self.blanket_id = blanket_id if blanket_id in VALID_BLANKET_IDS else None
        self._star_ids: list[str] = list(star_ids[:MAX_STARS_PER_CLOUD])
        self.asleep = asleep
        self.is_yawning = False
        self.yawn_start_time = 0.0
        self.hint_start_time = 0.0

    @property
    def star_ids(self) -> tuple[str, ...]:
        return tuple(self._star_ids)

    @property
    def star_count(self) -> int:
        return len(self._star_ids)

    @property
    def is_ready_to_sleep(self) -> bool:
        return self.blanket_id is not None and len(self._star_ids) >= 1

    @property
    def ready_to_sleep(self) -> bool:
        return self.is_ready_to_sleep

    def trigger_hint(self, now: float) -> None:
        self.hint_start_time = now

    def is_hint_active(self, now: float) -> bool:
        return (now - self.hint_start_time) < 1.2

    def give_blanket(self, blanket_id: str) -> bool:
        if self.asleep:
            return False
        if blanket_id in VALID_BLANKET_IDS:
            self.blanket_id = blanket_id
            return True
        return False

    def give_star(self, star_id: str | None = None) -> bool:
        if self.asleep:
            return False
        if len(self._star_ids) < MAX_STARS_PER_CLOUD:
            sid = star_id or f"star_{self.cloud_id}_{len(self._star_ids) + 1}"
            self._star_ids.append(sid)
            return True
        return False

    def tap_to_tuck_in(self, now: float) -> bool:
        """Handle tap on cloud: yawn-to-sleep if ready, gentle neutral hint if not."""
        if self.asleep or self.is_yawning:
            return False
        if self.is_ready_to_sleep:
            self.is_yawning = True
            self.yawn_start_time = now
            return True
        else:
            self.hint_start_time = now
            return False

    def update(self, now: float) -> bool:
        """Advance timers; return True if state changed."""
        if self.is_yawning and (now - self.yawn_start_time) >= 0.8:
            self.is_yawning = False
            self.asleep = True
            return True
        return False


class NightScene:
    """Own the three clouds, bedtime items, and peaceful night state."""

    def __init__(self, night_id: str, default_blankets: Sequence[str | None] = ()) -> None:
        self.night_id = night_id
        self.held_item: str | None = None
        self.completed_emitted = False

        b_ids: list[str | None] = [None, None, None]
        for i, b in enumerate(default_blankets[:3]):
            if b in VALID_BLANKET_IDS:
                b_ids[i] = b

        self.clouds: tuple[CloudFriend, CloudFriend, CloudFriend] = (
            CloudFriend("cloud_1", "cloud.1", 245, 230, blanket_id=b_ids[0]),
            CloudFriend("cloud_2", "cloud.2", 511, 200, blanket_id=b_ids[1]),
            CloudFriend("cloud_3", "cloud.3", 775, 230, blanket_id=b_ids[2]),
        )

    @classmethod
    def create_night(cls, night_id: str, default_blankets: Sequence[str | None] = ()) -> NightScene:
        return cls(night_id, default_blankets=default_blankets)

    @property
    def all_asleep(self) -> bool:
        return all(c.asleep for c in self.clouds)

    @property
    def all_sleeping(self) -> bool:
        return self.all_asleep

    @property
    def total_stars(self) -> int:
        return sum(c.star_count for c in self.clouds)

    @property
    def available_stars(self) -> int:
        return max(0, INITIAL_STARS - self.total_stars)

    def tuck_blanket(self, cloud_id: str, blanket_id: str) -> bool:
        for c in self.clouds:
            if c.cloud_id == cloud_id:
                return c.give_blanket(blanket_id)
        return False

    def add_star(self, cloud_id: str) -> bool:
        if self.available_stars <= 0:
            return False
        for c in self.clouds:
            if c.cloud_id == cloud_id:
                return c.give_star()
        return False

    def put_to_sleep(self, cloud_id: str) -> bool:
        for c in self.clouds:
            if c.cloud_id == cloud_id:
                if c.ready_to_sleep:
                    c.asleep = True
                    return True
        return False

    def update(self, now: float) -> bool:
        changed = False
        for c in self.clouds:
            if c.update(now):
                changed = True
        return changed
