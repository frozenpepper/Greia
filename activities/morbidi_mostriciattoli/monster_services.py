"""Greia persistence and event adapters for Fluffy Monsters.

Profile-scoped Greia Storage (never a Linux file workflow):

* KV ``morbidi_mostriciattoli.gallery.v1`` — the saved friends. Schema 2 is a
  JSON object ``{"schema_version": 2, "recipes": [...]}`` with nine part IDs per
  recipe. The first release stored a JSON *string* holding ``{"recipes": [...]}``
  with six parts; it still loads (renamed IDs are mapped, missing parts get
  gentle defaults) and is written forward as schema 2 on the next change;
* KV ``morbidi_mostriciattoli.draft.v1`` — the friend being built, kept across
  Home (never a blank one);
* ``monsters/<id>.png`` — a friend's picture, written only when the child
  shares it to My Creations, and reclaimed after that friend is deleted.

Gallery writes are commit-ordered: the visible gallery changes only after the
index write succeeds; an unreadable stored catalogue is never overwritten.
"""

from __future__ import annotations

import json
from typing import Final, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .monster_content import MAX_SAVED_PORTRAITS
    from .monster_model import MonsterGallery, MonsterRecipe, valid_portrait_id
else:
    from monster_content import MAX_SAVED_PORTRAITS
    from monster_model import MonsterGallery, MonsterRecipe, valid_portrait_id


STORAGE_KEY: Final[str] = "morbidi_mostriciattoli.gallery.v1"
DRAFT_KEY: Final[str] = "morbidi_mostriciattoli.draft.v1"
SCHEMA_VERSION: Final = 2
EVENT_PORTRAIT_CREATED: Final[str] = "monster.portrait_created"


class StoragePort(Protocol):
    def load_gallery(self) -> MonsterGallery: ...
    def save_gallery(self, gallery: MonsterGallery) -> bool: ...
    def save_draft(self, recipe: MonsterRecipe | None) -> bool: ...
    def load_draft(self) -> MonsterRecipe | None: ...
    def private_png_name(self, portrait_id: str, payload: bytes) -> str: ...


class EventPort(Protocol):
    def portrait_created(self, session_id: str, recipe: MonsterRecipe) -> None: ...


def _decode(raw: object) -> object:
    """First-release values were JSON text inside the KV value."""

    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
    return raw


def _readable(value: object) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get("recipes"), list):
        return False
    version = value.get("schema_version", 1)
    return version in (1, SCHEMA_VERSION)


def picture_name(portrait_id: str) -> str:
    if not valid_portrait_id(portrait_id):
        raise ValueError("invalid portrait id")
    return f"monsters/{portrait_id}.png"


class GreiaMonsterStorage:
    """Map the gallery, the unsaved friend and shared pictures onto Greia Storage."""

    def __init__(self, storage=None, key: str = STORAGE_KEY) -> None:
        self._storage = storage if storage is not None else get_storage()
        self._key = key

    # -- gallery ----------------------------------------------------------------------

    def load_gallery(self) -> MonsterGallery:
        try:
            value = _decode(self._storage.kv_get(self._key))
        except Exception:
            return MonsterGallery()
        if not _readable(value):
            return MonsterGallery()
        loaded: list[MonsterRecipe] = []
        for item in value["recipes"][:MAX_SAVED_PORTRAITS]:  # type: ignore[index]
            recipe = MonsterRecipe.from_json(item)
            if recipe is not None:
                loaded.append(recipe)
        return MonsterGallery(loaded)

    def save_gallery(self, gallery: MonsterGallery) -> bool:
        try:
            previous = _decode(self._storage.kv_get(self._key))
        except Exception:
            return False
        if previous is not None and not _readable(previous):
            # Never overwrite an unreadable/unknown catalogue during mutation.
            return False
        payload = {
            "schema_version": SCHEMA_VERSION,
            "recipes": [recipe.to_json() for recipe in gallery.recipes[:MAX_SAVED_PORTRAITS]],
        }
        try:
            self._storage.kv_set(self._key, payload)
        except Exception:
            return False
        # Reclaim shared pictures of friends that are gone, after the commit.
        kept = {recipe.portrait_id for recipe in gallery.recipes}
        if isinstance(previous, dict):
            for item in previous.get("recipes", []):
                portrait_id = item.get("portrait_id") if isinstance(item, dict) else None
                if isinstance(portrait_id, str) and portrait_id not in kept and valid_portrait_id(portrait_id):
                    try:
                        self._storage.file_delete(picture_name(portrait_id))
                    except Exception:
                        pass
        return True

    # -- the friend being built -------------------------------------------------------

    def save_draft(self, recipe: MonsterRecipe | None) -> bool:
        """Keep the unsaved friend; ``None`` (blank or saved) clears it."""

        try:
            if recipe is None:
                remove = getattr(self._storage, "kv_delete", None)
                if self._storage.kv_get(DRAFT_KEY) is not None:
                    if callable(remove):
                        remove(DRAFT_KEY)
                    else:
                        self._storage.kv_set(DRAFT_KEY, None)
                return True
            self._storage.kv_set(DRAFT_KEY, {"schema_version": SCHEMA_VERSION, "recipe": recipe.to_json()})
            return True
        except Exception:
            return False

    def load_draft(self) -> MonsterRecipe | None:
        try:
            raw = self._storage.kv_get(DRAFT_KEY)
        except Exception:
            return None
        if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
            return None
        return MonsterRecipe.from_json(raw.get("recipe"))

    # -- shared picture -------------------------------------------------------------------

    def private_png_name(self, portrait_id: str, payload: bytes) -> str:
        """Write one saved friend's picture for trusted publication."""

        if self.load_gallery().get(portrait_id) is None:
            raise ValueError("monster is not saved")
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("monster picture is empty")
        name = picture_name(portrait_id)
        self._storage.file_write_atomic(name, payload)
        return name


class GreiaMonsterEvents:
    """Publish the creation fact without leaking the child-made name."""

    def portrait_created(self, session_id: str, recipe: MonsterRecipe) -> None:
        try:
            emit_activity_event(
                EVENT_PORTRAIT_CREATED,
                {"portrait_id": recipe.portrait_id, "named": bool(recipe.name.strip())},
                idempotency_key=f"monster-portrait:{session_id}",
            )
        except Exception:
            pass


__all__ = [
    "DRAFT_KEY",
    "EVENT_PORTRAIT_CREATED",
    "EventPort",
    "GreiaMonsterEvents",
    "GreiaMonsterStorage",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
    "StoragePort",
    "picture_name",
]
