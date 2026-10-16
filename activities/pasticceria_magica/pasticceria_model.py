"""Pure rules for Magic Bakery: orders, cakes, rounds and the ladder.

No pygame, storage or Greia IO; randomness is injected so every round can be
driven deterministically in tests.

* An ``Order`` is what one customer asks for. ``CountOrder`` asks for
  quantities ("3 strawberries and 2 blueberries"); ``PatternOrder`` asks the
  child to finish a repeating row ("strawberry, blueberry, strawberry, ...").
  Both create their own cake (``new_cake``), say when the cake may be served
  (``ready``) and judge it (``check``) - the app never branches on the kind.
* A cake records only what the child placed. Placing never fails silently
  into a wrong state: a full cake or a topping that is not in the pantry is
  refused.
* ``BakeryRound`` is one finite visit of five customers; ``adapt_level``
  moves the ladder from the misses of a finished round.
* ``FreeCake`` is the "make your own cake" ending: toppings anywhere on the
  frosting (normalised ellipse coordinates), bounded and serialisable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Protocol

if __package__:
    from .pasticceria_content import (
        COUNT,
        COUNT_SLOTS,
        CUSTOMERS,
        FREE_LIMIT,
        LEVELS,
        LOOKALIKES,
        MAX_LEVEL,
        PATTERN,
        PATTERN_LENGTH,
        TOPPING_IDS,
        LevelSpec,
    )
else:
    from pasticceria_content import (
        COUNT,
        COUNT_SLOTS,
        CUSTOMERS,
        FREE_LIMIT,
        LEVELS,
        LOOKALIKES,
        MAX_LEVEL,
        PATTERN,
        PATTERN_LENGTH,
        TOPPING_IDS,
        LevelSpec,
    )


@dataclass(frozen=True, slots=True)
class Placement:
    """One topping put on the cake: where, what, and its count of that kind."""

    index: int
    topping_id: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class Verdict:
    """Result of serving a cake.

    ``wrong`` are cake places that do not belong (wrong kind, one too many, or
    a pattern place that breaks the pattern). ``missing`` lists one topping id
    per topping still to add; ``ghosts`` are the pattern places with the
    topping that belongs there (shown only as a late hint).
    """

    correct: bool
    wrong: tuple[int, ...] = ()
    missing: tuple[str, ...] = ()
    ghosts: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True, slots=True)
class DemoStep:
    """One beat of the "let's look together" demonstration after a wrong serve.

    ``number`` > 0 counts the topping at ``index`` aloud; 0 just taps it in
    rhythm (pattern rows), sounding ``tone`` (one pitch per topping kind, so
    A-B-A-B is heard as well as seen). ``row`` is the order-card line to
    light up.
    """

    index: int
    number: int
    row: int | None
    tone: int = 0


class Cake(Protocol):
    """What every cake on the counter offers to the app and renderer."""

    def place(self, topping_id: str) -> Placement | None: ...
    def remove(self, index: int) -> bool: ...
    def undo(self) -> int | None: ...
    def placements(self) -> tuple[tuple[int, str], ...]: ...
    @property
    def empty(self) -> bool: ...


class Order(Protocol):
    """One customer's order; creates, judges and hints its own cake."""

    kind: str
    pantry: tuple[str, ...]
    counts_aloud: bool

    def new_cake(self) -> Cake: ...
    def ready(self, cake) -> bool: ...
    def check(self, cake) -> Verdict: ...
    def next_needed(self, cake) -> str | None: ...
    def demonstration(self, cake) -> tuple[DemoStep, ...]: ...
    def ghosts(self, cake, verdict: Verdict) -> tuple[tuple[int, str], ...]: ...


# -- counting orders -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CountItem:
    topping_id: str
    amount: int


class CountCake:
    """Toppings placed into fixed places (filled in a stable, countable order)."""

    def __init__(self, capacity: int = COUNT_SLOTS) -> None:
        self._slots: list[str | None] = [None] * capacity
        self._history: list[int] = []

    @property
    def capacity(self) -> int:
        return len(self._slots)

    @property
    def empty(self) -> bool:
        return not self._history

    def count(self, topping_id: str) -> int:
        return sum(1 for value in self._slots if value == topping_id)

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for value in self._slots:
            if value is not None:
                result[value] = result.get(value, 0) + 1
        return result

    def place(self, topping_id: str) -> Placement | None:
        if topping_id not in TOPPING_IDS:
            return None
        for index, value in enumerate(self._slots):
            if value is None:
                self._slots[index] = topping_id
                self._history.append(index)
                return Placement(index, topping_id, self.count(topping_id))
        return None

    def remove(self, index: int) -> bool:
        if not 0 <= index < len(self._slots) or self._slots[index] is None:
            return False
        self._slots[index] = None
        self._history.remove(index)
        return True

    def undo(self) -> int | None:
        if not self._history:
            return None
        index = self._history[-1]
        self.remove(index)
        return index

    def placements(self) -> tuple[tuple[int, str], ...]:
        return tuple((index, value) for index, value in enumerate(self._slots) if value is not None)

    def in_count_order(self, topping_id: str) -> tuple[int, ...]:
        """Places holding ``topping_id`` in the order a child would count them."""

        return tuple(index for index, value in enumerate(self._slots) if value == topping_id)


