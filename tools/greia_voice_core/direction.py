"""Editable performance defaults; identity continues to come from the saved master."""
import json
from pathlib import Path

DEFAULT_DELIVERY_FILE = Path(__file__).with_name("character_delivery.json")


def character_delivery(path: Path = DEFAULT_DELIVERY_FILE) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"lilli", "leo", "flash", "dani", "tito", "momo"}:
        raise ValueError("delivery file must define all six canonical characters")
    if any(not isinstance(value, str) or not value.strip() or len(value) > 2000 for value in data.values()):
        raise ValueError("each character needs a nonempty delivery prompt of at most 2000 characters")
    return {key: value.strip() for key, value in data.items()}
