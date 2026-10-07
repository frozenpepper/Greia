"""Gallery geometry: large preview cards and protected platform chrome."""
from __future__ import annotations
import unittest
from greia_platform.creation_gallery_layout import CreationGalleryLayout
from greia_platform.system_chrome import ActivitySystemChromeLayout

class CreationGalleryLayoutTests(unittest.TestCase):
    def test_multiple_resolutions_have_big_cards_and_no_chrome_collision(self):
        for width,height in ((480,320),(640,360),(800,480),(1024,600),(1280,720),(1366,768),(1920,1080)):
            with self.subTest(size=(width,height)):
                l=CreationGalleryLayout.for_surface(width,height)
                c=ActivitySystemChromeLayout.for_surface(width,height,back_available=True)
                self.assertTrue(all(r.width>=48 and r.height>=48 for r in l.tabs))
                self.assertTrue(all(r.width>=200 if width>=740 else r.width>=400 for r in l.cards))
                self.assertTrue(all(r.height>=90 for r in l.cards))
                self.assertGreaterEqual(l.title.x,c.protected_region.right)
                self.assertTrue(all(r.y>=c.protected_region.bottom for r in l.tabs))
                self.assertTrue(all(r.y>=c.protected_region.bottom for r in l.cards))
                self.assertTrue(all(r.right<=width and r.bottom<=height for r in l.cards))
                self.assertTrue(l.full_preview.right<=width)
    def test_tiny_unsupported_is_explicit(self):
        with self.assertRaises(ValueError):CreationGalleryLayout.for_surface(320,200)

if __name__=='__main__':unittest.main()
