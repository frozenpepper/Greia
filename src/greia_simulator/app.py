"""Mac-first, portable desktop control plane for the Greia Activity Simulator."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from greia_platform.activities import RuntimeCatalogue
from greia_platform.system_language import SUPPORTED_SYSTEM_LANGUAGES
from greia_platform.ui_preferences import UiPreferencesStore

from .device import (
    DEFAULT_CAPABILITIES,
    VIEWPORT_PRESETS,
    SimulatedDeviceProfile,
    canonical_capability_choices,
    parse_viewport,
)
from .workspace import SimulatorWorkspace


class SimulatorDesktopApp:
    """Small control plane; the child-facing window is the real Greia Shell."""

    def __init__(self, workspace: SimulatorWorkspace, initial_language: str = "it"):
        import tkinter as tk
        from tkinter import ttk

        self._tk = tk
        self._ttk = ttk
        self.workspace = workspace
        self.process: subprocess.Popen[bytes] | None = None
        self._stopping = False

        runtime = RuntimeCatalogue.load(workspace.repo_root / "runtime" / "child-runtime.toml")
        self.capability_choices = canonical_capability_choices(runtime.allowed_capabilities)

        root = tk.Tk()
        self.root = root
        root.title("Greia Activity Simulator")
        root.minsize(560, 700)
        root.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Greia Activity Simulator",
            font=("TkDefaultFont", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(frame, text="Real Greia Shell + synthetic HAL/runtime adapters").pack(
            anchor="w", pady=(0, 8)
        )
        ttk.Label(
            frame,
            text=(
                "Developer safety: this desktop simulator is NOT an untrusted-code "
                "security sandbox. Load/run only Activities and packages you trust. "
                "Capability switches test Greia semantic policy; they do not physically "
                "disable host input/filesystem access."
            ),
            wraplength=520,
            justify="left",
        ).pack(fill="x", pady=(0, 14))

        device_group = ttk.LabelFrame(frame, text="Synthetic device facts", padding=12)
        device_group.pack(fill="x", pady=(0, 10))

        self.preset = tk.StringVar(value=next(iter(VIEWPORT_PRESETS)))
        preset_box = ttk.Combobox(
            device_group,
            textvariable=self.preset,
            values=tuple(VIEWPORT_PRESETS),
            state="readonly",
        )
        preset_box.pack(fill="x")
        preset_box.bind("<<ComboboxSelected>>", self._preset_selected)
        ttk.Label(
            device_group,
            text="Viewport presets are geometry only; no CPU/RAM/GPU model is emulated.",
        ).pack(anchor="w", pady=(3, 0))

        self.viewport = tk.StringVar(value="1024x600")
        row = ttk.Frame(device_group)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Viewport").pack(side="left")
        ttk.Entry(row, textvariable=self.viewport, width=16).pack(side="right")

        profile_group = ttk.LabelFrame(frame, text="Real child profile preference", padding=12)
        profile_group.pack(fill="x", pady=(0, 10))
        self.profile_choice = tk.StringVar()
        self._profiles_by_label: dict[str, str] = {}
        self.profile_box = ttk.Combobox(
            profile_group,
            textvariable=self.profile_choice,
            state="readonly",
        )
        self.profile_box.pack(fill="x")
        self.profile_box.bind("<<ComboboxSelected>>", self._profile_selected)

        self.interface_size = tk.StringVar(value="normal")
        size_row = ttk.Frame(profile_group)
        size_row.pack(fill="x", pady=(8, 0))
        ttk.Label(size_row, text="Interface size for selected profile").pack(side="left")
        ttk.Combobox(
            size_row,
            textvariable=self.interface_size,
            values=("compact", "normal", "large"),
            width=14,
            state="readonly",
        ).pack(side="right")

        # Offer exactly the canonical released device languages.
        self._language_mapping = {
            f"{item.native_name} {item.flag} ({item.locale})": item.locale
            for item in SUPPORTED_SYSTEM_LANGUAGES
        }
        lang_row = ttk.Frame(profile_group)
        lang_row.pack(fill="x", pady=(8, 0))
        ttk.Label(lang_row, text="Language / Lingua").pack(side="left")
        default_lang_label = next(
            (k for k, v in self._language_mapping.items() if v == initial_language),
            "Italiano 🇮🇹 (it)",
        )
        self.language_choice = tk.StringVar(value=default_lang_label)
        ttk.Combobox(
            lang_row,
            textvariable=self.language_choice,
            values=tuple(self._language_mapping.keys()),
            width=18,
            state="readonly",
        ).pack(side="right")

        self._refresh_profiles()

        capability_group = ttk.LabelFrame(
            frame,
            text="Semantic Greia capabilities",
            padding=12,
        )
        capability_group.pack(fill="x", pady=(0, 10))
        self.capability_vars: dict[str, object] = {}
        visible = tuple(item for item in self.capability_choices if item != "display")
        for index, capability in enumerate(visible):
            variable = tk.BooleanVar(value=capability in DEFAULT_CAPABILITIES)
            self.capability_vars[capability] = variable
            ttk.Checkbutton(
                capability_group,
                text=capability,
                variable=variable,
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 12), pady=2)

        activity_group = ttk.LabelFrame(frame, text="Activity development", padding=12)
        activity_group.pack(fill="x", pady=(0, 10))
        ttk.Button(
            activity_group,
            text="Load Activity Folder…",
            command=self.load_activity,
        ).pack(fill="x", pady=(0, 6))
        ttk.Button(
            activity_group,
            text="Install Activity Package…",
            command=self.install_package,
        ).pack(fill="x")

        shell_group = ttk.LabelFrame(frame, text="Greia Shell", padding=12)
        shell_group.pack(fill="x", pady=(0, 10))
        buttons = ttk.Frame(shell_group)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Start / Apply", command=self.start).pack(
            side="left", expand=True, fill="x"
        )
        ttk.Button(buttons, text="Restart", command=self.restart).pack(
            side="left", expand=True, fill="x", padx=6
        )
        ttk.Button(buttons, text="Stop", command=self.stop).pack(
            side="left", expand=True, fill="x"
        )

        remote_group = ttk.LabelFrame(frame, text="Remote Web Canvas", padding=12)
        remote_group.pack(fill="x", pady=(0, 10))
        remote_row = ttk.Frame(remote_group)
        remote_row.pack(fill="x")
        ttk.Label(remote_row, text="http://127.0.0.1:8767").pack(side="left")
        ttk.Button(remote_row, text="Open in Browser", command=self.open_web_canvas).pack(
            side="right"
        )

        self.status = tk.StringVar(
            value="Choose viewport/profile/capabilities, then Start / Apply."
        )
        ttk.Label(
            frame,
            textvariable=self.status,
            wraplength=520,
            justify="left",
        ).pack(fill="x", pady=(6, 0))
        root.after(500, self._poll_process_health)

    def run(self) -> int:
        try:
            self.root.mainloop()
            return 0
        finally:
            # Never release the writer lease while an owned child is still live.
            # A failed final stop leaves the lease file intentionally fail-closed.
            if self.stop():
                self.workspace.release_lock()

    def _preset_selected(self, _event=None) -> None:
        width, height = VIEWPORT_PRESETS[self.preset.get()]
        self.viewport.set(f"{width}x{height}")

    def _refresh_profiles(self) -> None:
        current_id = self._profiles_by_label.get(self.profile_choice.get())
        profiles = self.workspace.profiles()
        mapping = {
            f"{profile.display_name} — {profile.profile_id[:8]}": profile.profile_id
            for profile in profiles
        }
        self._profiles_by_label = mapping
        labels = tuple(mapping)
        self.profile_box.configure(values=labels)
        selected = next(
            (label for label, profile_id in mapping.items() if profile_id == current_id),
            labels[0] if labels else "",
        )
        self.profile_choice.set(selected)
        self._profile_selected()

    def _selected_profile_id(self) -> str:
        profile_id = self._profiles_by_label.get(self.profile_choice.get())
        if not profile_id:
            self._refresh_profiles()
            profile_id = self._profiles_by_label.get(self.profile_choice.get())
        if not profile_id:
            raise RuntimeError("no simulator child profile is available")
        return profile_id

    def _profile_selected(self, _event=None) -> None:
        try:
            profile_id = self._profiles_by_label.get(self.profile_choice.get())
            if profile_id:
                context = self.workspace.profile_store().context(profile_id)
                current = UiPreferencesStore(context.customization_dir).read()
                self.interface_size.set(current.interface_size.value)
        except Exception:
            self.interface_size.set("normal")

    def _device(self) -> SimulatedDeviceProfile:
        width, height = parse_viewport(self.viewport.get())
        capabilities = {"display"}
        for capability, variable in self.capability_vars.items():
            if variable.get():
                capabilities.add(capability)
        canonical = set(self.capability_choices)
        unknown = capabilities - canonical
        if unknown:
            raise ValueError(
                "selected capabilities are outside canonical Greia runtime: "
                + ", ".join(sorted(unknown))
            )
        return SimulatedDeviceProfile(width, height, frozenset(capabilities))

    def _child_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment.update(self.workspace.environment())
        selected_lang_key = self.language_choice.get()
        selected_locale = self._language_mapping.get(selected_lang_key, "it")
        environment["GREIA_PROFILE_LOCALE"] = selected_locale
        environment["GREIA_DEVICE_LOCALE"] = selected_locale
        source_path = str(self.workspace.repo_root / "src")
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            source_path if not inherited else os.pathsep.join((source_path, inherited))
        )
        return environment

    def _child_command(self, device: SimulatedDeviceProfile) -> list[str]:
        selected_lang_key = self.language_choice.get()
        selected_locale = self._language_mapping.get(selected_lang_key, "it")
        command = [
            sys.executable,
            "-m",
            "greia_simulator.child_shell",
            "--viewport",
            device.viewport,
            "--language",
            selected_locale,
        ]
        for capability in sorted(device.capabilities):
            command.extend(("--capability", capability))
        return command

    def start(self) -> None:
        from tkinter import messagebox

        try:
            device = self._device()
            requested_size = self.interface_size.get()
            self._refresh_profiles()
            profile_id = self._selected_profile_id()
            self.workspace.set_interface_size(profile_id, requested_size)
            self.interface_size.set(requested_size)
            if not self.stop():
                raise RuntimeError(
                    "the previous Greia Shell is still running; stop it before restarting"
                )
            process = subprocess.Popen(
                self._child_command(device),
                cwd=self.workspace.repo_root,
                env=self._child_environment(),
                stdin=subprocess.DEVNULL,
            )
            self.process = process
            try:
                self.workspace.update_lock_child_pid(process.pid)
            except Exception:
                # Keep ownership of the actual process while trying to unwind it;
                # if cleanup cannot be confirmed, stop() remains fail-closed.
                self.stop()
                raise
            self.status.set(
                f"Running real Greia Shell at {device.viewport}; selected profile "
                f"UI size={requested_size}."
            )
        except Exception as exc:
            messagebox.showerror("Greia Simulator", str(exc))
            self.status.set(f"Start failed: {exc}")

    def restart(self) -> None:
        self.start()

    def open_web_canvas(self) -> None:
        import webbrowser
        webbrowser.open("http://127.0.0.1:8767")

    def _clear_exited_process(self, process: subprocess.Popen[bytes], code: int) -> bool:
        """Clear the workspace child lease before dropping the dead process handle."""

        try:
            self.workspace.update_lock_child_pid(None)
        except Exception as exc:
            self.process = process
            self.status.set(
                "Greia Shell exited, but workspace child ownership could not be cleared: "
                f"{exc}"
            )
            return False
        self.process = None
        return True

    def stop(self) -> bool:
        """Stop the owned Shell without dropping its handle or lease prematurely."""

        process = self.process
        if process is None:
            return True
        code = process.poll()
        if code is not None:
            if not self._clear_exited_process(process, code):
                return False
            self.status.set(f"Greia Shell already exited (code {code}).")
            return True

        self._stopping = True
        forced = False
        try:
            try:
                process.terminate()
                try:
                    code = process.wait(timeout=4.0)
                except subprocess.TimeoutExpired:
                    forced = True
                    process.kill()
                    code = process.wait(timeout=2.0)
            except Exception as exc:
                code = process.poll()
                if code is None:
                    # Retain both process handle and registered child PID.
                    self.process = process
                    self.status.set(f"Stop failed; Greia Shell is still running: {exc}")
                    return False
            assert code is not None
            if not self._clear_exited_process(process, code):
                return False
            if forced:
                self.status.set(
                    f"Greia Shell force-killed after lifecycle cleanup timeout (code {code})."
                )
            elif code == 0:
                self.status.set("Greia Shell stopped cleanly through lifecycle cleanup.")
            else:
                self.status.set(f"Greia Shell stopped with non-zero code {code}.")
            return True
        finally:
            self._stopping = False

    def _poll_process_health(self) -> None:
        process = self.process
        if process is not None and not self._stopping:
            code = process.poll()
            if code is not None:
                if self._clear_exited_process(process, code):
                    if code == 0:
                        self.status.set("Greia Shell exited cleanly.")
                    else:
                        self.status.set(
                            f"Greia Shell exited unexpectedly with code {code}."
                        )
        try:
            self.root.after(500, self._poll_process_health)
        except Exception:
            pass

    def load_activity(self) -> None:
        from tkinter import filedialog, messagebox

        path = filedialog.askdirectory(title="Load trusted Greia Activity folder")
        if not path:
            return
        try:
            registration = self.workspace.load_activity(Path(path))
            self.status.set(
                f"Loaded {registration.manifest.activity_id} "
                f"({registration.manifest.runtime_type}); the real launcher will rescan it."
            )
            if self.process is None or self.process.poll() is not None:
                self.start()
        except Exception as exc:
            messagebox.showerror("Activity validation failed", str(exc))
            self.status.set(f"Activity load failed: {exc}")

    def install_package(self) -> None:
        from tkinter import filedialog, messagebox

        path = filedialog.askopenfilename(
            title="Install trusted Greia Activity package",
            filetypes=(
                ("Greia Activity package", "*.greiaactivity"),
                ("ZIP archive", "*.zip"),
                ("All files", "*"),
            ),
        )
        if not path:
            return
        try:
            receipt = self.workspace.install_activity_package(Path(path))
            self.status.set(
                f"Installed {receipt.activity_id} {receipt.version} through the "
                "canonical ActivityPackageService."
            )
            if self.process is None or self.process.poll() is not None:
                self.start()
        except Exception as exc:
            messagebox.showerror("Activity install failed", str(exc))
            self.status.set(f"Activity install failed: {exc}")

    def close(self) -> None:
        from tkinter import messagebox

        if not self.stop():
            messagebox.showerror(
                "Greia Simulator",
                "The Greia Shell is still running or its workspace ownership record could "
                "not be cleared, so the simulator workspace remains locked. Resolve the "
                "stop/lease failure before closing the control plane.",
            )
            return
        self.root.destroy()


def default_state_root() -> Path:
    return Path.home() / ".greia-simulator"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greia Activity Simulator")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Greia source checkout (default: checkout containing this tool)",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=default_state_root(),
        help="isolated simulator state directory",
    )
    parser.add_argument(
        "--rebind-state",
        action="store_true",
        help="deliberately bind an existing inactive workspace to this checkout",
    )
    parser.add_argument(
        "--language",
        "--locale",
        default="it",
        help="initial system/profile language (e.g. it, en, es)",
    )
    args = parser.parse_args(argv)
    workspace = SimulatorWorkspace(args.repo_root, args.state_dir)
    workspace.acquire_lock(allow_repo_rebind=args.rebind_state)
    try:
        app = SimulatorDesktopApp(workspace, initial_language=args.language)
    except Exception:
        workspace.release_lock()
        raise
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
