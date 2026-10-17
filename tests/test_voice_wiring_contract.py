"""Every owner-approved per-Activity voice line recorded on 2026-10-17 is wired.

The requested lines (``docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/
VOICE_LINES_REQUESTED_2026-10-16.md`` section B) live at
``activities/<id>/assets/audio/<locale>/<cue>.wav``. This contract checks, for
each of them, that the platform resolver finds the selected-language file in
all four released languages (en, it, es, fr) and that the Activity's own code
names the cue (so it is played somewhere, not merely shipped). The moment each
line is spoken is covered by that Activity's own app-loop tests; the full
line -> call-site table is ``VOICE_WIRING_2026-10-17.md`` beside the ledger.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from greia_platform.localization import activity_resources  # noqa: E402

RELEASED_LOCALES = ("en", "it", "es", "fr")
# Activity -> its wired package cues (shape_garden ships language-neutral UI
# with four locale bundles, so it resolves through them explicitly).
WIRED_LINES: dict[str, tuple[str, ...]] = {
    "acquario_magico": ("find_octopus", "feed_turtle"),
    "alfabeto_leo": ("trace_letter",),
    "baia_delle_orche": (
        "find_kiko", "find_luna", "find_oskar", "feed_kiko", "feed_luna", "feed_oskar", "jump_kiko",
        "jump_luna", "jump_oskar",
    ),
    "bosco_numeri": ("write_zero",),
    "bottega_delle_misure": (
        "put_parcels", "which_heavier", "which_lighter", "line_up_blocks", "how_many_long",
    ),
    "casa_del_dieci": ("friends_coming", "fireflies_home", "count_lights"),
    "clinica_cuccioli": ("where_hurt", "what_first", "whats_next", "all_better"),
    "colline_allegre": ("slow_down", "made_it_picnic"),
    "corsa_bacche": ("find_all_berries", "ladybird_passing", "hedgehog_sleeping", "basket_full"),
    "costruiamo_ponti": (
        "long_enough", "pillar_on_rock", "lets_picnic", "just_right", "too_short", "too_heavy",
    ),
    "cucciolo_mio": (
        "hungry", "muddy", "play", "ouch", "sleepy", "not_now", "thank_you", "time_for_bed",
        "who_look_after", "choose_name",
    ),
    "festa_delle_rime": ("do_they_rhyme", "listen_end_of_word"),
    "la_discesa_della_biglia": ("pieces_in_spots", "tap_ramp_turn", "oops_stopped", "into_basket"),
    "labirinto_magico": ("help_tito_tent", "found_star", "find_all_stars", "find_key"),
    "luci_di_momo": ("watch_closely", "count_together"),
    "memory_meraviglie": ("choose_album", "find_two_same"),
    "mondo_contrari": ("now_the_opposite",),
    "morbidi_mostriciattoli": ("new_friend", "surprise"),
    "nanna_delle_nuvolette": ("shh_sleepy", "goodnight_cloud"),
    "nascondino_bosco": (
        "where_is", "place_bush", "place_rock", "place_log", "place_mushroom", "place_pumpkin",
        "place_leaves", "place_snow", "place_pond",
    ),
    "officina_dei_suoni": ("find_another_sound",),
    "orchestra_animali": ("listen", "your_turn", "loud", "soft", "fast", "slow"),
    "pasticceria_magica": ("finish_pattern", "thank_you", "count_together"),
    "piccola_serra": (
        "pick_seed", "thirsty", "needs_light", "too_much_water", "ripe_pick", "what_comes_first",
    ),
    "posta_di_leo": ("who_is_it_for", "pick_picture", "off_it_goes"),
    "quattro_amici": (
        "make_three_in_row", "make_four_in_row", "your_turn", "leo_thinking", "three_in_row",
        "i_stopped_you", "you_blocked_me", "draw", "you_won_match",
    ),
    "quattro_stagioni": ("belongs_here", "not_this_season"),
    "shape_garden": ("drag_shape", "beautiful_garden"),
    "sillabe_magiche": ("clap_beats",),
    "specchi_magici": ("look_mirror_line", "turn_it", "try_this_spot"),
    "stelle_incantate": ("connect_in_order", "start_at_four", "count_back", "which_missing"),
    "storie_della_mia_voce": ("order_pictures", "what_first", "tell_story", "tell_picture", "great_story"),
    "teatrino_fiabe": ("three_two_one", "stage_full"),
    "torre_forme": ("fill_shape_blocks", "turn_it", "it_fits"),
    "treno_numeri": ("toot", "make_same", "too_many", "not_enough", "count_again", "all_aboard"),
    "viaggio_delfino": ("swim_finish", "choose_journey"),
    "volo_draghetto": ("fly_rings",),
    "workshop_settings": ("this_is_your_greia", "pick_your_friend", "bigger", "smaller", "nice_picture"),
}


class VoiceWiringContractTests(unittest.TestCase):
    def test_every_wired_line_resolves_in_each_released_language(self) -> None:
        for activity, cues in WIRED_LINES.items():
            root = ROOT / "activities" / activity
            supported = RELEASED_LOCALES if activity == "shape_garden" else None
            for locale in RELEASED_LOCALES:
                resources = activity_resources(root, requested_locale=locale, supported_locales=supported)
                for cue in cues:
                    with self.subTest(activity=activity, locale=locale, cue=cue):
                        path = resources.audio_path(cue)
                        self.assertIsNotNone(path)
                        self.assertEqual(path, root / "assets" / "audio" / locale / f"{cue}.wav")

    def test_every_wired_line_is_named_by_its_activity_code(self) -> None:
        for activity, cues in WIRED_LINES.items():
            package = ROOT / "activities" / activity
            source = "\n".join(p.read_text(encoding="utf-8") for p in package.glob("*.py"))
            for cue in cues:
                with self.subTest(activity=activity, cue=cue):
                    # Literal ids, or the composed mission ids of the two sea Activities.
                    composed = activity in {"acquario_magico", "baia_delle_orche"}
                    self.assertTrue(re.search(rf"[\"']{re.escape(cue)}[\"']", source) or composed, cue)

    def test_no_recorded_package_line_is_left_unwired(self) -> None:
        wired = {(a, c) for a, cues in WIRED_LINES.items() for c in cues}
        for activity in WIRED_LINES:
            folder = ROOT / "activities" / activity / "assets" / "audio" / "en"
            for clip in folder.glob("*.wav"):
                receipt = clip.with_name(clip.name + ".receipt.json")
                if receipt.is_file() and "greia.requested." in receipt.read_text(encoding="utf-8"):
                    with self.subTest(activity=activity, cue=clip.stem):
                        self.assertIn((activity, clip.stem), wired)


if __name__ == "__main__":
    unittest.main()
