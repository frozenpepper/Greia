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


PolicyFileToken = tuple[str, int, int, int, int]
_POLICY_RETRY_TOKEN: PolicyFileToken = ("retry", 0, 0, 0, 0)


class _PolicyChangedDuringRead(ActivityDiscoveryError):
    """The atomic policy file was replaced while one snapshot was being read."""


class ActivityPolicyEnforcementMixin:
    """Shared safety boundary for every child-visible Activity catalogue.

    A missing per-child policy file is a legitimate default and is handled by
    ``ActivityDiscoveryPolicyStore.read()``. A policy file that exists but is
    malformed, unreadable, an unsupported schema, or a symlink is different:
    it is invalid Parent authority and must never be reinterpreted as SHOW_ALL.

    This class deliberately owns the profile-activation and bounded-rescan
    lifecycle for policy projection. Presentation mixins downstream may choose
    direct or adaptive catalogue layout, but they do not read, write, recover,
    or poll Parent policy themselves.

    Installed child launcher compositions inherit this boundary either through
    ``PolicyEnforcedAdaptiveActivityDiscoveryMixin`` (the normal rich Shell) or
    ``DirectActivityPolicyDiscoveryMixin`` (the emergency trusted fallback).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._discovery_policy = ActivityDiscoveryPolicy()
        self._discovery_policy_store: ActivityDiscoveryPolicyStore | None = None
        self._discovery_policy_token: PolicyFileToken | None = None
        self._discovery_service = ActivityDiscoveryService()
        self._activity_policy_error = False

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        super()._activate_profile(profile, pygame)
        self._reload_effective_catalogue()

    def _logout(self, pygame: Any) -> None:
        self._discovery_policy = ActivityDiscoveryPolicy()
        self._discovery_policy_store = None
        self._discovery_policy_token = None
        if self._activity_policy_error:
            self._catalogue_error = False
        self._activity_policy_error = False
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
        """Project the active Parent policy into the presentation catalogue."""
        raise NotImplementedError

    @staticmethod
    def _policy_file_token_for(store: ActivityDiscoveryPolicyStore) -> PolicyFileToken:
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

    def _policy_file_token(self) -> PolicyFileToken | None:
        store = self._discovery_policy_store
        if store is None and self._active_profile is not None:
            store = ActivityDiscoveryPolicyStore(
                self._active_profile.activity_discovery_policy_path
            )
        if store is None:
            return None
        return self._policy_file_token_for(store)

    def _read_policy_snapshot(
        self, store: ActivityDiscoveryPolicyStore
    ) -> tuple[ActivityDiscoveryPolicy, PolicyFileToken]:
        """Read one policy version without acknowledging a different replacement.

        Parent writes replace the JSON atomically. The launcher brackets the
        read with lstat-derived identity tokens so a replacement that lands
        during the read is retried instead of applying old policy while storing
        the newer file's token. Two bounded attempts avoid an unbounded UI-path
        loop; repeated churn fails closed and is retried on the next normal
        rescan.
        """

        for _ in range(2):
            before = self._policy_file_token_for(store)
            try:
                policy = store.read()
            except ActivityDiscoveryError:
                after = self._policy_file_token_for(store)
                if before != after:
                    continue
                raise
            after = self._policy_file_token_for(store)
            if before == after:
                return policy, after
        raise _PolicyChangedDuringRead(
            "Activity discovery policy changed repeatedly while being read"
        )

    def _apply_policy_catalogue(
        self,
        *,
        store: ActivityDiscoveryPolicyStore,
        policy: ActivityDiscoveryPolicy,
        catalogue: ActivityCatalogue,
        token: PolicyFileToken | None = None,
        clear_policy_error: bool = True,
    ) -> None:
        if clear_policy_error:
            if self._activity_policy_error:
                # Do not leave a stale error badge after the rejected Parent
                # policy has been repaired and a valid snapshot is active.
                self._catalogue_error = False
            self._activity_policy_error = False

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
        self._discovery_policy_token = (
            token if token is not None else self._policy_file_token_for(store)
        )

    def _fail_closed_policy_catalogue(
        self,
        store: ActivityDiscoveryPolicyStore,
        *,
        token: PolicyFileToken | None = None,
    ) -> None:
        # The default policy object below is only an inert in-memory placeholder;
        # it is never evaluated against Activities on this error path. An invalid
        # Parent authority yields an empty launchable catalogue until repaired.
        self._activity_policy_error = True
        self._catalogue_error = True
        self._apply_policy_catalogue(
            store=store,
            policy=ActivityDiscoveryPolicy(),
            catalogue=ActivityCatalogue.from_activities(
                (),
                locale=self._active_locale,
                adaptive=False,
            ),
            token=token,
            clear_policy_error=False,
        )

    def _load_policy_or_fail_closed(
        self, store: ActivityDiscoveryPolicyStore
    ) -> tuple[ActivityDiscoveryPolicy, PolicyFileToken] | None:
        try:
            return self._read_policy_snapshot(store)
        except _PolicyChangedDuringRead:
            # Force the next normal rescan to retry even if the last replacement
            # has already settled by the time this failure is presented.
            self._fail_closed_policy_catalogue(store, token=_POLICY_RETRY_TOKEN)
        except ActivityDiscoveryError:
            self._fail_closed_policy_catalogue(
                store,
                token=self._policy_file_token_for(store),
            )
        return None


class PolicyEnforcedAdaptiveActivityDiscoveryMixin(
    ActivityPolicyEnforcementMixin,
    AdaptiveActivityDiscoveryMixin,
):
    """Rich child discovery UI with mandatory fail-closed Parent policy.

    Adaptive sub-Collection hysteresis is launcher-owned presentation state. An
    older persisted ``subdivided_collections`` value is accepted once as a
    compatibility seed when a profile becomes active, but the child Shell never
    writes presentation state back into the Parent policy file. This keeps a
    concurrent Parent visibility/age/difficulty mutation from being overwritten
    by a stale Shell policy snapshot.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._adaptive_subdivision_state: frozenset[str] | None = None

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        self._adaptive_subdivision_state = None
        super()._activate_profile(profile, pygame)

    def _logout(self, pygame: Any) -> None:
        self._adaptive_subdivision_state = None
        super()._logout(pygame)

    def _reload_effective_catalogue(self) -> None:
        context = self._active_profile
        if context is None:
            self._adaptive_subdivision_state = None
            self._catalogue = ActivityCatalogue.from_activities(self._activities)
            self._activity_policy_error = False
            return

        store = ActivityDiscoveryPolicyStore(context.activity_discovery_policy_path)
        snapshot = self._load_policy_or_fail_closed(store)
        if snapshot is None:
            return
        policy, policy_token = snapshot

        effective = self._discovery_service.effective_activities(
            self._activities,
            approximate_age=context.profile.approximate_age,
            challenge_preference=context.profile.challenge_preference,
            policy=policy,
        )
        if self._adaptive_subdivision_state is None:
            # Compatibility only: older launcher versions stored presentation
            # hysteresis in the Parent policy object. Seed from it once, then
            # keep ownership in-memory for the active Shell/profile lifetime.
            self._adaptive_subdivision_state = frozenset(
                policy.subdivided_collections
            )
        catalogue = ActivityCatalogue.from_activities(
            effective,
            locale=self._active_locale,
            previously_subdivided=self._adaptive_subdivision_state,
        )
        self._adaptive_subdivision_state = frozenset(
            catalogue.subdivided_collection_ids
        )

        self._apply_policy_catalogue(
            store=store,
            policy=policy,
            catalogue=catalogue,
            token=policy_token,
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

    def _reload_effective_catalogue(self) -> None:
        context = self._active_profile
        if context is None:
            self._catalogue = ActivityCatalogue.from_activities(
                self._activities,
                locale=self._active_locale,
                adaptive=False,
            )
            self._activity_policy_error = False
            return

        store = ActivityDiscoveryPolicyStore(context.activity_discovery_policy_path)
        snapshot = self._load_policy_or_fail_closed(store)
        if snapshot is None:
            return
        policy, policy_token = snapshot

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
            token=policy_token,
        )