"""Explicit runtime page catalogue for implemented encyclopedia pages."""

from __future__ import annotations

if __package__:
    from .enciclopedia_engine import PageRegistry
    from .pages.airplane import AirplanePage
    from .pages.animals import AnimalsPage
    from .pages.bee import BeePage
    from .pages.bicycle import BicyclePage
    from .pages.body import BodyPage
    from .pages.bones import BonesPage
    from .pages.bridge import BridgePage
    from .pages.earth import EarthPage
    from .pages.elephant import ElephantPage
    from .pages.fossils import FossilsPage
    from .pages.frog import FrogPage
    from .pages.gears import GearsPage
    from .pages.heart import HeartPage
    from .pages.history import HistoryPage
    from .pages.home import HomePage
    from .pages.jupiter import JupiterPage
    from .pages.lion import LionPage
    from .pages.lungs import LungsPage
    from .pages.machines import MachinesPage
    from .pages.magnet import MagnetPage
    from .pages.mars import MarsPage
    from .pages.mercury import MercuryPage
    from .pages.moon import MoonPage
    from .pages.neptune import NeptunePage
    from .pages.ocean import OceanPage
    from .pages.octopus import OctopusPage
    from .pages.penguin import PenguinPage
    from .pages.planet_earth import EarthPlanetPage
    from .pages.rain import RainPage
    from .pages.rainbow import RainbowPage
    from .pages.saturn import SaturnPage
    from .pages.senses import SensesPage
    from .pages.space import SpacePage
    from .pages.sun import SunPage
    from .pages.teeth import TeethPage
    from .pages.tree import TreePage
    from .pages.uranus import UranusPage
    from .pages.venus import VenusPage
    from .pages.volcano import VolcanoPage
else:
    from enciclopedia_engine import PageRegistry
    from pages.airplane import AirplanePage
    from pages.animals import AnimalsPage
    from pages.bee import BeePage
    from pages.bicycle import BicyclePage
    from pages.body import BodyPage
    from pages.bones import BonesPage
    from pages.bridge import BridgePage
    from pages.earth import EarthPage
    from pages.elephant import ElephantPage
    from pages.fossils import FossilsPage
    from pages.frog import FrogPage
    from pages.gears import GearsPage
    from pages.heart import HeartPage
    from pages.history import HistoryPage
    from pages.home import HomePage
    from pages.jupiter import JupiterPage
    from pages.lion import LionPage
    from pages.lungs import LungsPage
    from pages.machines import MachinesPage
    from pages.magnet import MagnetPage
    from pages.mars import MarsPage
    from pages.mercury import MercuryPage
    from pages.moon import MoonPage
    from pages.neptune import NeptunePage
    from pages.ocean import OceanPage
    from pages.octopus import OctopusPage
    from pages.penguin import PenguinPage
    from pages.planet_earth import EarthPlanetPage
    from pages.rain import RainPage
    from pages.rainbow import RainbowPage
    from pages.saturn import SaturnPage
    from pages.senses import SensesPage
    from pages.space import SpacePage
    from pages.sun import SunPage
    from pages.teeth import TeethPage
    from pages.tree import TreePage
    from pages.uranus import UranusPage
    from pages.venus import VenusPage
    from pages.volcano import VolcanoPage

IMPLEMENTED_PAGE_IDS = (
    "home",
    "animals",
    "animals.lion",
    "animals.elephant",
    "animals.octopus",
    "animals.bee",
    "animals.penguin",
    "animals.frog",
    "space",
    "space.sun",
    "space.mercury",
    "space.venus",
    "space.earth",
    "space.moon",
    "space.mars",
    "space.jupiter",
    "space.saturn",
    "space.uranus",
    "space.neptune",
    "earth",
    "earth.volcano",
    "earth.rain",
    "earth.ocean",
    "earth.tree",
    "earth.rainbow",
    "body",
    "body.heart",
    "body.lungs",
    "body.bones",
    "body.teeth",
    "body.senses",
    "machines",
    "machines.gears",
    "machines.magnet",
    "machines.bicycle",
    "machines.airplane",
    "machines.bridge",
    "history",
    "history.fossils",
)


def build_page_registry() -> PageRegistry:
    registry = PageRegistry()
    for page_type in (
        HomePage,
        AnimalsPage,
        LionPage,
        ElephantPage,
        OctopusPage,
        BeePage,
        PenguinPage,
        FrogPage,
        SpacePage,
        SunPage,
        MercuryPage,
        VenusPage,
        EarthPlanetPage,
        MoonPage,
        MarsPage,
        JupiterPage,
        SaturnPage,
        UranusPage,
        NeptunePage,
        EarthPage,
        VolcanoPage,
        RainPage,
        OceanPage,
        TreePage,
        RainbowPage,
        BodyPage,
        HeartPage,
        LungsPage,
        BonesPage,
        TeethPage,
        SensesPage,
        MachinesPage,
        GearsPage,
        MagnetPage,
        BicyclePage,
        AirplanePage,
        BridgePage,
        HistoryPage,
        FossilsPage,
    ):
        registry.register(page_type.page_id, page_type)
    if registry.page_ids() != IMPLEMENTED_PAGE_IDS:
        raise AssertionError("runtime encyclopedia page registry drifted from implemented ledger")
    return registry
