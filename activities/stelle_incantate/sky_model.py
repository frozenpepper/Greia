"""Domain model and round state machine for Stelle Incantate.

The model owns the connect-the-dots invariants only: which stars are
connected, which numbered star the child is invited to tap next, and when a
constellation figure is complete. Presentation, input and platform services
live in their own modules.
"""

from __future__ import annotations

from typing import Iterable

if __package__:
    from .sky_content import Constellation, CONSTELLATIONS_BY_ID, CONSTELLATION_ORDER
else:
    from sky_content import Constellation, CONSTELLATIONS_BY_ID, CONSTELLATION_ORDER


class SkyRound:
    """One connect-the-dots round over a real constellation figure.

    Invariant: connected stars are always a prefix-friendly set discovered in
    numeric order, so every newly connected star can be drawn attached to at
    least one already-lit star.
    """

    def __init__(self, constellation: Constellation) -> None:
        self.constellation = constellation
        self._connected: set[int] = set()
        self._last_connected: int | None = None

    @property
    def star_count(self) -> int:
        return self.constellation.star_count

    @property
    def connected(self) -> frozenset[int]:
        return frozenset(self._connected)

    @property
    def last_connected(self) -> int | None:
        return self._last_connected

    @property
    def next_star(self) -> int:
        """Zero-based index of the numbered star the child should tap now."""

        for index in range(self.constellation.star_count):
            if index not in self._connected:
                return index
        raise RuntimeError("complete round has no next star")

    @property
    def next_star_number(self) -> int:
        return self.next_star + 1

    @property
    def is_complete(self) -> bool:
        return len(self._connected) == self.constellation.star_count

    def connect(self, star_index: int) -> bool:
        """Connect one star in numeric order; out-of-order taps are rejected."""

        if not 0 <= star_index < self.constellation.star_count:
            return False
        if star_index in self._connected:
            return False
        expected = self.next_star
        if star_index != expected:
            return False
        self._connected.add(star_index)
        self._last_connected = star_index
        return True

    def edges_affected_by(self, star_index: int) -> tuple[tuple[int, int], ...]:
        """Edges that become visible once ``star_index`` is connected.

        The star itself may not be registered as connected yet: the renderer
        calls this right after a successful connect, or speculatively, and the
        other endpoint must already be lit for the edge to appear.
        """

        return tuple(
            edge
            for edge in self.constellation.edges
            if star_index in edge
            and (edge[0] in self._connected or edge[0] == star_index)
            and (edge[1] in self._connected or edge[1] == star_index)
            and any(other != star_index and other in self._connected for other in edge)
        )


class SkySession:
    """Ordered constellation progression for one play session."""

    def __init__(
        self,
        *,
        completed_ids: Iterable[str] = (),
        constellation_ids: tuple[str, ...] = CONSTELLATION_ORDER,
    ) -> None:
        self._order = tuple(
            constellation_id
            for constellation_id in constellation_ids
            if constellation_id in CONSTELLATIONS_BY_ID
        ) or CONSTELLATION_ORDER
        self._completed: set[str] = {
            constellation_id
            for constellation_id in completed_ids
            if constellation_id in self._order
        }
        self.round: SkyRound = self._open_next_round()

    @property
    def order(self) -> tuple[str, ...]:
        return self._order

    @property
    def completed_ids(self) -> frozenset[str]:
        return frozenset(self._completed)

    @property
    def current(self) -> SkyRound:
        return self.round

    @property
    def all_complete(self) -> bool:
        return len(self._completed) == len(self._order)

    def record_completion(self) -> str:
        """Mark the current round's constellation completed and return its id."""

        constellation_id = self.round.constellation.constellation_id
        self._completed.add(constellation_id)
        return constellation_id

    def advance(self) -> SkyRound:
        """Open the next not-yet-completed constellation (wraps for replay)."""

        self.round = self._open_next_round()
        return self.round

    def _open_next_round(self) -> SkyRound:
        for constellation_id in self._order:
            if constellation_id not in self._completed:
                return SkyRound(CONSTELLATIONS_BY_ID[constellation_id])
        # Every constellation is complete: replay the first figure so the child
        # always has a live sky, without erasing durable completion facts.
        return SkyRound(CONSTELLATIONS_BY_ID[self._order[0]])
