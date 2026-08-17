#!/usr/bin/env python3
"""Generate the keyboard layout probe table from real xkb data.

Compiles each layout with xkbcomp and extracts the character produced by the
physical key that types each probe character in the US layout. The resulting
table is written as Python source that the Greia installer imports, so layout
inference is based on the actual xkb maps shipped with the base system rather
than hand-maintained guesses.

This is a build-time developer tool, not part of the runtime installer.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

XKB_INCLUDE = "/usr/share/X11/xkb"
LAYOUTS = [
    "us", "gb", "it", "de", "es", "fr", "pt", "be",
    "cz", "dk", "fi", "no", "se", "pl", "ru", "ua", "tr", "br",
]

# Physical key positions (xkb keycode) used as probes, covering characters
# whose position differs between layouts.
PROBE_US_KEYS = ["AE02", "AE03", "AC06", "AB10", "AB01", "AD01", "AD03", "AD06"]


def compile_layout(layout: str, tmp: Path) -> Path | None:
    keymap = tmp / "xkb_keymap.km"
    keymap.write_text(
        f"""xkb_keymap {{
\txkb_keycodes  {{ include "evdev+aliases(qwerty)" }};
\txkb_types     {{ include "complete" }};
\txkb_compat    {{ include "complete" }};
\txkb_symbols   {{ include "pc+{layout}+inet(evdev)" }};
\txkb_geometry  {{ include "pc(pc105)" }};
}};
""",
        encoding="utf-8",
    )
    compiled = tmp / f"{layout}.xkb"
    result = subprocess.run(
        [
            "xkbcomp",
            "-xkb",
            "-w",
            "0",
            f"-I{XKB_INCLUDE}",
            str(keymap),
            str(compiled),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"WARN {layout}: xkbcomp failed: {result.stderr.strip()[:120]}", file=sys.stderr)
        return None
    return compiled


def extract_symbols(compiled: Path) -> dict[str, list[str]]:
    text = compiled.read_text(encoding="utf-8")
    output: dict[str, list[str]] = {}
    for match in re.finditer(r"key\s+<([A-Z0-9]+)>\s*\{(.*?)\};", text, re.DOTALL):
        keycode, body = match.group(1), match.group(2)
        symbols = re.search(r"symbols\[Group1\]\s*=\s*\[(.*?)\]", body, re.DOTALL)
        if not symbols:
            symbols = re.search(r"\[\s*(.*?)\s*\]", body, re.DOTALL)
        if not symbols:
            continue
        raw = symbols.group(1)
        chars: list[str] = []
        for token in raw.split(","):
            token = token.strip()
            if not token:
                continue
            if token in {"NoSymbol", "VoidSymbol"}:
                chars.append("")
            elif re.fullmatch(r"U[0-9A-Fa-f]{4,6}", token):
                chars.append(chr(int(token[1:], 16)))
            elif len(token) == 1:
                chars.append(token)
            else:
                chars.append(_keysym_to_char(token))
        output[keycode] = chars
    return output


_KEYSYM_TO_CHAR = {
    "aacute": "á", "agrave": "à", "adiaeresis": "ä", "aring": "å",
    "atilde": "ã", "ccedilla": "ç", "eacute": "é", "egrave": "è",
    "icircumflex": "î", "iacute": "í", "nacute": "ń", "oacute": "ó",
    "ocircumflex": "ô", "odiaeresis": "ö", "oslash": "ø", "otilde": "õ",
    "sacute": "ś", "ssharp": "ß", "uacute": "ú", "ucircumflex": "û",
    "udiaeresis": "ü", "yacute": "ý", "ydiaeresis": "ÿ", "zacute": "ź",
    "zcaron": "ž", "scaron": "š", "cacute": "ć", "ccaron": "č",
    "dcaron": "ď", "eogonek": "ę", "eng": "ŋ", "gbreve": "ğ",
    "idotless": "ı", "lacute": "ĺ", "lcaron": "ľ", "lstroke": "ł",
    "ncaron": "ň", "ntilde": "ñ", "rcaron": "ř", "rcedilla": "ŗ",
    "tcaron": "ť", "tcedilla": "ţ", "tstroke": "ŧ", "uhorn": "ư",
    "uring": "ů", "ustroke": "ű", "uogonek": "ų", "wcircumflex": "ŵ",
    "ycircumflex": "ŷ", "dead_acute": "´", "dead_grave": "`",
    "dead_circumflex": "^", "dead_tilde": "~", "dead_diaeresis": "¨",
    "dead_macron": "¯", "dead_breve": "˘", "dead_abovedot": "˙",
    "dead_caron": "ˇ", "dead_cedilla": "¸", "dead_ogonek": "˛",
    "dead_abovering": "˚", "dead_doubleacute": "˝", "dead_horn": "˛",
    "guillemotleft": "«", "guillemotright": "»", "exclamdown": "¡",
    "questiondown": "¿", "yen": "¥", "section": "§", "degree": "°",
    "masculine": "º", "minus": "-", "underscore": "_", "equal": "=",
    "plus": "+", "bracketleft": "[", "bracketright": "]", "braceleft": "{",
    "braceright": "}", "backslash": "\\", "bar": "|", "semicolon": ";",
    "colon": ":", "apostrophe": "'", "quotedbl": '"', "comma": ",",
    "less": "<", "period": ".", "greater": ">", "slash": "/",
    "question": "?", "grave": "`", "asciitilde": "~", "numbersign": "#",
    "at": "@", "sterling": "£", "euro": "€", "cent": "¢",
    "onehalf": "½", "onequarter": "¼", "threequarters": "¾",
    "cedilla": "¸", "diaeresis": "¨", "tilde": "~", "acute": "´",
    "grave": "`", "breve": "˘", "caron": "ˇ", "ogonek": "˛",
    "doubleacute": "˝", "abovedot": "˙", "macron": "¯",
}


def _keysym_to_char(token: str) -> str:
    return _KEYSYM_TO_CHAR.get(token, "")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # For each layout, emit the full keycode -> (unshifted, shifted) map.
        # Only keycodes that carry a printable character are kept.
        table: dict[str, dict[str, list[str]]] = {}
        for layout in LAYOUTS:
            compiled = compile_layout(layout, tmp)
            if compiled is None:
                continue
            symbols = extract_symbols(compiled)
            rows: dict[str, list[str]] = {}
            for keycode in sorted(symbols):
                chars = symbols[keycode]
                if not chars or not any(chars):
                    continue
                if keycode.startswith("I") and len(keycode) == 4 and keycode[1:].isdigit():
                    continue
                if keycode in {"RTRN", "SPCE", "TAB", "CAPS", "ESC", "BKSP", "DELE",
                               "LFSH", "RTSH", "LCTL", "LALT", "LMTA", "RCTL", "RALT",
                               "RMTA", "HYPR", "LVL3", "LEFT", "RGHT", "UP", "DOWN",
                               "HOME", "END", "PGUP", "PGDN", "INS", "KPEN", "KPDV"}:
                    continue
                unshifted = chars[0] if chars else ""
                shifted = chars[1] if len(chars) > 1 else ""
                if unshifted or shifted:
                    rows[keycode] = [unshifted, shifted]
            table[layout] = rows
        print("_LAYOUT_TABLE = " + repr(table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
