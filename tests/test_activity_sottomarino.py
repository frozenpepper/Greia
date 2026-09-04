"""Tests for Sottomarino Giramondo activity domain model and dynamics."""

import sys
from pathlib import Path
import pytest

SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
ACTIVITY_DIR = Path(__file__).parent.parent / "activities" / "sottomarino_giramondo"
if str(ACTIVITY_DIR) not in sys.path:
    sys.path.insert(0, str(ACTIVITY_DIR))

from sub_model import (
    SubmarineModel,
    BiomeType,
    EncounterType,
    get_biome,
    MAX_DEPTH,
    MIN_DEPTH,
)


def test_biome_transitions():
    assert get_biome(0.0) == BiomeType.SHALLOW_REEF
    assert get_biome(24.9) == BiomeType.SHALLOW_REEF
    assert get_biome(25.0) == BiomeType.TWILIGHT_KELP
    assert get_biome(64.9) == BiomeType.TWILIGHT_KELP
    assert get_biome(65.0) == BiomeType.MIDNIGHT_ABYSS
    assert get_biome(100.0) == BiomeType.MIDNIGHT_ABYSS


def test_submarine_initial_state():
    model = SubmarineModel()
    assert model.depth == 5.0
    assert model.speed == 0.5
    assert not model.lights_on
    assert not model.sonar_active
    assert len(model.entities) >= 20
    assert model.encounter.active_type == EncounterType.NONE


def test_submarine_controls():
    model = SubmarineModel()
    
    # Toggle lights
    state = model.toggle_lights()
    assert state is True
    assert model.lights_on is True
    
    # Trigger sonar
    model.trigger_sonar()
    assert model.sonar_active is True
    
    # Speed control
    model.set_speed(1.0)
    assert model.speed == 1.0
    
    # Stop
    model.set_speed(0.0)
    assert model.speed == 0.0


def test_encounter_lifecycle():
    model = SubmarineModel()
    
    # Set octopus encounter
    model.encounter.active_type = EncounterType.OCTOPUS_HUG
    assert not model.encounter.solved
    
    # Resolving encounter
    resolved = model.resolve_encounter()
    assert resolved is True
    assert model.encounter.solved is True
    
    # Updating while solved progresses timer and clears encounter
    model.update(2.5)
    assert model.encounter.active_type == EncounterType.NONE


def test_order_condition_satisfaction():
    model = SubmarineModel()
    model.current_order.active = True
    model.current_order.order_id = "bubbles"
    model.current_order.solved = False
    
    # Wrong action does not satisfy
    assert model.check_action("horn") is False
    assert not model.current_order.solved
    
    # Correct action satisfies
    assert model.check_action("bubbles") is True
    assert model.current_order.solved is True


def test_species_fact_triggering():
    model = SubmarineModel()
    model.trigger_species_fact("dolphin")
    assert model.active_fact.species == "dolphin"
    assert model.active_fact.text_key == "voice.fact.dolphin.1"
    assert model.active_fact.cue_key == "voice.fact.dolphin.1"
    assert model.active_fact.display_timer > 0.0


def test_octopus_bubbles_resolution_no_crash():
    import os
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    from sub_app import SubmarineApp

    app = SubmarineApp()
    app.model.encounter.active_type = EncounterType.OCTOPUS_HUG
    app.model.encounter.progress = 1.0

    # Pressing bubbles during octopus encounter should resolve it cleanly without NameError or crash
    app._handle_button_press("bubbles")
    assert app.model.encounter.solved is True

    # Render frame with active/resolving encounter
    app.canvas.surface.fill((0, 0, 0))
    app.presenter.render(app.canvas.surface, app.model, app.resources, None)

