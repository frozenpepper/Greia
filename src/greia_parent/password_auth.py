from __future__ import annotations

import time
from collections import OrderedDict, deque
from collections.abc import Callable


class ParentPasswordAttemptLimiter:
    """Bound failed Parent-password bootstrap attempts by client address.

    The Parent API is intentionally single-process and low-resource. This limiter
    therefore keeps only recent failure timestamps for a bounded number of
    client addresses; successful authentication clears that client's history.
    It does not persist passwords, credentials, or network identifiers to disk.
    """

    def __init__(
        self,
        *,
        max_failures: int = 5,
        window_seconds: float = 60.0,
        max_clients: int = 128,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_failures < 1:
            raise ValueError("max_failures must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_clients < 1:
            raise ValueError("max_clients must be positive")
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self.clock = clock
        self._failures: OrderedDict[str, deque[float]] = OrderedDict()

    def allowed(self, client_address: str) -> bool:
        failures = self._recent_failures(client_address)
        return len(failures) < self.max_failures

    def record_failure(self, client_address: str) -> None:
        now = self.clock()
        failures = self._recent_failures(client_address, now=now)
        failures.append(now)
        self._failures.move_to_end(client_address)
        while len(self._failures) > self.max_clients:
            self._failures.popitem(last=False)

    def clear(self, client_address: str) -> None:
        self._failures.pop(client_address, None)

    def _recent_failures(
        self,
        client_address: str,
        *,
        now: float | None = None,
    ) -> deque[float]:
        timestamp = self.clock() if now is None else now
        failures = self._failures.get(client_address)
        if failures is None:
            failures = deque()
            self._failures[client_address] = failures
        cutoff = timestamp - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            # Keep the current address available to callers that are about to
            # append, but discard other empty entries opportunistically.
            for address in tuple(self._failures):
                if address != client_address and not self._failures[address]:
                    self._failures.pop(address, None)
        self._failures.move_to_end(client_address)
        return failures
