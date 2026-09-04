from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from greia_platform.activities import ActivityManifest

from .lifecycle import (
    ActivityControlChannel,
    ProcessHandle,
    signal_process_group,
)
from .runtime_adapter import (
    ProcessFactory,
    RuntimeAdapterError,
    RuntimeCommand,
    RuntimeExit,
    RuntimeExitKind,
    RuntimeInvocation,
    RuntimeLifecycleBinding,
    RuntimeLifecycleSupport,
    RuntimeUnavailableError,
    RuntimeValidationError,
)


@dataclass(frozen=True, slots=True)
class WebRuntimePolicy:
    """Policy constraints for curated Web Activities."""

    forbidden_suffixes: frozenset[str] = frozenset(
        {".so", ".dll", ".dylib", ".exe", ".elf", ".bin", ".pyc"}
    )
    forbidden_file_names: frozenset[str] = frozenset(
        {".env", ".git", ".gitignore", "package.json", "node_modules"}
    )


class WebRuntimeAdapter:
    """Runtime adapter for launching HTML-based activities in kiosk mode."""

    runtime_type = "web"
    lifecycle_support = RuntimeLifecycleSupport()
    required_device_capabilities = frozenset()

    # Browser executables ordered by preference
    LINUX_CANDIDATES = (
        "chromium-shell",
        "chromium",
        "chromium-browser",
        "cog",
        "google-chrome",
        "google-chrome-stable",
        "firefox-esr",
        "firefox",
    )

    DARWIN_CANDIDATES = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "chromium",
        "google-chrome",
    )

    def __init__(
        self,
        browser_executable: Path | None = None,
        *,
        policy: WebRuntimePolicy | None = None,
        process_factory: ProcessFactory = subprocess.Popen,
    ) -> None:
        self._browser_executable = browser_executable
        self._policy = policy or WebRuntimePolicy()
        self._process_factory = process_factory

    def validate_package(self, manifest: ActivityManifest) -> None:
        if manifest.runtime_type != self.runtime_type:
            raise RuntimeValidationError(
                f"Web adapter cannot validate runtime {manifest.runtime_type!r}"
            )
        launch_path = manifest.launch_path
        if launch_path.suffix.casefold() not in {".html", ".htm"} or not launch_path.is_file():
            raise RuntimeValidationError(
                f"Web entrypoint is not an HTML file: {launch_path}"
            )

        policy = self._policy
        package_root = manifest.root.resolve()
        for path in manifest.root.rglob("*"):
            if path.is_symlink():
                resolved = path.resolve()
                if resolved != package_root and package_root not in resolved.parents:
                    raise RuntimeValidationError(
                        f"symlink in Web package escapes package root: {path}"
                    )
            if path.is_file():
                if path.suffix.casefold() in policy.forbidden_suffixes:
                    raise RuntimeValidationError(
                        f"forbidden binary or executable in Web package: {path.name}"
                    )
                if path.name.casefold() in policy.forbidden_file_names:
                    raise RuntimeValidationError(
                        f"forbidden file name in Web package: {path.name}"
                    )

    def resolve_browser(self) -> Path:
        if self._browser_executable is not None:
            if not self._browser_executable.is_file():
                raise RuntimeUnavailableError(
                    f"configured web browser does not exist: {self._browser_executable}"
                )
            return self._browser_executable

        configured = os.environ.get("GREIA_WEB_BROWSER")
        if configured:
            path = Path(configured)
            if path.is_file():
                return path
            which_path = shutil.which(configured)
            if which_path:
                return Path(which_path)
            raise RuntimeUnavailableError(
                f"GREIA_WEB_BROWSER executable not found: {configured}"
            )

        candidates = (
            self.DARWIN_CANDIDATES
            if sys.platform == "darwin"
            else self.LINUX_CANDIDATES
        )
        for name in candidates:
            if name.startswith("/"):
                path = Path(name)
                if path.is_file() and os.access(path, os.X_OK):
                    return path
            else:
                found = shutil.which(name)
                if found:
                    return Path(found)

        raise RuntimeUnavailableError(
            "no supported kiosk web browser found on system (tried: "
            + ", ".join(candidates)
            + ")"
        )

    def build_kiosk_args(self, executable: Path, entrypoint: Path) -> list[str]:
        name = executable.name.casefold()
        url = entrypoint.resolve().as_uri()

        if "cog" in name:
            return [str(executable), "--platform=wl", url]

        if "firefox" in name:
            return [
                str(executable),
                "--kiosk",
                "--private-window",
                url,
            ]

        # Default: Chromium / Chrome / chromium-shell family
        return [
            str(executable),
            "--kiosk",
            "--incognito",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-translate",
            "--disable-features=Translate",
            "--disable-component-update",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
            "--check-for-update-interval=31536000",
            "--overscroll-history-navigation=0",
            "--autoplay-policy=no-user-gesture-required",
            url,
        ]

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand:
        browser = self.resolve_browser()
        args = self.build_kiosk_args(browser, manifest.launch_path)
        return RuntimeCommand(
            command=tuple(args),
            cwd=manifest.root,
            environment=(),
        )

    def create_lifecycle_binding(
        self,
        session_id: str,
        host_activity_data: Path,
        child_activity_data: Path,
    ) -> RuntimeLifecycleBinding:
        control = ActivityControlChannel.create_for_session(
            session_id, host_activity_data, child_activity_data
        )
        return RuntimeLifecycleBinding(
            control=control,
            environment=(
                ("GREIA_ACTIVITY_READY_PATH", str(control.child_ready_path)),
                ("GREIA_ACTIVITY_STOP_PATH", str(control.child_stop_path)),
            ),
        )

    def launch(self, invocation: RuntimeInvocation) -> ProcessHandle:
        try:
            return self._process_factory(
                list(invocation.command),
                cwd=invocation.cwd,
                env=dict(invocation.environment),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        except OSError as exc:
            raise RuntimeAdapterError(
                f"Web runtime kiosk browser launch failed: {exc}"
            ) from exc

    def collect_exit(self, process: ProcessHandle) -> RuntimeExit | None:
        return_code = process.poll()
        if return_code is None:
            return None
        return RuntimeExit(
            return_code=return_code,
            kind=RuntimeExitKind.NORMAL if return_code == 0 else RuntimeExitKind.CRASH,
        )

    def force_stop(self, process: ProcessHandle) -> None:
        signal_process_group(process, force=True)

    def cleanup(self, process: ProcessHandle) -> None:
        if process.poll() is None:
            self.force_stop(process)
