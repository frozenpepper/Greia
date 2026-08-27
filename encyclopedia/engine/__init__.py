"""Small internal foundation for the Greia Encyclopedia authoring workstream.

This package is not yet wired into a discoverable Greia Activity. It exists to
keep the page/navigation contract explicit while Phase E1 integrates the real
Greia runtime seams.
"""

from .navigation import PageNavigator, PageRegistry
from .page import EncyclopediaPage, PageContext, PageRequest

__all__ = [
    "EncyclopediaPage",
    "PageContext",
    "PageNavigator",
    "PageRegistry",
    "PageRequest",
]