@dataclass(frozen=True, slots=True)
class CountOrder:
    """Make a cake with exactly these toppings in these amounts."""

    items: tuple[CountItem, ...]
    pantry: tuple[str, ...]
    pictures: bool = True
    kind: str = COUNT
    counts_aloud: bool = True

    @property
    def total(self) -> int:
        return sum(item.amount for item in self.items)

    def new_cake(self) -> CountCake:
        return CountCake()

    def ready(self, cake: CountCake) -> bool:
        return not cake.empty

    def check(self, cake: CountCake) -> Verdict:
        wanted = {item.topping_id: item.amount for item in self.items}
        wrong: list[int] = []
        seen: dict[str, int] = {}
        for index, topping in cake.placements():
            seen[topping] = seen.get(topping, 0) + 1
            if seen[topping] > wanted.get(topping, 0):
                wrong.append(index)
        missing: list[str] = []
        for item in self.items:
            missing.extend([item.topping_id] * max(0, item.amount - cake.count(item.topping_id)))
        return Verdict(not wrong and not missing, tuple(wrong), tuple(missing))

    def next_needed(self, cake: CountCake) -> str | None:
        for item in self.items:
            if cake.count(item.topping_id) < item.amount:
                return item.topping_id
        return None

    def demonstration(self, cake: CountCake) -> tuple[DemoStep, ...]:
        """Count each ordered topping on the cake, one card line at a time."""

        return tuple(
            DemoStep(index, number, row)
            for row, item in enumerate(self.items)
            for number, index in enumerate(cake.in_count_order(item.topping_id), start=1)
        )

    def ghosts(self, cake: CountCake, verdict: Verdict) -> tuple[tuple[int, str], ...]:
        """Missing toppings shown faintly on the next open places (late hint)."""

        used = {index for index, _ in cake.placements()}
        free = [index for index in range(cake.capacity) if index not in used]
        return tuple(zip(free, verdict.missing))


# -- pattern orders --------------------------------------------------------------------


class PatternCake:
    """A row of places: the customer's start, then places the child fills."""

    def __init__(self, given: tuple[str, ...], length: int = PATTERN_LENGTH) -> None:
        if not 0 < len(given) < length:
            raise ValueError("a pattern needs a start and at least one blank")
        self._cells: list[str | None] = [*given, *([None] * (length - len(given)))]
        self.given = len(given)
        self._history: list[int] = []

    @property
    def length(self) -> int:
        return len(self._cells)

    @property
    def empty(self) -> bool:
        return not self._history

    @property
    def full(self) -> bool:
        return all(value is not None for value in self._cells)

    def cell(self, index: int) -> str | None:
        return self._cells[index]

    def place(self, topping_id: str) -> Placement | None:
        if topping_id not in TOPPING_IDS:
            return None
        for index in range(self.given, len(self._cells)):
            if self._cells[index] is None:
                self._cells[index] = topping_id
                self._history.append(index)
                ordinal = sum(1 for value in self._cells if value == topping_id)
                return Placement(index, topping_id, ordinal)
        return None

    def remove(self, index: int) -> bool:
        if not self.given <= index < len(self._cells) or self._cells[index] is None:
            return False
        self._cells[index] = None
        self._history.remove(index)
        return True

    def undo(self) -> int | None:
        if not self._history:
            return None
        index = self._history[-1]
        self.remove(index)
        return index

    def placements(self) -> tuple[tuple[int, str], ...]:
        """Only the child's toppings (the start row belongs to the customer)."""

        return tuple(
            (index, value)
            for index, value in enumerate(self._cells)
            if index >= self.given and value is not None
        )

    def row(self) -> tuple[str | None, ...]:
        return tuple(self._cells)


