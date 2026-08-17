from __future__ import annotations

from dataclasses import dataclass

from .keyboard_layout_data import _LAYOUT_TABLE

# Greia keyboard layouts: identifier is the xkbrules layout name passed to
# setxkbmap, label is human-readable. The set is intentionally curated.
#
# Layout detection is keypress-guided. Each probe asks the parent to type one
# character; the installer records the physical key that produced it using the
# SDL2 scancode (layout-independent). That scancode is then looked up in the
# generated keycode table, mapping each layout to the character it prints on
# every physical key. The layout whose table agrees with the parent's physical
# keys wins, regardless of which layout is currently active.


@dataclass(frozen=True, slots=True)
class KeyboardLayout:
    """A keyboard layout Greia can apply and infer."""

    id: str
    label: str

    def __post_init__(self) -> None:
        if not self.id or not all(character.isalnum() for character in self.id):
            raise ValueError("keyboard layout id must be alphanumeric")
        if not self.label:
            raise ValueError("keyboard layout label cannot be empty")


@dataclass(frozen=True, slots=True)
class LayoutProbe:
    """One character the parent types to identify their physical keyboard."""

    character: str
    shift_required: bool = False

    @property
    def prompt(self) -> str:
        prefix = "Hold Shift and press" if self.shift_required else "Press"
        return f"{prefix} the key that types “{self.character}”"


_LAYOUTS: tuple[KeyboardLayout, ...] = (
    KeyboardLayout("us", "US English"),
    KeyboardLayout("gb", "UK English"),
    KeyboardLayout("it", "Italiano"),
    KeyboardLayout("de", "Deutsch"),
    KeyboardLayout("es", "Español"),
    KeyboardLayout("fr", "Français"),
    KeyboardLayout("pt", "Português"),
    KeyboardLayout("be", "Belge / Belgisch"),
    KeyboardLayout("cz", "Čeština"),
    KeyboardLayout("dk", "Dansk"),
    KeyboardLayout("fi", "Suomi"),
    KeyboardLayout("no", "Norsk"),
    KeyboardLayout("se", "Svenska"),
    KeyboardLayout("pl", "Polski"),
    KeyboardLayout("ru", "Русский"),
    KeyboardLayout("ua", "Українська"),
    KeyboardLayout("tr", "Türkçe"),
    KeyboardLayout("br", "Português (BR)"),
)

# SDL2 scancodes are USB HID usage IDs: letters 'a'..'z' are 4..29, '1'..'0'
# are 30..39, punctuation follows. These are layout-independent physical keys.
# Map from HID scancode to xkb keycode name (generated from evdev keycodes).
_HID_TO_XKB: dict[int, str] = {
    4: "AC01", 5: "AB05", 6: "AB03", 7: "AC03", 8: "AD03", 9: "AC04",
    10: "AC05", 11: "AC06", 12: "AD08", 13: "AC07", 14: "AC08", 15: "AC09",
    16: "AB07", 17: "AB06", 18: "AD09", 19: "AD10", 20: "AD01", 21: "AD04",
    22: "AC02", 23: "AD05", 24: "AD07", 25: "AB04", 26: "AD02", 27: "AB02",
    28: "AD06", 29: "AB01", 30: "AE01", 31: "AE02", 32: "AE03", 33: "AE04",
    34: "AE05", 35: "AE06", 36: "AE07", 37: "AE08", 38: "AE09", 39: "AE10",
    45: "AE11", 46: "AE12", 47: "AD11", 48: "AD12", 49: "BKSL", 51: "AC10",
    52: "AC11", 53: "TLDE", 54: "AB08", 55: "AB09", 56: "AB10",
}


# Probe characters chosen because the physical key that types them differs
# across common layouts. Letters are used because every layout has them and
# they discriminate QWERTY vs QWERTZ vs AZERTY. Ordered most-discriminating
# first.
PROBES: tuple[LayoutProbe, ...] = (
    LayoutProbe("z"),
    LayoutProbe("y"),
    LayoutProbe("q"),
    LayoutProbe("a"),
    LayoutProbe("w"),
    LayoutProbe("m"),
    LayoutProbe("e"),
)


def available_layouts() -> tuple[KeyboardLayout, ...]:
    return _LAYOUTS


def layout_by_id(layout_id: str) -> KeyboardLayout:
    for layout in _LAYOUTS:
        if layout.id == layout_id:
            return layout
    raise LookupError(f"unknown keyboard layout: {layout_id!r}")


def _xkb_keycode(scancode: int) -> str | None:
    return _HID_TO_XKB.get(scancode)


def infer_layout(probe_results: dict[str, tuple[int, bool]]) -> str:
    """Infer the layout from probe character -> (scancode, shift_held) results.

    Each probe character was typed by the parent; we recorded the physical
    scancode and whether Shift was held. For every layout, check whether that
    physical key produces the probe character (at the recorded shift level) in
    that layout's table. The layout agreeing with the most probes wins; ties
    resolve to the smallest layout id.
    """

    if not probe_results:
        return "us"
    scores: dict[str, int] = {}
    for character, (scancode, shift_held) in probe_results.items():
        keycode_name = _HID_TO_XKB.get(scancode)
        if not keycode_name:
            continue
        level = 1 if shift_held else 0
        for layout_id, table in _LAYOUT_TABLE.items():
            chars = table.get(keycode_name)
            if chars and len(chars) > level and chars[level] == character:
                scores[layout_id] = scores.get(layout_id, 0) + 1
    if not scores:
        return "us"
    best = max(scores.values())
    candidates = [layout_id for layout_id, score in scores.items() if score == best]
    if "us" in candidates:
        return "us"
    return _preferred(candidates)


def layout_candidates(probe_results: dict[str, tuple[int, bool]]) -> tuple[str, ...]:
    """Return layout ids ordered by probe agreement (best first).

    Used by the installer confirmation step so a tied or wrong guess can be
    corrected from a short list of near matches.
    """

    if not probe_results:
        return ("us",)
    scores: dict[str, int] = {}
    for character, (scancode, shift_held) in probe_results.items():
        keycode_name = _HID_TO_XKB.get(scancode)
        if not keycode_name:
            continue
        level = 1 if shift_held else 0
        for layout_id, table in _LAYOUT_TABLE.items():
            chars = table.get(keycode_name)
            if chars and len(chars) > level and chars[level] == character:
                scores[layout_id] = scores.get(layout_id, 0) + 1
    if not scores:
        return ("us",)
    return tuple(
        layout_id
        for layout_id, _ in sorted(scores.items(), key=lambda item: (-item[1], _preference_rank(item[0])))
    )


# Ordering preference for tied layouts: most widely used first, so an ambiguous
# guess lands on the common layout rather than an alphabetically-earlier niche.
_PREFERENCE_ORDER: tuple[str, ...] = (
    "us", "gb", "de", "fr", "it", "es", "pt", "pl", "br", "nl",
    "se", "no", "dk", "fi", "cz", "be", "tr", "ru", "ua",
)


def _preference_rank(layout_id: str) -> tuple[int, str]:
    try:
        index = _PREFERENCE_ORDER.index(layout_id)
    except ValueError:
        index = len(_PREFERENCE_ORDER)
    return (index, layout_id)


def _preferred(candidates: list[str]) -> str:
    return sorted(candidates, key=_preference_rank)[0]
