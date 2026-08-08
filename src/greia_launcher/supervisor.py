from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from greia_platform.activities import ActivityManifest
from greia_platform.permissions import ActivityAuthority
from greia_platform.profiles import ProfileContext


SANDBOX_ACTIVITY_ROOT = Path("/run/greia-activity-data")
SANDBOX_CUSTOMIZATION_ROOT = Path("/run/greia-customization")
PRODUCTION_ROOT = Path("/opt/greia-os")
PRODUCTION_BWRAP = Path("/usr/bin/bwrap")


@dataclass(frozen=True, slots=True)
class ActivityResult:
    activity_id: str
    return_code: int

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


class ActivitySupervisor:
    """Launch one curated activity in the shared Python runtime.

    Development runs use the host process namespace so the project remains easy
    to test on macOS. Installed Greia OS runs fail closed through bubblewrap:
    an ordinary Activity gets only its own writable `(profile_id, activity_id)`
    data namespace, sibling Activity/profile/platform state is hidden, networking
    is absent, and the host filesystem is otherwise read-only. Narrow privileged
    resources are mounted only when a validated manifest is trusted for them.

    This is deliberately an OS boundary in addition to manifest/import review.
    Python's built-in ``open()`` is sufficient to read arbitrary paths, so a
    shared Unix uid plus HOME/XDG scoping alone is not profile isolation.
    """

    def __init__(
        self,
        python_executable: Path | None = None,
        *,
        sandbox_executable: Path | None = None,
        require_sandbox: bool | None = None,
    ):
        self._python_executable = python_executable
        self._sandbox_executable = sandbox_executable
        self._require_sandbox_override = require_sandbox

    def launch(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> ActivityResult:
        executable = self._resolve_interpreter()
        sandboxed = self._sandbox_required()
        environment = self._sanitized_environment(
            manifest,
            profile,
            authority,
            sandboxed=sandboxed,
        )
        if sandboxed:
            sandbox = self._resolve_sandbox()
            if not sandbox.is_file() or not os.access(sandbox, os.X_OK):
                return ActivityResult(manifest.activity_id, 126)
            command = self._sandbox_command(
                sandbox,
                executable,
                manifest,
                profile,
                authority,
            )
            cwd: Path | None = None
        else:
            command = [str(executable), str(manifest.launch_path)]
            cwd = manifest.root
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=environment,
                check=False,
                shell=False,
            )
        except OSError:
            return ActivityResult(manifest.activity_id, 126)
        return ActivityResult(manifest.activity_id, completed.returncode)

    def _resolve_interpreter(self) -> Path:
        if self._python_executable is not None:
            return self._python_executable
        configured = os.environ.get("GREIA_CHILD_PYTHON")
        if configured:
            return Path(configured)
        installed_root = Path(os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT))).resolve()
        system_python = Path("/usr/bin/python3")
        if installed_root == PRODUCTION_ROOT and system_python.exists():
            return system_python
        return Path(sys.executable)

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
        executable: Path,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> list[str]:
        """Build the fail-closed Linux namespace boundary for an activity.

        The Activity's own data bind is established before the global profile tree
        is hidden. The active profile root itself is never mounted writable into
        the Activity namespace. Current Activities have no network capability, so
        each gets a fresh network namespace. Media is hidden unless explicitly
        declared. Privileged customization access is a separate narrow bind.
        """

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
        command.extend(
            [
                "--chdir",
                str(manifest.root),
                str(executable),
                str(manifest.launch_path),
            ]
        )
        return command

    @staticmethod
    def _sanitized_environment(
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
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
            }
        )
        if authority.has_permission("customization.manage"):
            environment["GREIA_CUSTOMIZATION_DIR"] = str(env_customization)
        if authority.has_permission("profile.manage_own"):
            environment["GREIA_AVATAR_REQUEST_PATH"] = str(env_avatar_request)
        return environment