@dataclass(frozen=True, slots=True)
class PatternOrder:
    """Finish the repeating row ``answer`` from its first ``given`` places."""

    unit: str
    answer: tuple[str, ...]
    given: int
    pantry: tuple[str, ...]
    kind: str = PATTERN
    counts_aloud: bool = False

    @property
    def start(self) -> tuple[str, ...]:
        return self.answer[: self.given]

    @property
    def blanks(self) -> int:
        return len(self.answer) - self.given

    def new_cake(self) -> PatternCake:
        return PatternCake(self.start, len(self.answer))

    def ready(self, cake: PatternCake) -> bool:
        return cake.full

    def check(self, cake: PatternCake) -> Verdict:
        wrong = []
        ghosts = []
        missing = []
        for index in range(self.given, len(self.answer)):
            value = cake.cell(index)
            if value is None:
                missing.append(self.answer[index])
                ghosts.append((index, self.answer[index]))
            elif value != self.answer[index]:
                wrong.append(index)
                ghosts.append((index, self.answer[index]))
        return Verdict(not wrong and not missing, tuple(wrong), tuple(missing), tuple(ghosts))

    def next_needed(self, cake: PatternCake) -> str | None:
        for index in range(self.given, len(self.answer)):
            if cake.cell(index) != self.answer[index]:
                return self.answer[index]
        return None

    def demonstration(self, cake: PatternCake) -> tuple[DemoStep, ...]:
        """Walk the whole row in rhythm: the customer's start, then the child's places."""

        kinds: list[str] = []
        for topping in self.answer:
            if topping not in kinds:
                kinds.append(topping)
        steps = []
        for index, value in enumerate(cake.row()):
            tone = 1 + 2 * kinds.index(value) if value in kinds else (2 if value is not None else 0)
            steps.append(DemoStep(index, 0, 0, tone))
        return tuple(steps)

    def ghosts(self, cake: PatternCake, verdict: Verdict) -> tuple[tuple[int, str], ...]:
        return verdict.ghosts


# -- order generation ------------------------------------------------------------------


def _compatible(chosen: list[str], candidate: str) -> bool:
    return all(frozenset({candidate, other}) not in LOOKALIKES for other in chosen if other != candidate)


def _pick_toppings(rng: random.Random, count: int, avoid: tuple[str, ...] = ()) -> list[str]:
    """``count`` distinct toppings that never look alike (and not in ``avoid``)."""

    pool = [topping for topping in TOPPING_IDS if topping not in avoid]
    rng.shuffle(pool)
    chosen: list[str] = []
    for topping in pool:
        if len(chosen) == count:
            break
        if _compatible(chosen, topping) and _compatible(list(avoid), topping):
            chosen.append(topping)
    return chosen


def _pantry(rng: random.Random, needed: list[str], size: int) -> tuple[str, ...]:
    """The needed toppings plus distinct distractors, in the stable shop order."""

    extra = _pick_toppings(rng, max(0, size - len(needed)), avoid=tuple(needed))
    chosen = set(needed) | set(extra)
    return tuple(topping for topping in TOPPING_IDS if topping in chosen)


def make_count_order(spec: LevelSpec, rng: random.Random) -> CountOrder:
    kinds = rng.randint(*spec.kinds)
    toppings = _pick_toppings(rng, kinds)
    low, high = spec.count_range
    amounts = [rng.randint(low, high) for _ in toppings]
    # Keep the whole order within the rung's total by trimming the largest.
    while sum(amounts) > spec.max_total:
        largest = max(range(len(amounts)), key=lambda i: amounts[i])
        if amounts[largest] <= 1:
            break
        amounts[largest] -= 1
    items = tuple(CountItem(topping, amount) for topping, amount in zip(toppings, amounts))
    return CountOrder(items, _pantry(rng, toppings, spec.pantry), spec.pictures)


def make_pattern_order(spec: LevelSpec, rng: random.Random) -> PatternOrder:
    unit = rng.choice(spec.units)
    letters = sorted(set(unit))
    toppings = _pick_toppings(rng, len(letters))
    mapping = dict(zip(letters, toppings))
    repeats = math.ceil(PATTERN_LENGTH / len(unit))
    answer = tuple(mapping[letter] for letter in (unit * repeats)[:PATTERN_LENGTH])
    given = PATTERN_LENGTH - spec.blanks
    return PatternOrder(unit, answer, given, _pantry(rng, toppings, spec.pantry))


def make_order(kind: str, spec: LevelSpec, rng: random.Random) -> Order:
    return make_pattern_order(spec, rng) if kind == PATTERN else make_count_order(spec, rng)


def adapt_level(level: int, misses: int) -> int:
    """Next rung: a smooth round climbs, a round with many misses steps down."""

    if misses <= 1:
        level += 1
    elif misses >= 5:
        level -= 1
    return max(0, min(MAX_LEVEL, level))


# -- one round -------------------------------------------------------------------------


