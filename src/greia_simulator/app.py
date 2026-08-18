"""Mac-first, portable desktop control plane for the Greia Activity Simulator."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from .device import (
    DEFAULT_CAPABILITIES,
    DEVICE_PRESETS,
    SIMULATOR_CAPABILITIES,
    SimulatedDeviceProfile,
    parse_viewport,
)
from .workspace import SimulatorWorkspace


class SimulatorDesktopApp:
    """Small control plane; the child-facing window is the real Greia shell."""

    def __init__(self, workspace: SimulatorWorkspace):
        import tkinter as tk
        from tkinter import ttk

        self._tk = tk
        self._ttk = ttk
        self.workspace = workspace
        self.process: subprocess.Popen[bytes] | None = None

        root = tk.Tk()
        self.root = root
        root.title("Greia Activity Simulator")
        root.minsize(520, 560)
        root.protocol("WM_DELETE_WINDOW", self.close)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Greia Activity Simulator", font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Real Greia Shell + synthetic device adapters").pack(anchor="w", pady=(0, 16))

        device_group = ttk.LabelFrame(frame, text="Synthetic device", padding=12)
        device_group.pack(fill="x", pady=(0, 10))

        self.preset = tk.StringVar(value=next(iter(DEVICE_PRESETS)))
        preset_box = ttk.Combobox(
            device_group,
            textvariable=self.preset,
            values=tuple(DEVICE_PRESETS),
            state="readonly",
        )
        preset_box.pack(fill="x")
        preset_box.bind("<<ComboboxSelected>>", self._preset_selected)

        self.viewport = tk.StringVar(value="1024x600")
        row = ttk.Frame(device_group)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Viewport").pack(side="left")
        ttk.Entry(row, textvariable=self.viewport, width=16).pack(side="right")

        self.interface_size = tk.StringVar(value="normal")
        size_row = ttk.Frame(device_group)
        size_row.pack(fill="x", pady=(8, 0))
        ttk.Label(size_row, text="Child interface size").pack(side="left")
        ttk.Combobox(
            size_row,
            textvariable=self.interface_size,
            values=("compact", "normal", "large"),
            width=14,
            state="readonly",
        ).pack(side="right")

        capability_group = ttk.LabelFrame(frame, text="Capabilities", padding=12)
        capability_group.pack(fill="x", pady=(0, 10))
        self.capability_vars: dict[str, object] = {}
        for index, capability in enumerate(sorted(SIMULATOR_CAPABILITIES - {"display"})):
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
        ttk.Button(buttons, text="Start / Apply", command=self.start).pack(side="left", expand=True, fill="x")
        ttk.Button(buttons, text="Restart", command=self.restart).pack(side="left", expand=True, fill="x", padx=6)
        ttk.Button(buttons, text="Stop", command=self.stop).pack(side="left", expand=True, fill="x")

        self.status = tk.StringVar(value="Choose a device/profile, then Start / Apply.")
        ttk.Label(
            frame,
            textvariable=self.status,
            wraplength=480,
            justify="left",
        ).pack(fill="x", pady=(6, 0))

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def _preset_selected(self, _event=None) -> None:
        width, height = DEVICE_PRESETS[self.preset.get()]
        self.viewport.set(f"{width}x{height}")

    def _device(self) -> SimulatedDeviceProfile:
        width, height = parse_viewport(self.viewport.get())
        capabilities = {"display"}
        for capability, variable in self.capability_vars.items():
            if variable.get():
                capabilities.add(capability)
        return SimulatedDeviceProfile(width, height, frozenset(capabilities))

    def _child_environment(self, device: SimulatedDeviceProfile) -> dict[str, str]:
        environment = dict(os.environ)
        environment.update(
            self.workspace.environment(
                device,
                interface_size=self.interface_size.get(),
            )
        )
        source_path = str(self.workspace.repo_root / "src")
        inherited = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = source_path if not inherited else os.pathsep.join((source_path, inherited))
        return environment

    def start(self) -> None:
        from tkinter import messagebox

        try:
            device = self._device()
            self.stop()
            self.process = subprocess.Popen(
                [sys.executable, "-m", "greia_simulator.child_shell"],
                cwd=self.workspace.repo_root,
                env=self._child_environment(device),
                stdin=subprocess.DEVNULL,
            )
            self.status.set(
                f"Running real Greia Shell at {device.viewport}; "
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
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)
        self.status.set("Greia Shell stopped.")

    def load_activity(self) -> None:
        from tkinter import filedialog, messagebox

        path = filedialog.askdirectory(title="Load Greia Activity folder")
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
            title="Install Greia Activity package",
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
    args = parser.parse_args(argv)
    workspace = SimulatorWorkspace(args.repo_root, args.state_dir)
    workspace.ensure()
    return SimulatorDesktopApp(workspace).run()


if __name__ == "__main__":
    raise SystemExit(main())
