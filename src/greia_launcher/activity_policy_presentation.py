from __future__ import annotations

from typing import Any

from greia_platform.activity_discovery import (
    ActivityDiscoveryError,
    ActivityDiscoveryPolicy,
    ActivityDiscoveryPolicyStore,
    ActivityDiscoveryService,
)

from .adaptive_discovery_presentation import AdaptiveActivityDiscoveryMixin
from .catalogue_view import ActivityCatalogue


class ActivityPolicyEnforcementMixin:
    """Shared safety boundary for child-visible Activity policy.

    A missing per-child policy file is a legitimate default and is handled by
    ``ActivityDiscoveryPolicyStore.read()``. A policy file that exists but is
    malformed, unreadable, an unsupported schema, or a symlink is different:
    it is invalid Parent authority and must never be reinterpreted as SHOW_ALL.

    Installed child launcher compositions inherit this boundary either through
    ``PolicyEnforcedAdaptiveActivityDiscoveryMixin`` (the normal rich Shell) or
    ``DirectActivityPolicyDiscoveryMixin`` (the emergency trusted fallback).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._discovery_policy = ActivityDiscoveryPolicy()
        self._discovery_policy_store: ActivityDiscoveryPolicyStore | None = None
        self._discovery_policy_token: tuple[str, int, int, int, int] | None = None
        self._discovery_service = ActivityDiscoveryService()

    def _policy_file_token(self) -> tuple[str, int, int, int, int] | None:
        store = self._discovery_policy_store
        if store is None and self._active_profile is not None:
            store = ActivityDiscoveryPolicyStore(
                self._active_profile.activity_discovery_policy_path
            )
        if store is None:
            return None
        try:
            stat = store.path.lstat()
        except FileNotFoundError:
            # Missing is a legitimate state and must stay distinct from an I/O
            # failure so repairing directory/file access is observable.
            return ("missing", 0, 0, 0, 0)
        except OSError as exc:
            return ("unavailable", int(exc.errno or 0), 0, 0, 0)
        # Include inode and mode as well as mtime/size. Parent writes are atomic
        # replacements, and this also guarantees that repairing a rejected
        # symlink is observable even in the unlikely event of equal size/mtime.
        return (
            "present",
            stat.st_mtime_ns,
            stat.st_size,
            stat.st_ino,
            stat.st_mode,
        )

    def _apply_policy_catalogue(
        self,
        *,
        store: ActivityDiscoveryPolicyStore,
        policy: ActivityDiscoveryPolicy,
        catalogue: ActivityCatalogue,
    ) -> None:
        self._discovery_policy_store = store
        self._discovery_policy = policy
        self._catalogue = catalogue
        self._category_id = self._catalogue.nearest_category(self._category_id)

        subcollection_id = getattr(self, "_subcollection_id", None)
        if (
            subcollection_id is not None
            and self._catalogue.subcollection(self._category_id, subcollection_id)
            is None
        ):
            self._subcollection_id = None

        self._selected = 0
        if hasattr(self, "_subcollection_selected"):
            self._subcollection_selected = 0
        self._activity_scroll_start = 0
        self._cached_activities_key = None
        self._cached_activities_surface = None
        for name in (
            "_cached_activities_targets",
            "_tile_surface_cache",
            "_backdrop_cache",
        ):
            cache = getattr(self, name, None)
            if cache is not None:
                cache.clear()
        self._discovery_policy_token = self._policy_file_token()

    def _fail_closed_policy_catalogue(
        self, store: ActivityDiscoveryPolicyStore
    ) -> None:
        # The default policy object below is only an inert in-memory placeholder;
        # it is never evaluated against Activities on this error path. An invalid
        # Parent authority yields an empty launchable catalogue until repaired.
        self._catalogue_error = True
        self._apply_policy_catalogue(
            store=store,
            policy=ActivityDiscoveryPolicy(),
            catalogue=ActivityCatalogue.from_activities(
                (),
                locale=self._active_locale,
                adaptive=False,
            ),
        )


class PolicyEnforcedAdaptiveActivityDiscoveryMixin(
    ActivityPolicyEnforcementMixin,
    AdaptiveActivityDiscoveryMixin,
):
    """Rich child discovery UI with mandatory fail-closed Parent policy."""

    def _reload_effective_catalogue(self) -> None:
        context = self._active_profile
        if context is None:
            self._catalogue = ActivityCatalogue.from_activities(self._activities)
            return

        store = ActivityDiscoveryPolicyStore(context.activity_discovery_policy_path)
        try:
            policy = store.read()
        except ActivityDiscoveryError:
            self._fail_closed_policy_catalogue(store)
            return

        effective = self._discovery_service.effective_activities(
            self._activities,
            approximate_age=context.profile.approximate_age,
            challenge_preference=context.profile.challenge_preference,
            policy=policy,
        )
        catalogue = ActivityCatalogue.from_activities(
            effective,
            locale=self._active_locale,
            previously_subdivided=policy.subdivided_collections,
        )

        # Preserve the existing adaptive-navigation hysteresis, but keep it
        # explicitly below the Parent visibility authority. Failure to persist
        # this presentation-only state may degrade grouping, never visibility.
        desired_state = frozenset(catalogue.subdivided_collection_ids)
        current_state = frozenset(policy.subdivided_collections)
        if desired_state != current_state:
            updated = policy
            for collection_id in current_state - desired_state:
                updated = updated.with_subdivision_state(collection_id, False)
            for collection_id in desired_state - current_state:
                updated = updated.with_subdivision_state(collection_id, True)
            try:
                store.write(updated)
                policy = updated
            except (ActivityDiscoveryError, OSError):
                self._catalogue_error = True

        self._apply_policy_catalogue(
            store=store,
            policy=policy,
            catalogue=catalogue,
        )


class DirectActivityPolicyDiscoveryMixin(ActivityPolicyEnforcementMixin):
    """Mandatory policy projection for the minimal trusted launcher fallback.

    The emergency path intentionally has no adaptive sub-Collection UI. It does,
    however, consume exactly the same Parent visibility/age/difficulty authority
    as the normal Shell before exposing any Activity for launch.
    """

    @property
    def _presented_activities(self):
        self._category_id = self._catalogue.nearest_category(self._category_id)
        return self._catalogue.collection(self._category_id).items

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        super()._activate_profile(profile, pygame)
        self._reload_effective_catalogue()

    def _logout(self, pygame: Any) -> None:
        self._discovery_policy = ActivityDiscoveryPolicy()
        self._discovery_policy_store = None
        self._discovery_policy_token = None
        super()._logout(pygame)

    def _rescan_if_due(self) -> bool:
        changed = super()._rescan_if_due()
        if self._active_profile is None:
            return changed
        token = self._policy_file_token()
        if token != self._discovery_policy_token:
            self._reload_effective_catalogue()
            return True
        return changed

    def _rescan_activities(self) -> bool:
        changed = super()._rescan_activities()
        if changed and self._active_profile is not None:
            self._reload_effective_catalogue()
        return changed

    def _rescan_profiles(self) -> bool:
        active_id = (
            self._active_profile.profile.profile_id
            if self._active_profile is not None
            else None
        )
        changed = super()._rescan_profiles()
        if not changed or self._active_profile is None:
            return changed
        if self._active_profile.profile.profile_id == active_id:
            self._reload_effective_catalogue()
        return changed

    def _reload_effective_catalogue(self) -> None:
        context = self._active_profile
        if context is None:
            self._catalogue = ActivityCatalogue.from_activities(
                self._activities,
                locale=self._active_locale,
                adaptive=False,
            )
            return

        store = ActivityDiscoveryPolicyStore(context.activity_discovery_policy_path)
        try:
            policy = store.read()
        except ActivityDiscoveryError:
            self._fail_closed_policy_catalogue(store)
            return

        effective = self._discovery_service.effective_activities(
            self._activities,
            approximate_age=context.profile.approximate_age,
            challenge_preference=context.profile.challenge_preference,
            policy=policy,
        )
        self._apply_policy_catalogue(
            store=store,
            policy=policy,
            catalogue=ActivityCatalogue.from_activities(
                effective,
                locale=self._active_locale,
                adaptive=False,
            ),
        )