@dataclass(slots=True)
class BakeryRound:
    """Five customers, one order each, served one after another."""

    level: int
    orders: tuple[Order, ...]
    customers: tuple[str, ...]
    index: int = 0
    misses: int = 0  # wrong serves of the current order
    total_misses: int = 0
    served: int = 0
    first_try: int = 0
    cake: Cake = field(init=False)

    def __post_init__(self) -> None:
        if not self.orders or len(self.customers) < len(self.orders):
            raise ValueError("a round needs one customer per order")
        self.cake = self.orders[0].new_cake()

    @classmethod
    def planned(cls, level: int, rng: random.Random) -> "BakeryRound":
        level = max(0, min(MAX_LEVEL, int(level)))
        spec = LEVELS[level]
        orders = tuple(make_order(kind, spec, rng) for kind in spec.orders)
        customers = list(CUSTOMERS)
        rng.shuffle(customers)
        return cls(level, orders, tuple(customers[: len(orders)]))

    @property
    def order(self) -> Order:
        return self.orders[self.index]

    @property
    def customer(self) -> str:
        return self.customers[self.index]

    @property
    def total(self) -> int:
        return len(self.orders)

    @property
    def finished(self) -> bool:
        return self.served >= len(self.orders)

    def place(self, topping_id: str) -> Placement | None:
        if self.finished or topping_id not in self.order.pantry:
            return None
        return self.cake.place(topping_id)

    def serve(self) -> Verdict | None:
        """Judge the cake; ``None`` when it cannot be served yet."""

        if self.finished or not self.order.ready(self.cake):
            return None
        verdict = self.order.check(self.cake)
        if verdict.correct:
            self.served += 1
            if self.misses == 0:
                self.first_try += 1
        else:
            self.misses += 1
            self.total_misses += 1
        return verdict

    def next_customer(self) -> bool:
        """Move on after a served order; False when the round is over."""

        if self.served <= self.index:
            return False
        if self.served >= len(self.orders):
            return False
        self.index = self.served
        self.misses = 0
        self.cake = self.order.new_cake()
        return True


# -- the make-your-own-cake ending -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class FreeTopping:
    topping_id: str
    u: float  # -1 .. 1 across the frosting ellipse
    v: float  # -1 .. 1 back to front


def inside_frosting(u: float, v: float, margin: float = 0.86) -> bool:
    return u * u + v * v <= margin * margin


class FreeCake:
    """A cake the child decorates freely (bounded; kept as a draft)."""

    def __init__(self, toppings: tuple[FreeTopping, ...] = ()) -> None:
        self._toppings: list[FreeTopping] = list(toppings)[:FREE_LIMIT]

    @property
    def toppings(self) -> tuple[FreeTopping, ...]:
        return tuple(self._toppings)

    @property
    def empty(self) -> bool:
        return not self._toppings

    @property
    def full(self) -> bool:
        return len(self._toppings) >= FREE_LIMIT

    def place(self, topping_id: str, u: float, v: float) -> FreeTopping | None:
        if self.full or topping_id not in TOPPING_IDS:
            return None
        u, v = float(u), float(v)
        length = math.hypot(u, v)
        if length > 0.86:  # keep it on the frosting
            u, v = u * 0.86 / length, v * 0.86 / length
        topping = FreeTopping(topping_id, round(u, 3), round(v, 3))
        self._toppings.append(topping)
        return topping

    def remove(self, index: int) -> bool:
        if not 0 <= index < len(self._toppings):
            return False
        del self._toppings[index]
        return True

    def undo(self) -> int | None:
        if not self._toppings:
            return None
        index = len(self._toppings) - 1
        del self._toppings[index]
        return index

    def clear(self) -> None:
        self._toppings.clear()

    def signature(self) -> tuple:
        return tuple((t.topping_id, t.u, t.v) for t in self._toppings)

    def to_json(self) -> list[list[object]]:
        return [[t.topping_id, t.u, t.v] for t in self._toppings]

    @classmethod
    def from_json(cls, raw: object) -> "FreeCake":
        toppings: list[FreeTopping] = []
        if isinstance(raw, list):
            for entry in raw[:FREE_LIMIT]:
                if not (isinstance(entry, list) and len(entry) == 3):
                    continue
                topping, u, v = entry
                if topping not in TOPPING_IDS:
                    continue
                if isinstance(u, bool) or isinstance(v, bool) or not isinstance(u, (int, float)) or not isinstance(v, (int, float)):
                    continue
                if not (math.isfinite(u) and math.isfinite(v)) or not inside_frosting(u, v, 0.87):
                    continue
                toppings.append(FreeTopping(topping, round(float(u), 3), round(float(v), 3)))
        return cls(tuple(toppings))


__all__ = [
    "BakeryRound",
    "Cake",
    "CountCake",
    "CountItem",
    "CountOrder",
    "DemoStep",
    "FreeCake",
    "FreeTopping",
    "Order",
    "PatternCake",
    "PatternOrder",
    "Placement",
    "Verdict",
    "adapt_level",
    "inside_frosting",
    "make_count_order",
    "make_order",
    "make_pattern_order",
]
