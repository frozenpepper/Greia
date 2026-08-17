from __future__ import annotations

from dataclasses import dataclass

from .keyboard_layout_data import _LAYOUT_TABLE

# Greia keyboard layouts: identifier is the xkbrules layout name passed to
# setxkbmap, label is human-readable. The set is intentionally curated.
#
# Layout detection is keypress-guided but character-first. Each probe asks the
# parent to TYPE a specific character (e.g. "/" or "-"); the installer records
# the physical scancode they pressed and the character that resulted. Every
# candidate layout is then scored by whether that layout would produce the same
# character on the same physical key at the same shift level. This works for
# any keyboard regardless of where the character sits, because the parent types
# the character rather than being told which key to press.
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
    """One character the parent types to identify their keyboard.

    ``character`` is what the parent is asked to type. We record the physical
    scancode they used and the resulting character; layouts are scored by
    agreement on (character, scancode, shift).
    """

    character: str

    @property
    def instruction(self) -> str:
        return f"Press the key that types “{self.character}”"


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

# Probe sequence. Ordered most-discriminating first. Each probe is a character
# the parent types; we record the physical scancode + produced character. These
# characters sit on different physical keys across layout families, which is
# what makes them discriminating. See the generated xkb table for the exact
# per-layout positions (build/gen-keyboard-layout-table.py).
#
# The set covers every layout family without requiring the parent to know where
# any key is: they simply type the character, wherever their keyboard puts it.
PROBES: tuple[LayoutProbe, ...] = (
    # '/' : Shift+7 (continental), /? key (us/gb/pl), Shift+. (fr/be), etc.
    LayoutProbe("/"),
    # ';' : ; key (us/gb/pl), . key (continental), m key (fr/be), 7 key (ru/ua), etc.
    LayoutProbe(";"),
    # '-' : - key (us/gb/pl/br), / key (continental), 6 key (fr), = key (be/tr)
    LayoutProbe("-"),
    # '?' : / key (us/gb/pl), - key (continental), q key (fr/be), 7 key (ru/ua)
    LayoutProbe("?"),
    # 'z' : z key (QWERTY), y key (QWERTZ de/cz), w key (AZERTY fr/be)
    LayoutProbe("z"),
    # '@' : Shift+2 (us/pl/br), Shift+' (gb), AltGr (many continental)
    LayoutProbe("@"),
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


def _character_for_layout(layout_id: str, keycode: str, shift: bool) -> str:
    chars = _LAYOUT_TABLE.get(layout_id, {}).get(keycode)
    if not chars:
        return ""
    level = 1 if shift else 0
    return chars[level] if len(chars) > level else ""


def _score_probes(
    probe_results: dict[str, tuple[int, bool, str]],
) -> dict[str, int]:
    scores: dict[str, int] = {}
    for character, produced in probe_results.items():
        if not isinstance(produced, (tuple, list)) or len(produced) < 3:
            continue
        scancode, shift_held = int(produced[0]), bool(produced[1])
        keycode = _HID_TO_XKB.get(scancode)
        if not keycode:
            continue
        # The parent pressed the physical key that types `character` on their
        # keyboard. We recorded the physical scancode and shift state; the
        # character the active layout produced is deliberately ignored because
        # that layout may be wrong. A candidate layout agrees if IT produces
        # `character` on that same physical key at the same shift level.
        for layout_id in _LAYOUT_TABLE:
            if _character_for_layout(layout_id, keycode, shift_held) == character:
                scores[layout_id] = scores.get(layout_id, 0) + 1
    return scores


def infer_layout(probe_results: dict[str, tuple[int, bool, str]]) -> str:
    """Infer the layout from character -> (scancode, shift_held, character).

    The parent typed each probe character; we recorded the physical scancode,
    shift state, and the character produced. A candidate layout is scored by
    whether it produces the same character on the same physical key at the same
    shift level. The layout agreeing with the most probes wins; ties resolve by
    the preference order.
    """

    if not probe_results:
        return "us"
    scores = _score_probes(probe_results)
    if not scores:
        return "us"
    best = max(scores.values())
    candidates = [layout_id for layout_id, score in scores.items() if score == best]
    if "us" in candidates:
        return "us"
    return _preferred(candidates)


def layout_candidates(probe_results: dict[str, tuple[int, bool, str]]) -> tuple[str, ...]:
    """Return layout ids ordered by probe agreement (best first)."""

    if not probe_results:
        return ("us",)
    scores = _score_probes(probe_results)
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
