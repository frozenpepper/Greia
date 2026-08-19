"""Mac-first, portable desktop control plane for the Greia Activity Simulator."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from greia_platform.activities import RuntimeCatalogue
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

    def __init__(self, workspace: SimulatorWorkspace):
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
            try:
                self.stop()
            finally:
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
            # A transient profile refresh should not make the control plane fail.
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
        source_path = str(self.workspace.repo_root / "src")
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            source_path if not inherited else os.pathsep.join((source_path, inherited))
        )
        return environment

    def _child_command(self, device: SimulatedDeviceProfile) -> list[str]:
        command = [
            sys.executable,
            "-m",
            "greia_simulator.child_shell",
            "--viewport",
            device.viewport,
        ]
        for capability in sorted(device.capabilities):
            command.extend(("--capability", capability))
        return command

    def start(self) -> None:
        from tkinter import messagebox

        try:
            device = self._device()
            self._refresh_profiles()
            profile_id = self._selected_profile_id()
            self.workspace.set_interface_size(profile_id, self.interface_size.get())
            self.stop()
            self.process = subprocess.Popen(
                self._child_command(device),
                cwd=self.workspace.repo_root,
                env=self._child_environment(),
                stdin=subprocess.DEVNULL,
            )
            self.status.set(
                f"Running real Greia Shell at {device.viewport}; selected profile "
                f"UI size={self.interface_size.get()}."
            )
        except Exception as exc:
            messagebox.showerror("Greia Simulator", str(exc))
            self.status.set(f"Start failed: {exc}")

    def restart(self) -> None:
        self.start()

    def stop(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return
        code = process.poll()
        if code is not None:
            self.status.set(f"Greia Shell already exited (code {code}).")
            return

        self._stopping = True
        try:
            # SIGTERM is handled by the simulator Shell as an unwind request;
            # it shuts any active Activity down through the real supervisor first.
            process.terminate()
            try:
                process.wait(timeout=4.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
            self.status.set("Greia Shell stopped; Activity lifecycle cleanup requested.")
        finally:
            self._stopping = False

    def _poll_process_health(self) -> None:
        process = self.process
        if process is not None and not self._stopping:
            code = process.poll()
            if code is not None:
                self.process = None
                if code == 0:
                    self.status.set("Greia Shell exited cleanly.")
                else:
                    self.status.set(f"Greia Shell exited unexpectedly with code {code}.")
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
        self.stop()
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
    args = parser.parse_args(argv)
    workspace = SimulatorWorkspace(args.repo_root, args.state_dir)
    workspace.ensure(allow_repo_rebind=args.rebind_state)
    workspace.acquire_lock()
    try:
        return SimulatorDesktopApp(workspace).run()
    except Exception:
        workspace.release_lock()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
