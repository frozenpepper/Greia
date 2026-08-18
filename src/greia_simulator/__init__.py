"""Greia Activity Simulator.

The simulator is developer tooling over the real Greia platform contracts. It
supplies synthetic hardware/display adapters below the same Activity registry,
permission, profile, storage, history, lifecycle and runtime boundaries used by
Greia OS. It is not a second/fake Greia implementation and it is not hardware
or production-sandbox evidence.
"""

from .device import SimulatedDeviceProfile
from .workspace import SimulatorWorkspace

__all__ = ["SimulatedDeviceProfile", "SimulatorWorkspace"]
