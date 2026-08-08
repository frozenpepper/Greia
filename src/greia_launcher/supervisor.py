from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, Mapping

from greia_platform.activities import ActivityManifest
from greia_platform.permissions import ActivityAuthority
from greia_platform.profiles import ProfileContext

from .lifecycle import (
    ActivityControlChannel,
    ActivityExitReason,
    ActivityResult,
    ActivitySession,
    ActivitySessionState,
    monotonic_now,
    signal_process_group,
)
from .runtime_adapter import PythonRuntimeAdapter, RuntimeLaunchAdapter


SANDBOX_ACTIVITY_ROOT = Path("/run/greia-activity-data")
SANDBOX_CUSTOMIZATION_ROOT = Path("/run/greia-customization")
PRODUCTION_ROOT = Path("/opt/greia-os")
PRODUCTION_BWRAP = Path("/usr/bin/bwrap")


class ActivityLifecycleError(RuntimeError):
    """Raised when the platform cannot preserve the one-Activity lifecycle."""


ProcessFactory = Callable[..., subprocess.Popen[bytes]]


class ActivitySupervisor:
    """Own one Activity process from launch through cleanup.

    The supervisor is the runtime-neutral lifecycle/security owner. Runtime
    adapters choose the child runtime command; this class owns effective
    authority, Bubblewrap shape, per-launch control paths, readiness, graceful
    stop, forced process-tree termination and normalized exit results.
    """

    def __init__(
        self,
        python_executable: Path | None = None,
        *,
        sandbox_executable: Path | None = None,
        require_sandbox: bool | None = None,
        ready_timeout_seconds: float = 10.0,
        graceful_stop_seconds: float = 2.0,
        runtime_adapters: Mapping[str, RuntimeLaunchAdapter] | None = None,
        process_factory: ProcessFactory = subprocess.Popen,
    ):
        if ready_timeout_seconds <= 0:
            raise ValueError("ready_timeout_seconds must be positive")
        if graceful_stop_seconds <= 0:
            raise ValueError("graceful_stop_seconds must be positive")
        adapters = dict(runtime_adapters or {})
        adapters.setdefault("python", PythonRuntimeAdapter(python_executable))
        self._runtime_adapters = adapters
        self._sandbox_executable = sandbox_executable
        self._require_sandbox_override = require_sandbox
        self._ready_timeout_seconds = ready_timeout_seconds
        self._graceful_stop_seconds = graceful_stop_seconds
        self._process_factory = process_factory
        self._active_session: ActivitySession | None = None

    @property
    def active_session(self) -> ActivitySession | None:
        session = self._active_session
        if session is not None and not session.terminal:
            return session
        return None

    def start(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> ActivitySession:
        if self.active_session is not None:
            raise ActivityLifecycleError("only one Activity may run at a time")
        if authority.activity_id != manifest.activity_id:
            raise ActivityLifecycleError("Activity authority identity does not match manifest")

        adapter = self._runtime_adapters.get(manifest.runtime_type)
        if adapter is None:
            return self._failed_launch_session(manifest, profile, authority)

        sandboxed = self._sandbox_required()
        host_activity_data = profile.activity_data_dir(manifest.activity_id)
        child_activity_data = SANDBOX_ACTIVITY_ROOT if sandboxed else host_activity_data
        control = ActivityControlChannel.create(host_activity_data, child_activity_data)
        environment = self._sanitized_environment(
            manifest,
            profile,
            authority,
            control,
            sandboxed=sandboxed,
        )
        runtime_command = adapter.command_for(manifest)

        if sandboxed:
            sandbox = self._resolve_sandbox()
            if not sandbox.is_file() or not os.access(sandbox, os.X_OK):
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    control=control,
                )
            command = self._sandbox_command(
                sandbox,
                runtime_command.command,
                manifest,
                profile,
                authority,
            )
            cwd: Path | None = None
        else:
            command = list(runtime_command.command)
            cwd = runtime_command.cwd

        started = monotonic_now()
        try:
            process = self._process_factory(
                command,
                cwd=cwd,
                env=environment,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        except OSError:
            return self._failed_launch_session(
                manifest,
                profile,
                authority,
                control=control,
                started_at=started,
            )

        session = ActivitySession(
            activity_id=manifest.activity_id,
            package_digest=authority.package_digest,
            control=control,
            process=process,
            state=ActivitySessionState.STARTING,
            started_at=started,
            ready_deadline=started + self._ready_timeout_seconds,
            graceful_stop_seconds=self._graceful_stop_seconds,
        )
        self._active_session = session
        return session

    def poll(self, session: ActivitySession) -> ActivityResult | None:
        if session.result is not None:
            return session.result
        if self._active_session is not session:
            raise ActivityLifecycleError("session is not owned by this supervisor")
        process = session.process
        if process is None:
            raise ActivityLifecycleError("non-terminal session has no process")

        now = monotonic_now()
        return_code = process.poll()
        if return_code is not None:
            # READY is a per-launch marker, so consume it even when the child
            # exits between polling ticks. Otherwise a fast Activity can create
            # its usable surface, publish READY, and terminate before Greia
            # observes the intermediate RUNNING state.
            if session.ready_at is None and session.control.ready():
                session.ready_at = now
            return self._finish_session(session, return_code, now)

        if session.state is ActivitySessionState.STARTING:
            if session.control.ready():
                session.ready_at = now
                session.state = ActivitySessionState.RUNNING
            elif now >= session.ready_deadline:
                self.force_stop(session, ActivityExitReason.READY_TIMEOUT)

        if session.state is ActivitySessionState.STOPPING:
            requested_at = session.stop_requested_at
            if (
                requested_at is not None
                and session.forced_reason is None
                and now - requested_at >= session.graceful_stop_seconds
            ):
                self.force_stop(session, ActivityExitReason.FORCED_STOP)

        return_code = process.poll()
        if return_code is not None:
            return self._finish_session(session, return_code, monotonic_now())
        return None

    def request_stop(self, session: ActivitySession) -> ActivityResult | None:
        if session.result is not None:
            return session.result
        if self._active_session is not session:
            raise ActivityLifecycleError("session is not owned by this supervisor")
        if session.state is not ActivitySessionState.STOPPING:
            session.control.request_stop()
            session.stop_requested_at = monotonic_now()
            session.state = ActivitySessionState.STOPPING
        return self.poll(session)

    def force_stop(
        self,
        session: ActivitySession,
        reason: ActivityExitReason = ActivityExitReason.FORCED_STOP,
    ) -> ActivityResult | None:
        if session.result is not None:
            return session.result
        if self._active_session is not session:
            raise ActivityLifecycleError("session is not owned by this supervisor")
        if reason not in {
            ActivityExitReason.FORCED_STOP,
            ActivityExitReason.READY_TIMEOUT,
            ActivityExitReason.SYSTEM_SHUTDOWN,
        }:
            raise ValueError("force_stop requires a forced terminal reason")
        session.forced_reason = reason
        session.state = ActivitySessionState.STOPPING
        process = session.process
        if process is not None:
            signal_process_group(process, force=True)
            return_code = process.poll()
            if return_code is not None:
                return self._finish_session(session, return_code, monotonic_now())
        return None

    def shutdown_active(self) -> ActivityResult | None:
        session = self.active_session
        if session is None:
            return None
        return self.force_stop(session, ActivityExitReason.SYSTEM_SHUTDOWN)

    def _finish_session(
        self,
        session: ActivitySession,
        return_code: int,
        ended_at: float,
    ) -> ActivityResult:
        if session.forced_reason is not None:
            reason = session.forced_reason
        elif session.stop_requested_at is not None and return_code == 0:
            reason = ActivityExitReason.GRACEFUL_STOP
        elif return_code == 0:
            reason = ActivityExitReason.NORMAL
        else:
            reason = ActivityExitReason.CRASH

        state = (
            ActivitySessionState.EXITED
            if reason in {ActivityExitReason.NORMAL, ActivityExitReason.GRACEFUL_STOP}
            else ActivitySessionState.FAILED
        )
        result = ActivityResult(
            activity_id=session.activity_id,
            session_id=session.session_id,
            return_code=return_code,
            exit_reason=reason,
            ready=session.ready_at is not None,
            started_at=session.started_at,
            ready_at=session.ready_at,
            ended_at=ended_at,
        )
        session.state = state
        session.result = result
        session.control.cleanup()
        if self._active_session is session:
            self._active_session = None
        return result

    def _failed_launch_session(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
        *,
        control: ActivityControlChannel | None = None,
        started_at: float | None = None,
    ) -> ActivitySession:
        sandboxed = self._sandbox_required()
        host_activity_data = profile.activity_data_dir(manifest.activity_id)
        if control is None:
            control = ActivityControlChannel.create(
                host_activity_data,
                SANDBOX_ACTIVITY_ROOT if sandboxed else host_activity_data,
            )
        started = monotonic_now() if started_at is None else started_at
        ended = monotonic_now()
        result = ActivityResult(
            activity_id=manifest.activity_id,
            session_id=control.session_id,
            return_code=126,
            exit_reason=ActivityExitReason.LAUNCH_FAILURE,
            ready=False,
            started_at=started,
            ready_at=None,
            ended_at=ended,
        )
        session = ActivitySession(
            activity_id=manifest.activity_id,
            package_digest=authority.package_digest,
            control=control,
            process=None,
            state=ActivitySessionState.FAILED,
            started_at=started,
            ready_deadline=started,
            graceful_stop_seconds=self._graceful_stop_seconds,
            result=result,
        )
        control.cleanup()
        return session

    def _sandbox_required(self) -> bool:
        if self._require_sandbox_override is not None:
            return self._require_sandbox_override
        installed_root = Path(os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT))).resolve()
        return installed_root == PRODUCTION_ROOT

    def _resolve_sandbox(self) -> Path:
        if self._sandbox_executable is not None:
            return self._sandbox_executable
        configured = os.environ.get("GREIA_ACTIVITY_SANDBOX")
        return Path(configured) if configured else PRODUCTION_BWRAP

    @staticmethod
    def _sandbox_command(
        sandbox: Path,
        runtime_command: tuple[str, ...],
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> list[str]:
        command = [
            str(sandbox),
            "--die-with-parent",
            "--new-session",
            "--unshare-user",
            "--disable-userns",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-uts",
            "--ro-bind",
            "/",
            "/",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--dev-bind-try",
            "/dev/dri",
            "/dev/dri",
        ]
        if authority.has_capability("audio.basic"):
            command.extend(["--dev-bind-try", "/dev/snd", "/dev/snd"])
        activity_data = profile.activity_data_dir(manifest.activity_id)
        command.extend(
            [
                "--bind",
                str(activity_data),
                str(SANDBOX_ACTIVITY_ROOT),
                "--tmpfs",
                "/var/lib/greia-profiles",
                "--tmpfs",
                "/var/lib/greia-os",
                "--tmpfs",
                "/run/greia-os",
            ]
        )
        if authority.has_permission("customization.manage"):
            command.extend(
                [
                    "--bind",
                    str(profile.customization_dir),
                    str(SANDBOX_CUSTOMIZATION_ROOT),
                ]
            )
        if not authority.has_permission("removable_media.read"):
            command.extend(["--tmpfs", "/media/greia"])
        command.extend(["--chdir", str(manifest.root), *runtime_command])
        return command

    @staticmethod
    def _sanitized_environment(
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
        control: ActivityControlChannel,
        *,
        sandboxed: bool = False,
    ) -> dict[str, str]:
        allowed_names = {
            "DISPLAY",
            "LANG",
            "LC_ALL",
            "PULSE_SERVER",
            "SDL_AUDIODRIVER",
            "SDL_VIDEODRIVER",
            "WAYLAND_DISPLAY",
            "XAUTHORITY",
            "XDG_RUNTIME_DIR",
        }
        environment = {
            name: value for name, value in os.environ.items() if name in allowed_names
        }
        activity_data = profile.activity_data_dir(manifest.activity_id)
        cache_dir = activity_data / "cache"
        config_dir = activity_data / "config"
        data_dir = activity_data / "data"
        for path in (cache_dir, config_dir, data_dir):
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, 0o770)

        avatar_request = activity_data / ".greia" / "requests" / "avatar.json"
        if authority.has_permission("profile.manage_own"):
            avatar_request.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(avatar_request.parent, 0o770)

        if sandboxed:
            env_activity_data = SANDBOX_ACTIVITY_ROOT
            env_cache = SANDBOX_ACTIVITY_ROOT / "cache"
            env_config = SANDBOX_ACTIVITY_ROOT / "config"
            env_data = SANDBOX_ACTIVITY_ROOT / "data"
            env_customization = SANDBOX_CUSTOMIZATION_ROOT
            env_avatar_request = SANDBOX_ACTIVITY_ROOT / ".greia" / "requests" / "avatar.json"
        else:
            env_activity_data = activity_data
            env_cache = cache_dir
            env_config = config_dir
            env_data = data_dir
            env_customization = profile.customization_dir
            env_avatar_request = avatar_request

        environment.update(
            {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": str(env_activity_data),
                "XDG_CACHE_HOME": str(env_cache),
                "XDG_CONFIG_HOME": str(env_config),
                "XDG_DATA_HOME": str(env_data),
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "GREIA_OS_ROOT": os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT)),
                "GREIA_ACTIVITY_ID": manifest.activity_id,
                "GREIA_ACTIVITY_ROOT": str(manifest.root),
                "GREIA_ACTIVITY_DATA_DIR": str(env_activity_data),
                "GREIA_RUNTIME_API": manifest.api_version,
                "GREIA_ACTIVITY_CAPABILITIES": ",".join(sorted(authority.sdk_features)),
                "GREIA_PACKAGE_TRUST": authority.package_trust.value,
                "GREIA_PROFILE_ID": profile.profile.profile_id,
                "GREIA_PROFILE_NAME": profile.profile.display_name,
                "GREIA_PROFILE_AVATAR": profile.profile.avatar_id,
                "GREIA_MEDIA_ROOT": os.environ.get("GREIA_MEDIA_ROOT", "/media/greia"),
                "GREIA_ACTIVITY_SESSION_ID": control.session_id,
                "GREIA_ACTIVITY_READY_PATH": str(control.child_ready_path),
                "GREIA_ACTIVITY_STOP_PATH": str(control.child_stop_path),
            }
        )
        if authority.has_permission("customization.manage"):
            environment["GREIA_CUSTOMIZATION_DIR"] = str(env_customization)
        if authority.has_permission("profile.manage_own"):
            environment["GREIA_AVATAR_REQUEST_PATH"] = str(env_avatar_request)
        return environment
