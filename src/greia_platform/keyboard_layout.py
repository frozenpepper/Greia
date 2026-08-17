from __future__ import annotations

from dataclasses import dataclass

from .keyboard_layout_data import _LAYOUT_TABLE

# Greia keyboard layouts: identifier is the xkbrules layout name passed to
# setxkbmap, label is human-readable. The set is intentionally curated.
#
# Layout detection is keypress-guided. Each probe highlights a specific
# physical key (the keycode is layout-independent) and asks the parent to press
# it, optionally holding Shift. The installer records the character the current
# (possibly wrong) layout produced on that physical key. Every candidate layout
# is then scored by whether it produces the same character on the same physical
# key at the same shift level. The layout agreeing with the most probes wins,
# which is robust regardless of which layout is currently active.
#
# The probe set deliberately uses punctuation and symbols that differ between
# keyboard families (QWERTY vs AZERTY, ISO vs ANSI, continental layouts). Letter
# probes are not used because almost all layouts are QWERTY for letters.


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
    """One physical key the parent presses to identify their keyboard.

    ``keycode`` is the xkb keycode name (layout-independent physical key).
    ``shift`` requires the parent to hold Shift. ``prompt`` is a human
    description shown with a visual highlight of the physical key.
    """

    keycode: str
    shift: bool = False
    prompt: str = ""

    @property
    def instruction(self) -> str:
        prefix = "Hold Shift and press" if self.shift else "Press"
        target = self.prompt or f"the highlighted key"
        return f"{prefix} {target}"


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

_XKB_TO_HID: dict[str, int] = {keycode: scancode for scancode, keycode in _HID_TO_XKB.items()}

# Probe sequence. Ordered most-discriminating first; each probe is a physical
# key whose printed character differs between layout families. Derived from the
# generated xkb table (see build/gen-keyboard-layout-table.py).
PROBES: tuple[LayoutProbe, ...] = (
    # Shift+7: '/' on continental layouts, '&' on us/gb/pl/br, 'è' on fr/be
    LayoutProbe("AE07", shift=True, prompt="the key with 7 on it"),
    # The '/?' key: '/' on us/gb/pl, '-' on continental, ';' on br, '.' on ru/ua/tr
    LayoutProbe("AB10", prompt="the key with / on it"),
    # Shift+2: '@' on us/pl/br, '"' on gb/it/de/es/pt, 'é' on fr/be
    LayoutProbe("AE02", shift=True, prompt="the key with 2 on it"),
    # The '-' key: distinguishes fr (6 row) from continental (7 row) etc.
    LayoutProbe("AE11", prompt="the key with - on it"),
    # Shift+3: '#' on us/pl/br, '£' on gb/it/pt, '§' on de — splits it/es/pt
    LayoutProbe("AE03", shift=True, prompt="the key with 3 on it"),
    # The "'" key: distinguishes it (à), de/fi/se (ä), dk (ø), br (~)
    LayoutProbe("AC11", prompt="the key with ' on it"),
)


def available_layouts() -> tuple[KeyboardLayout, ...]:
    return _LAYOUTS


def layout_by_id(layout_id: str) -> KeyboardLayout:
    for layout in _LAYOUTS:
        if layout.id == layout_id:
            return layout
    raise LookupError(f"unknown keyboard layout: {layout_id!r}")


def probe_by_keycode(keycode: str) -> LayoutProbe | None:
    for probe in PROBES:
        if probe.keycode == keycode:
            return probe
    return None


def _xkb_keycode(scancode: int) -> str | None:
    return _HID_TO_XKB.get(scancode)


def _character_for_layout(layout_id: str, keycode: str, shift: bool) -> str:
    chars = _LAYOUT_TABLE.get(layout_id, {}).get(keycode)
    if not chars:
        return ""
    level = 1 if shift else 0
    return chars[level] if len(chars) > level else ""


def infer_layout(probe_results: dict[str, tuple[int, bool]]) -> str:
    """Infer the layout from physical key -> (scancode, shift_held) results.

    Each probe is a physical key the parent pressed (identified by the
    highlighted prompt). We recorded the scancode (physical position) and
    whether Shift was held, together with the character the current layout
    produced. For every candidate layout, check whether that physical key
    produces the same character at the same shift level. The layout agreeing
    with the most probes wins; ties resolve by the preference order.
    """

    if not probe_results:
        return "us"
    scores: dict[str, int] = {}
    for keycode, produced in probe_results.items():
        if not isinstance(produced, (tuple, list)) or len(produced) < 3:
            continue
        scancode, shift_held = produced[0], produced[1]
        observed_keycode = _HID_TO_XKB.get(scancode)
        probe = probe_by_keycode(keycode)
        if not probe or not observed_keycode or observed_keycode != probe.keycode:
            continue
        character = produced[2]
        if not character:
            continue
        for layout_id in _LAYOUT_TABLE:
            if _character_for_layout(layout_id, keycode, shift_held) == character:
                scores[layout_id] = scores.get(layout_id, 0) + 1
    if not scores:
        return "us"
    best = max(scores.values())
    candidates = [layout_id for layout_id, score in scores.items() if score == best]
    if "us" in candidates:
        return "us"
    return _preferred(candidates)


def layout_candidates(probe_results: dict[str, tuple[int, bool]]) -> tuple[str, ...]:
    """Return layout ids ordered by probe agreement (best first)."""

    if not probe_results:
        return ("us",)
    scores: dict[str, int] = {}
    for keycode, produced in probe_results.items():
        if not isinstance(produced, (tuple, list)) or len(produced) < 3:
            continue
        scancode, shift_held = produced[0], produced[1]
        probe = probe_by_keycode(keycode)
        if not probe or len(produced) < 3:
            continue
        character = produced[2]
        if not character:
            continue
        for layout_id in _LAYOUT_TABLE:
            if _character_for_layout(layout_id, keycode, shift_held) == character:
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
