"""Explicit runtime page catalogue for implemented encyclopedia pages."""

from __future__ import annotations

if __package__:
    from .enciclopedia_engine import PageRegistry
    from .pages.animals import AnimalsPage
    from .pages.bee import BeePage
    from .pages.body import BodyPage
    from .pages.earth import EarthPage
    from .pages.elephant import ElephantPage
    from .pages.fossils import FossilsPage
    from .pages.gears import GearsPage
    from .pages.heart import HeartPage
    from .pages.history import HistoryPage
    from .pages.home import HomePage
    from .pages.lion import LionPage
    from .pages.machines import MachinesPage
    from .pages.octopus import OctopusPage
    from .pages.saturn import SaturnPage
    from .pages.space import SpacePage
    from .pages.volcano import VolcanoPage
else:
    from enciclopedia_engine import PageRegistry
    from pages.animals import AnimalsPage
    from pages.bee import BeePage
    from pages.body import BodyPage
    from pages.earth import EarthPage
    from pages.elephant import ElephantPage
    from pages.fossils import FossilsPage
    from pages.gears import GearsPage
    from pages.heart import HeartPage
    from pages.history import HistoryPage
    from pages.home import HomePage
    from pages.lion import LionPage
    from pages.machines import MachinesPage
    from pages.octopus import OctopusPage
    from pages.saturn import SaturnPage
    from pages.space import SpacePage
    from pages.volcano import VolcanoPage

IMPLEMENTED_PAGE_IDS = (
    "home",
    "animals",
    "animals.lion",
    "animals.elephant",
    "animals.octopus",
    "animals.bee",
    "space",
    "space.saturn",
    "earth",
    "earth.volcano",
    "body",
    "body.heart",
    "machines",
    "machines.gears",
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
        SpacePage,
        SaturnPage,
        EarthPage,
        VolcanoPage,
        BodyPage,
        HeartPage,
        MachinesPage,
        GearsPage,
        HistoryPage,
        FossilsPage,
    ):
        registry.register(page_type.page_id, page_type)
    if registry.page_ids() != IMPLEMENTED_PAGE_IDS:
        raise AssertionError("runtime encyclopedia page registry drifted from implemented ledger")
    return registry
