"""Explicit runtime page catalogue for implemented encyclopedia pages."""

from __future__ import annotations

if __package__:
    from .enciclopedia_engine import PageRegistry
    from .pages.animals import AnimalsPage
    from .pages.body import BodyPage
    from .pages.earth import EarthPage
    from .pages.history import HistoryPage
    from .pages.home import HomePage
    from .pages.machines import MachinesPage
    from .pages.octopus import OctopusPage
    from .pages.space import SpacePage
else:
    from enciclopedia_engine import PageRegistry
    from pages.animals import AnimalsPage
    from pages.body import BodyPage
    from pages.earth import EarthPage
    from pages.history import HistoryPage
    from pages.home import HomePage
    from pages.machines import MachinesPage
    from pages.octopus import OctopusPage
    from pages.space import SpacePage

IMPLEMENTED_PAGE_IDS = (
    "home",
    "animals",
    "animals.octopus",
    "space",
    "earth",
    "body",
    "machines",
    "history",
)


def build_page_registry() -> PageRegistry:
    registry = PageRegistry()
    for page_type in (
        HomePage,
        AnimalsPage,
        OctopusPage,
        SpacePage,
        EarthPage,
        BodyPage,
        MachinesPage,
        HistoryPage,
    ):
        registry.register(page_type.page_id, page_type)
    if registry.page_ids() != IMPLEMENTED_PAGE_IDS:
        raise AssertionError("runtime encyclopedia page registry drifted from implemented ledger")
    return registry
