"""Pre-reader gallery and picker behavior without Pygame or an audio device."""
from __future__ import annotations
import tempfile
import unittest
import wave
import io
from pathlib import Path
from greia_platform.creation_capacity import VolumeBudget, VolumeUsage
from greia_platform.creations import CreationLibrary
from greia_platform.creation_gallery import (
    CreationsGalleryController, CreationFamily, GalleryMode, GalleryError,
)

class Player:
    def __init__(self):
        self.plays = 0
        self.stops = 0
        self.pauses = 0
        self.resumes = 0
        self.active = False
        self.paused = False
        self.last = b""
    def play(self, wav):
        self.plays += 1
        self.active = True
        self.paused = False
        self.last = wav
    def pause(self):
        self.pauses += 1
        self.paused = True
    def resume(self):
        self.resumes += 1
        self.paused = False
    def is_playing(self):
        return self.active
    def stop(self):
        self.stops += 1
        self.active = False
        self.paused = False

def audio():
    target=io.BytesIO()
    with wave.open(target, 'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        w.writeframes(b'\0\0'*16000)
    return target.getvalue()

class TestGallery(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.library=CreationLibrary(Path(t.name)/'creations',volume_budget=VolumeBudget(probe=lambda _ : VolumeUsage(8*1024**3,2*1024**3,6*1024**3)))
        self.ids=[]
        for i in range(5):
            self.ids.append(self.library.publish(f'Story {i}'.encode(), producer_id='org.greia.writing',media_type='text/plain',role='story').creation_id)
        self.sound=self.library.publish(audio(),producer_id='org.greia.voice',media_type='audio/wav',role='song').creation_id
        self.player=Player()

    def test_paged_browsing_is_bounded_and_filterable(self):
        controller=CreationsGalleryController(self.library,audio_player=self.player)
        self.assertEqual(len(controller.page.items),2)
        self.assertTrue(controller.page.has_next)
        self.assertTrue(controller.next_page())
        self.assertTrue(controller.page.has_previous)
        controller.set_family(CreationFamily.AUDIO)
        self.assertEqual(len(controller.page.items),1)
        self.assertEqual(controller.page.items[0].creation_id,self.sound)
        self.assertFalse(controller.page.has_next)

    def test_no_autoplay_and_stop_on_filter_detail_and_close(self):
        controller=CreationsGalleryController(self.library,audio_player=self.player)
        self.assertEqual(self.player.plays,0)
        controller.set_family(CreationFamily.AUDIO)
        controller.open_item(self.sound)
        self.assertEqual(self.player.plays,0)
        self.assertTrue(controller.toggle_audio(self.sound))
        self.assertEqual(self.player.plays,1)
        self.assertEqual(controller.page.playing_id,self.sound)
        self.assertFalse(controller.toggle_audio(self.sound))
        controller.toggle_audio(self.sound)
        controller.close_item()
        self.assertIsNone(controller.page.playing_id)
        controller.close()
        with self.assertRaises(GalleryError):controller.next_page()

    def test_audio_has_real_pause_resume_and_separate_replay(self):
        gallery = CreationsGalleryController(self.library, audio_player=self.player)
        gallery.set_family(CreationFamily.AUDIO)
        gallery.open_item(self.sound)
        self.assertTrue(gallery.toggle_audio(self.sound))
        self.assertEqual(self.player.plays, 1)
        self.assertFalse(gallery.toggle_audio(self.sound))
        self.assertEqual(gallery.page.paused_id, self.sound)
        self.assertEqual(self.player.pauses, 1)
        self.assertFalse(gallery.poll_playback())
        self.assertTrue(gallery.toggle_audio(self.sound))
        self.assertIsNone(gallery.page.paused_id)
        self.assertEqual(self.player.resumes, 1)
        self.assertEqual(self.player.plays, 1)
        gallery.replay_audio(self.sound)
        self.assertEqual(self.player.plays, 2)
        self.assertEqual(gallery.page.playing_id, self.sound)
        self.player.active = False
        self.assertFalse(gallery.poll_playback())
        self.assertIsNone(gallery.page.playing_id)

    def test_gallery_deletion_requires_open_and_confirm(self):
        controller=CreationsGalleryController(self.library,audio_player=self.player)
        with self.assertRaises(GalleryError): controller.confirm_delete()
        first=controller.page.items[0].creation_id
        controller.open_item(first)
        controller.ask_delete()
        controller.cancel_delete()
        self.assertTrue(any(x.creation_id==first for x in controller.page.items))
        with self.assertRaises(GalleryError):controller.confirm_delete()
        controller.ask_delete()
        self.assertTrue(controller.confirm_delete())
        self.assertFalse(any(x.creation_id==first for x in self.library.list()))

    def test_picker_never_deletes_and_issues_handle_only_on_choose(self):
        chosen=[]
        controller=CreationsGalleryController(self.library,mode=GalleryMode.PICKER,media_types=frozenset({'audio/wav'}),on_pick=lambda item: chosen.append(item) or 'grant123',audio_player=self.player)
        self.assertEqual(len(controller.page.items),1)
        self.assertEqual(chosen,[])
        controller.open_item(self.sound)
        with self.assertRaises(GalleryError):controller.ask_delete()
        controller.toggle_audio(self.sound)
        self.assertEqual(chosen,[])
        self.assertEqual(controller.choose(),'grant123')
        self.assertEqual(chosen,[self.sound])
        self.assertIsNone(controller.page.playing_id)
        with self.assertRaises(GalleryError):controller.choose()

    def test_only_visible_items_can_preview_or_be_opened(self):
        controller=CreationsGalleryController(self.library)
        with self.assertRaises(GalleryError):controller.open_item('forged')
        with self.assertRaises(GalleryError):controller.preview('forged')
        with self.assertRaises(GalleryError):controller.toggle_audio(controller.page.items[0].creation_id)

    def test_picker_wrong_family_and_missing_grant_owner_are_rejected(self):
        with self.assertRaises(ValueError):CreationsGalleryController(self.library, mode=GalleryMode.PICKER)
        with self.assertRaises(ValueError):CreationsGalleryController(self.library,mode=GalleryMode.LIBRARY,on_pick=lambda _: 'x')
        with self.assertRaises(ValueError):CreationsGalleryController(self.library,page_size=10)
        # An explicitly empty consumer declaration must NOT silently gain
        # visibility of all child-created media.
        with self.assertRaises(ValueError):
            CreationsGalleryController(
                self.library, mode=GalleryMode.PICKER,
                media_types=frozenset(), on_pick=lambda _: "ticket",
            )
        controller=CreationsGalleryController(self.library,mode=GalleryMode.PICKER,media_types=frozenset({'text/plain'}),on_pick=lambda _: 'x')
        with self.assertRaises(GalleryError):controller.set_family(CreationFamily.AUDIO)
        with self.assertRaises(GalleryError):controller.choose()

    def test_audio_preview_requires_explicit_live_player(self):
        controller=CreationsGalleryController(self.library)
        controller.set_family(CreationFamily.AUDIO)
        with self.assertRaisesRegex(GalleryError,'unavailable'):
            controller.toggle_audio(self.sound)
        self.assertIsNone(controller.page.playing_id)

    def test_role_scoped_picker_hides_unrelated_creations(self):
        self.library.publish(
            b"a postcard", producer_id="org.greia.mail",
            media_type="text/plain", role="postcard",
        )
        picker = CreationsGalleryController(
            self.library,
            mode=GalleryMode.PICKER,
            media_types=frozenset({"text/plain"}),
            roles=frozenset({"story"}),
            on_pick=lambda _: "trusted-selection",
        )
        all_stories = []
        while True:
            all_stories.extend(picker.page.items)
            if not picker.next_page():
                break
        self.assertEqual(len(all_stories), 5)
        self.assertTrue(all(record.role == "story" for record in all_stories))
        with self.assertRaises(ValueError):
            CreationsGalleryController(
                self.library,
                mode=GalleryMode.PICKER,
                media_types=frozenset({"text/plain"}),
                roles=frozenset(),
                on_pick=lambda _: "trusted-selection",
            )

    def test_filtered_pagination_reaches_beyond_sixty_four_items(self):
        for i in range(76):
            self.library.publish(f'Later story {i}'.encode(), producer_id='org.greia.writing', media_type='text/plain', role='story')
        gallery=CreationsGalleryController(self.library, mode=GalleryMode.PICKER,media_types=frozenset({'text/plain'}),on_pick=lambda _: 'ticket')
        seen=[]
        while True:
            seen.extend(item.creation_id for item in gallery.page.items)
            if not gallery.next_page():break
        self.assertEqual(len(seen),81)
        self.assertEqual(len(set(seen)),81)

if __name__=='__main__':unittest.main()
