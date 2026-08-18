"""Greia child/profile and Activity launch-language policy.

This module composes localization primitives into the product-selected authority
chain without owning persistence or UI rendering.  Device/profile stores,
launcher presentation, Parent controls and runtime adapters can therefore share
one deterministic policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from .language_presentation import ContentLanguageSelection, UiLanguageSelection
from .localization import (
    ActivityLocaleSupport,
    LocaleContext,
    LocaleTag,
    LocalizationError,
    resolve_activity_locale,
)


@dataclass(frozen=True, slots=True)
class ChildLanguageContext:
    """Resolved Greia UI locale for one child session."""

    device_default: LocaleTag
    profile_override: LocaleTag | None
    ui_locale: LocaleTag

    @classmethod
    def resolve(
        cls,
        device_default: str | LocaleTag,
        profile_override: str | LocaleTag | None = None,
    ) -> "ChildLanguageContext":
        default = (
            device_default
            if isinstance(device_default, LocaleTag)
            else LocaleTag.parse(device_default)
        )
        override = (
            profile_override
            if isinstance(profile_override, LocaleTag)
            else LocaleTag.parse(profile_override)
            if profile_override is not None
            else None
        )
        return cls(default, override, override or default)


@dataclass(frozen=True, slots=True)
class ActivityContentLanguageSupport:
    """Language-sensitive Activity content independent from ordinary UI locale."""

    locales: tuple[LocaleTag, ...] = ()
    default_locale: LocaleTag | None = None
    selection: ContentLanguageSelection = ContentLanguageSelection.NONE

    def __post_init__(self) -> None:
        if len({item.value for item in self.locales}) != len(self.locales):
            raise LocalizationError("Activity content locales must be unique")
        if self.selection is ContentLanguageSelection.NONE:
            if self.locales or self.default_locale is not None:
                raise LocalizationError(
                    "content-language NONE cannot declare content locales"
                )
            return
        if not self.locales or self.default_locale is None:
            raise LocalizationError(
                "language-sensitive Activity content must declare locales and a default"
            )
        if self.default_locale not in self.locales:
            raise LocalizationError("default content locale must be declared")
        if (
            self.selection is ContentLanguageSelection.FIXED
            and len(self.locales) != 1
        ):
            raise LocalizationError(
                "fixed content language must declare exactly one locale"
            )
        if (
            self.selection is ContentLanguageSelection.PRELAUNCH_CHOOSER
            and len(self.locales) < 2
        ):
            raise LocalizationError(
                "content pre-launch chooser requires at least two locales"
            )

    @classmethod
    def none(cls) -> "ActivityContentLanguageSupport":
        return cls()

    @classmethod
    def fixed(cls, locale: str) -> "ActivityContentLanguageSupport":
        parsed = LocaleTag.parse(locale)
        return cls(
            locales=(parsed,),
            default_locale=parsed,
            selection=ContentLanguageSelection.FIXED,
        )

    @classmethod
    def selectable(
        cls,
        locales: tuple[str, ...],
        *,
        default_locale: str,
    ) -> "ActivityContentLanguageSupport":
        return cls(
            locales=tuple(LocaleTag.parse(item) for item in locales),
            default_locale=LocaleTag.parse(default_locale),
            selection=ContentLanguageSelection.PRELAUNCH_CHOOSER,
        )


@dataclass(frozen=True, slots=True)
class ActivityLanguagePolicy:
    """Resolved language capabilities/policy declared by one Activity package.

    Catalogue locales cover launcher-facing metadata such as title/description;
    they may be a superset of in-Activity UI locales.  This permits an
    English-only Activity to have an Italian launcher title.
    """

    catalogue_locales: tuple[LocaleTag, ...]
    default_catalogue_locale: LocaleTag
    ui_support: ActivityLocaleSupport
    ui_selection: UiLanguageSelection = UiLanguageSelection.FOLLOW_PROFILE
    content: ActivityContentLanguageSupport = ActivityContentLanguageSupport()
    remember_prelaunch_choice: bool = True

    def __post_init__(self) -> None:
        if not self.catalogue_locales:
            raise LocalizationError("Activity must declare at least one catalogue locale")
        if len({item.value for item in self.catalogue_locales}) != len(
            self.catalogue_locales
        ):
            raise LocalizationError("Activity catalogue locales must be unique")
        if self.default_catalogue_locale not in self.catalogue_locales:
            raise LocalizationError("default catalogue locale must be declared")
        if self.ui_support.language_neutral:
            if self.ui_selection is not UiLanguageSelection.FOLLOW_PROFILE:
                raise LocalizationError(
                    "language-neutral Activity cannot select an in-Activity UI locale"
                )
        elif (
            self.ui_selection is UiLanguageSelection.PRELAUNCH_CHOOSER
            and len(self.ui_support.ui_locales) < 2
        ):
            raise LocalizationError(
                "UI pre-launch chooser requires at least two Activity UI locales"
            )

    @classmethod
    def localized(
        cls,
        *,
        catalogue_locales: tuple[str, ...],
        default_catalogue_locale: str,
        ui_locales: tuple[str, ...],
        default_ui_locale: str,
        ui_selection: UiLanguageSelection = UiLanguageSelection.FOLLOW_PROFILE,
        content: ActivityContentLanguageSupport | None = None,
        remember_prelaunch_choice: bool = True,
    ) -> "ActivityLanguagePolicy":
        return cls(
            catalogue_locales=tuple(
                LocaleTag.parse(item) for item in catalogue_locales
            ),
            default_catalogue_locale=LocaleTag.parse(default_catalogue_locale),
            ui_support=ActivityLocaleSupport.localized(
                ui_locales,
                default_ui_locale=default_ui_locale,
            ),
            ui_selection=ui_selection,
            content=content or ActivityContentLanguageSupport.none(),
            remember_prelaunch_choice=bool(remember_prelaunch_choice),
        )

    @classmethod
    def language_neutral(
        cls,
        *,
        catalogue_locales: tuple[str, ...],
        default_catalogue_locale: str,
        content: ActivityContentLanguageSupport | None = None,
    ) -> "ActivityLanguagePolicy":
        return cls(
            catalogue_locales=tuple(
                LocaleTag.parse(item) for item in catalogue_locales
            ),
            default_catalogue_locale=LocaleTag.parse(default_catalogue_locale),
            ui_support=ActivityLocaleSupport.neutral(),
            content=content or ActivityContentLanguageSupport.none(),
        )


@dataclass(frozen=True, slots=True)
class ActivityLaunchLanguageContext:
    child: ChildLanguageContext
    catalogue_locale: LocaleTag
    ui_locale: LocaleContext | None
    content_locale: LocaleTag | None

    @property
    def activity_ui_differs_from_child(self) -> bool:
        return (
            self.ui_locale is not None
            and self.ui_locale.selected.language != self.child.ui_locale.language
        )


def resolve_activity_launch_languages(
    child: ChildLanguageContext,
    policy: ActivityLanguagePolicy,
    *,
    ui_choice: str | LocaleTag | None = None,
    content_choice: str | LocaleTag | None = None,
) -> ActivityLaunchLanguageContext:
    """Resolve launcher title, Activity UI and content languages for one launch."""

    catalogue = _resolve_supported_locale(
        child.ui_locale,
        policy.catalogue_locales,
        policy.default_catalogue_locale,
    )

    if policy.ui_support.language_neutral:
        if ui_choice is not None:
            raise LocalizationError("language-neutral Activity cannot accept UI locale choice")
        ui_context = None
    elif ui_choice is not None:
        if policy.ui_selection is not UiLanguageSelection.PRELAUNCH_CHOOSER:
            raise LocalizationError("Activity does not allow UI language selection")
        explicit = ui_choice if isinstance(ui_choice, LocaleTag) else LocaleTag.parse(ui_choice)
        if explicit not in policy.ui_support.ui_locales:
            raise LocalizationError("selected UI locale is not supported by Activity")
        # An explicit chooser selection is authoritative for this launch; use it
        # as the requested locale while preserving Activity fallback semantics.
        ui_context = resolve_activity_locale(explicit, policy.ui_support)
    else:
        ui_context = resolve_activity_locale(child.ui_locale, policy.ui_support)

    content_locale = _resolve_content_locale(policy.content, content_choice)
    return ActivityLaunchLanguageContext(
        child=child,
        catalogue_locale=catalogue,
        ui_locale=ui_context,
        content_locale=content_locale,
    )


def _resolve_content_locale(
    support: ActivityContentLanguageSupport,
    explicit_choice: str | LocaleTag | None,
) -> LocaleTag | None:
    if support.selection is ContentLanguageSelection.NONE:
        if explicit_choice is not None:
            raise LocalizationError("Activity has no content-language concept")
        return None
    assert support.default_locale is not None
    if support.selection is ContentLanguageSelection.FIXED:
        if explicit_choice is not None:
            raise LocalizationError("fixed content language cannot be overridden")
        return support.default_locale
    if explicit_choice is None:
        return support.default_locale
    explicit = (
        explicit_choice
        if isinstance(explicit_choice, LocaleTag)
        else LocaleTag.parse(explicit_choice)
    )
    if explicit not in support.locales:
        raise LocalizationError("selected content locale is not supported")
    return explicit


def _resolve_supported_locale(
    requested: LocaleTag,
    supported: tuple[LocaleTag, ...],
    default: LocaleTag,
) -> LocaleTag:
    by_value = {item.value: item for item in supported}
    for candidate in requested.fallback_chain():
        match = by_value.get(candidate.value)
        if match is not None:
            return match
    for candidate in default.fallback_chain():
        match = by_value.get(candidate.value)
        if match is not None:
            return match
    raise LocalizationError("language policy has no usable fallback")


__all__ = [
    "ActivityContentLanguageSupport",
    "ActivityLanguagePolicy",
    "ActivityLaunchLanguageContext",
    "ChildLanguageContext",
    "resolve_activity_launch_languages",
]
