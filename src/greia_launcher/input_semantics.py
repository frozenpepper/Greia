from __future__ import annotations

from typing import Any, Iterable


_PREINTERACTIVE_INPUT_EVENT_NAMES = (
    "MOUSEMOTION",
    "MOUSEBUTTONDOWN",
    "MOUSEBUTTONUP",
    "MOUSEWHEEL",
    "KEYDOWN",
    "KEYUP",
    "TEXTINPUT",
    "FINGERMOTION",
    "FINGERDOWN",
    "FINGERUP",
    "MULTIGESTURE",
    "JOYAXISMOTION",
    "JOYBALLMOTION",
    "JOYHATMOTION",
    "JOYBUTTONDOWN",
    "JOYBUTTONUP",
    "CONTROLLERAXISMOTION",
    "CONTROLLERBUTTONDOWN",
    "CONTROLLERBUTTONUP",
)


def _resolved_event_types(pygame: Any, names: Iterable[str]) -> tuple[int, ...]:
    """Resolve available pygame event constants once, preserving declaration order."""

    resolved: list[int] = []
    seen: set[int] = set()
    for name in names:
        value = getattr(pygame, name, None)
        if value is None:
            continue
        try:
            event_type = int(value)
        except (TypeError, ValueError):
            continue
        if event_type in seen:
            continue
        seen.add(event_type)
        resolved.append(event_type)
    return tuple(resolved)


def discard_preinteractive_input(pygame: Any) -> None:
    """Discard stale user actions immediately before the Shell becomes interactive.

    The branded boot handoff is deliberately non-interactive. Pointer motion is
    already drained continuously by ``boot_intro`` to prevent a seven-second
    burst, but clicks, key/text input, wheel, touch and controller actions must
    not be replayed against the first Home frame after preparation completes.

    Only direct user-input events are discarded. System/lifecycle events such as
    ``QUIT``, ``VIDEORESIZE`` and window/display events remain queued. The helper
    is fail-soft because input cleanup must never become a boot-critical path.
    """

    try:
        event_mod = getattr(pygame, "event", None)
        if event_mod is None:
            return
        discarded = _resolved_event_types(pygame, _PREINTERACTIVE_INPUT_EVENT_NAMES)
        if not discarded:
            return

        clear = getattr(event_mod, "clear", None)
        if clear is not None:
            try:
                clear(discarded)
                return
            except TypeError:
                pass
            except Exception:  # noqa: BLE001 - boot cleanup is fail-soft
                return

        get = getattr(event_mod, "get", None)
        if get is None:
            return
        try:
            get(discarded)
            return
        except TypeError:
            pass
        except Exception:  # noqa: BLE001 - boot cleanup is fail-soft
            return

        # Compatibility fallback for event stand-ins exposing only unfiltered
        # get(). Never consume the full queue unless we can re-post every event
        # that is outside the stale user-input discard set.
        post = getattr(event_mod, "post", None)
        if post is None:
            return
        try:
            pending = get()
        except Exception:  # noqa: BLE001
            return
        discarded_set = set(discarded)
        for queued_event in pending:
            try:
                event_type = int(getattr(queued_event, "type", -1))
            except (TypeError, ValueError):
                event_type = -1
            if event_type in discarded_set:
                continue
            try:
                post(queued_event)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001 - input quarantine must never fail boot
        pass
