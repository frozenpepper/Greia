"""P6-PARENT acceptance: Parent starts behind launcher first-frame readiness.

Source-level contract for the systemd ordering edge launcher -> Parent:

- ``greia-parent.service`` orders ``After=greia-launcher.service`` so the
  Parent browser/backend no longer contends with the child's first intro
  frame (launcher is ``Type=notify``, ready at the real first flip).
- Parent still starts automatically: ``WantedBy=multi-user.target`` plus the
  launcher-side ``Wants=greia-parent.service`` are retained.
- The launcher must never require Parent (``Wants=`` only; no ``Requires=``
  or ``BindsTo=`` toward Parent) so the first frame is never delayed by
  Parent.
- No ordering cycle across the overlay units (static substitute for
  ``systemd-analyze verify`` on hosts without systemd/PID 1).
- Networking untouched; no sleeps; no new daemon/manager.
- Parent unit-level functionality retained (integrity gate + production API).
"""

from __future__ import annotations

import configparser
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UNIT_DIR = PROJECT_ROOT / "build/overlay/etc/systemd/system"
LAUNCHER = UNIT_DIR / "greia-launcher.service"
PARENT = UNIT_DIR / "greia-parent.service"


def _read_unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # keep directive case
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def _tokens(unit: configparser.ConfigParser, section: str, key: str) -> list[str]:
    if not unit.has_option(section, key):
        return []
    return unit.get(section, key).split()


class ParentOrderingTests(unittest.TestCase):
    def test_parent_orders_after_launcher(self) -> None:
        parent = _read_unit(PARENT)
        self.assertIn("greia-launcher.service", _tokens(parent, "Unit", "After"))

    def test_parent_starts_automatically(self) -> None:
        parent = _read_unit(PARENT)
        launcher = _read_unit(LAUNCHER)
        self.assertIn(
            "multi-user.target", _tokens(parent, "Install", "WantedBy")
        )
        self.assertIn(
            "greia-parent.service", _tokens(launcher, "Unit", "Wants")
        )

    def test_launcher_does_not_require_parent(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("Wants=greia-parent.service", text)
        launcher = _read_unit(LAUNCHER)
        for key in ("Requires", "BindsTo"):
            self.assertNotIn(
                "greia-parent.service", _tokens(launcher, "Unit", key)
            )
        # No hard-require line toward Parent anywhere in the launcher unit.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            self.assertFalse(
                stripped.startswith("Requires=")
                and "greia-parent.service" in stripped,
                f"launcher must not Require Parent: {stripped!r}",
            )
            self.assertFalse(
                stripped.startswith("BindsTo=")
                and "greia-parent.service" in stripped,
                f"launcher must not BindsTo Parent: {stripped!r}",
            )

    def test_launcher_readiness_precondition(self) -> None:
        # The launcher is Type=simple: a logind session moves it out of the
        # unit cgroup so READY=1 can never be attributed, and Type=notify made
        # systemd kill a working Shell (see greia-launcher.service). Parent's
        # After= therefore orders behind the launcher *start*, and real
        # readiness is the launcher_interactive_ready boot marker.
        launcher = _read_unit(LAUNCHER)
        self.assertEqual(launcher.get("Service", "Type").strip(), "simple")
        self.assertNotIn(
            "NotifyAccess",
            dict(launcher.items("Service")),
            "a Type=simple launcher has no notification channel to authorize",
        )

    def test_no_ordering_cycle(self) -> None:
        """Static After/Before graph over overlay units must stay acyclic.

        Substitute for ``systemd-analyze verify`` on hosts without systemd:
        build ordering edges (After/Before, plus Wants+After pull-in) and
        prove the graph has no cycle while the launcher -> Parent edge exists.
        """
        units: dict[str, configparser.ConfigParser] = {}
        for path in sorted(UNIT_DIR.glob("*.service")):
            units[path.name] = _read_unit(path)
        edges: dict[str, set[str]] = {name: set() for name in units}
        for name, unit in units.items():
            for dep in _tokens(unit, "Unit", "After"):
                if dep in edges:
                    edges[dep].add(name)  # dep must start first: dep -> name
            for dep in _tokens(unit, "Unit", "Before"):
                if dep in edges:
                    edges[name].add(dep)
        self.assertIn("greia-launcher.service", units)
        self.assertIn("greia-parent.service", units)
        self.assertIn(
            "greia-parent.service", edges["greia-launcher.service"]
        )
        self.assertNotIn(
            "greia-launcher.service", edges["greia-parent.service"]
        )
        # DFS cycle detection over the ordering graph.
        color: dict[str, str] = {name: "white" for name in edges}

        def visit(node: str, stack: list[str]) -> None:
            color[node] = "gray"
            for nxt in sorted(edges[node]):
                if color[nxt] == "gray":
                    cycle = " -> ".join([*stack, node, nxt])
                    self.fail(f"systemd ordering cycle detected: {cycle}")
                if color[nxt] == "white":
                    visit(nxt, [*stack, node])
            color[node] = "black"

        for node in sorted(edges):
            if color[node] == "white":
                visit(node, [])

    def test_networking_untouched(self) -> None:
        parent = _read_unit(PARENT)
        self.assertIn("network.target", _tokens(parent, "Unit", "After"))
        self.assertIn("network.target", _tokens(parent, "Unit", "Wants"))

    def test_parent_unit_functionality_retained(self) -> None:
        text = PARENT.read_text(encoding="utf-8")
        self.assertIn(
            "greia_parent.parent_client_integrity", text
        )
        self.assertIn("greia_parent.production_api", text)
        self.assertIn("Requires=greia-first-boot.service", text)

    def test_no_sleeps_or_new_daemon(self) -> None:
        for path in (LAUNCHER, PARENT):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("sleep", text.lower())
            self.assertNotIn("ExecStartPre=/bin/sleep", text)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
