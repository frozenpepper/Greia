"""Planned Greia Encyclopedia v0.1 page catalogue.

This is authoring metadata, not the final runtime registry. It gives tests and
future sessions one exact list of the 43 agreed page IDs without creating empty
placeholder page modules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedPage:
    page_id: str
    role: str
    signature_interaction: str


PLANNED_PAGES: tuple[PlannedPage, ...] = (
    PlannedPage("home", "root", "six living visual worlds"),
    PlannedPage("animals", "section", "habitat collage"),
    PlannedPage("animals.lion", "entry", "roar plus mane/paw hotspots"),
    PlannedPage("animals.elephant", "entry", "trunk spray plus size comparison"),
    PlannedPage("animals.octopus", "entry", "camouflage plus ink"),
    PlannedPage("animals.bee", "entry", "flower-to-flower pollination"),
    PlannedPage("animals.penguin", "entry", "waddle/swim toggle"),
    PlannedPage("animals.frog", "entry", "life-cycle sequence"),
    PlannedPage("space", "section", "complete major-planet Solar System orbits"),
    PlannedPage("space.sun", "entry", "rotation plus Earth scale comparison"),
    PlannedPage("space.mercury", "entry", "crater/day-night reveal"),
    PlannedPage("space.venus", "entry", "cloud/surface toggle"),
    PlannedPage("space.earth", "entry", "rotation plus day/night"),
    PlannedPage("space.moon", "entry", "phase demonstration"),
    PlannedPage("space.mars", "entry", "landmark reveal"),
    PlannedPage("space.jupiter", "entry", "bands plus Great Red Spot"),
    PlannedPage("space.saturn", "entry", "ring tilt/rotation"),
    PlannedPage("space.uranus", "entry", "sideways rotation"),
    PlannedPage("space.neptune", "entry", "bounded wind/cloud motion"),
    PlannedPage("earth", "section", "sky-to-ocean landscape"),
    PlannedPage("earth.volcano", "entry", "pressure to eruption"),
    PlannedPage("earth.rain", "entry", "water-cycle loop"),
    PlannedPage("earth.ocean", "entry", "surface-to-depth journey"),
    PlannedPage("earth.tree", "entry", "roots plus seasons"),
    PlannedPage("earth.rainbow", "entry", "sun/rain alignment"),
    PlannedPage("body", "section", "friendly body map"),
    PlannedPage("body.heart", "entry", "beat plus circulation"),
    PlannedPage("body.lungs", "entry", "breathe in/out"),
    PlannedPage("body.bones", "entry", "skeleton reveal/assemble"),
    PlannedPage("body.teeth", "entry", "tooth-shape jobs"),
    PlannedPage("body.senses", "entry", "multi-sense exploration"),
    PlannedPage("machines", "section", "interactive workshop"),
    PlannedPage("machines.gears", "entry", "linked gear train"),
    PlannedPage("machines.magnet", "entry", "attract/repel/materials"),
    PlannedPage("machines.bicycle", "entry", "pedal-chain-wheel"),
    PlannedPage("machines.airplane", "entry", "wing/airflow schematic"),
    PlannedPage("machines.bridge", "entry", "load/force-path comparison"),
    PlannedPage("history", "section", "visual journey backward in time"),
    PlannedPage("history.dinosaurs", "entry", "representative dinosaur forms"),
    PlannedPage("history.fossils", "entry", "brush reveal"),
    PlannedPage("history.mammoth", "entry", "cold-adaptation comparison"),
    PlannedPage("history.cave_paintings", "entry", "light/reveal rock art"),
    PlannedPage("history.pyramids", "entry", "layer/cross-section build"),
)


def planned_page_ids() -> tuple[str, ...]:
    """Return v0.1 page IDs in child-navigation planning order."""

    return tuple(page.page_id for page in PLANNED_PAGES)


def validate_catalogue() -> None:
    """Fail loudly if the authoring catalogue loses its core invariants."""

    ids = planned_page_ids()
    if len(ids) != 43:
        raise AssertionError(f"expected 43 v0.1 pages, found {len(ids)}")
    if len(set(ids)) != len(ids):
        raise AssertionError("duplicate page IDs in v0.1 catalogue")
    if ids[0] != "home":
        raise AssertionError("home must remain the first/root planned page")
    for section in ("animals", "space", "earth", "body", "machines", "history"):
        if section not in ids:
            raise AssertionError(f"missing required v0.1 section: {section}")
