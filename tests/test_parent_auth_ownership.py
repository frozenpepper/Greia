from __future__ import annotations

import unittest

from greia_parent.api_server import ParentApiApplication
from greia_parent.production_api import ProductionParentApiApplication
from greia_parent.server import ParentStatusApplication


class ParentAuthenticationOwnershipTests(unittest.TestCase):
    def test_api_v1_owns_shared_token_retirement(self) -> None:
        self.assertIn("_load_or_create_token", ParentApiApplication.__dict__)
        self.assertIs(
            ParentApiApplication._load_or_create_token,
            ProductionParentApiApplication._load_or_create_token,
        )
        self.assertNotIn("_load_or_create_token", ProductionParentApiApplication.__dict__)

    def test_legacy_status_server_keeps_separate_compatibility_hook(self) -> None:
        self.assertIn("_load_or_create_token", ParentStatusApplication.__dict__)
        self.assertIsNot(
            ParentStatusApplication._load_or_create_token,
            ParentApiApplication._load_or_create_token,
        )


if __name__ == "__main__":
    unittest.main()
