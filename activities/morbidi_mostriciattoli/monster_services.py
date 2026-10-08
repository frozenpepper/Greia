"""Platform event publishing and gallery storage for Morbidi Mostriciattoli."""

from __future__ import annotations

import json
from typing import Any, Final, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .monster_model import (
        MAX_SAVED_PORTRAITS,
        MonsterGallery,
        MonsterRecipe,
    )
else:
    from monster_model import (
        MAX_SAVED_PORTRAITS,
        MonsterGallery,
        MonsterRecipe,
    )


STORAGE_KEY: Final[str] = "morbidi_mostriciattoli.gallery.v1"
EVENT_PORTRAIT_CREATED: Final[str] = "monster.portrait_created"


class GreiaMonsterEvents:
    """Safe emission of portrait creation events without child name leakage."""

    def portrait_created(self, session_id: str, recipe: MonsterRecipe) -> None:
        """Emit monster.portrait_created with privacy-safe boolean 'named'."""
        try:
            payload = {
                "portrait_id": recipe.portrait_id,
                "named": bool(recipe.name.strip()),
            }
            emit_activity_event(
                EVENT_PORTRAIT_CREATED,
                payload,
                idempotency_key=f"monster-portrait:{session_id}",
            )
        except Exception:
            pass


class GreiaMonsterStorage:
    """Persistence for saved monster portrait recipes."""

    def __init__(self, storage=None, key: str = STORAGE_KEY) -> None:
        self._storage = storage if storage is not None else get_storage()
        self._key = key

    def load_gallery(self) -> MonsterGallery:
        try:
            raw = self._storage.kv_get(self._key)
            if not raw:
                return MonsterGallery()

            data = json.loads(raw)
            if not isinstance(data, dict):
                return MonsterGallery()

            recipes_data = data.get("recipes")
            if not isinstance(recipes_data, list):
                return MonsterGallery()

            loaded: list[MonsterRecipe] = []
            for item in recipes_data[:MAX_SAVED_PORTRAITS]:
                if not isinstance(item, dict):
                    continue
                try:
                    r = MonsterRecipe(
                        portrait_id=str(item["portrait_id"]),
                        body_shape=str(item["body_shape"]),
                        body_color=str(item["body_color"]),
                        eyes=str(item["eyes"]),
                        mouth=str(item["mouth"]),
                        tuft=str(item["tuft"]),
                        accessory=str(item["accessory"]),
                        name=str(item.get("name", "")),
                        created_at=int(item.get("created_at", 0)),
                    )
                    loaded.append(r)
                except (KeyError, ValueError, TypeError):
                    continue

            return MonsterGallery(loaded)
        except Exception:
            return MonsterGallery()

    def save_gallery(self, gallery: MonsterGallery) -> bool:
        try:
            recipes_data = [
                {
                    "portrait_id": r.portrait_id,
                    "body_shape": r.body_shape,
                    "body_color": r.body_color,
                    "eyes": r.eyes,
                    "mouth": r.mouth,
                    "tuft": r.tuft,
                    "accessory": r.accessory,
                    "name": r.name,
                    "created_at": r.created_at,
                }
                for r in gallery.recipes[:MAX_SAVED_PORTRAITS]
            ]
            payload = {"recipes": recipes_data}
            raw = json.dumps(payload, ensure_ascii=False)
            self._storage.kv_set(self._key, raw)
            return True
        except Exception:
            return False
