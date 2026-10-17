# Voice wiring of the 2026-10-17 recordings (line -> call site)

**Date:** 2026-10-17 · **Evidence class:** SOURCE (focused unit tests with fake players + `make test`; no rendered, installed-image or hardware listening run) · **Companion of:** [`VOICE_RECORDING_LEDGER_2026-10-17.csv`](./VOICE_RECORDING_LEDGER_2026-10-17.csv) · **Request list:** [`VOICE_LINES_REQUESTED_2026-10-16.md`](./VOICE_LINES_REQUESTED_2026-10-16.md)

Every line below is an existing owner-approved file; nothing was recorded, re-encoded, renamed or deleted. Activities resolve them only through the platform resolvers (`LocalizedResources.audio_path` / `activity_resources`, `shared_vocab_audio_path`, `shared_number_audio_path`, `shared_character_audio_path`), so the speech fallback (locale -> base -> English -> silence) applies everywhere and every Activity stays playable in silence. Lines join each Activity's existing speech owner: a `SpeechQueue` where one exists, otherwise the speech channel's own one-slot queue (`then`), an only-when-quiet call (`say_if_quiet`) for light helper lines, or a replacement of the generic shared reaction at that moment (never two lines stacked). The three favourites (Acquario Magico, Baia delle Orche, Sottomarino Giramondo) only gained the lines explicitly requested for them (mission invitations, creature names); Sottomarino needed no change.

Generic contract: `tests/test_voice_wiring_contract.py` (every section-B line resolves to `assets/audio/<locale>/<cue>.wav` in en/it/es/fr and is named by its Activity's code; no requested clip is left unwired). The moment each line is spoken is asserted in that Activity's own app-loop test.

## Summary

| set (ledger category) | cues | files (x4 languages) | wired | not wired |
|---|---|---|---|---|
| per-Activity requested lines (`requested`) | 139 | 556 | 139 (556) | 0 |
| per-Activity counting / shape cues (`wired`) | 45 | 180 | 45 (180) after 2 fixes | 0 |
| vocabulary bank (`vocab`) | 119 | 476 | 104 (416) | 15 (60): 11 `pos_*`, `colour_black`, `rain`/`wind`/`snow` |
| numbers bank 0-25 (`numbers`) | 26 | 104 | 25 (100): 1-25 | 1 (4): `0` |
| shared character ES/FR takes + intros (`shared`) | 30 + 6 intros | 192 | all (existing callers) | 0 |
| first-boot wizard, launcher label, missing titles, Submarine, literacy gaps | - | 87 | all (existing callers) | 0 |

Voice-identity flags for the owner (lines wired as recorded; the speaker differs from the Activity's on-screen guide): **Bottega delle Misure** five lines recorded as Dani while Leo is the guide and voices the older prompts; **Storie della mia Voce** five lines recorded as Lilli while Leo hosts; **Costruiamo Ponti** Tito's lines play whichever friend is crossing; **Pasticceria Magica** "finish the row" / "thank you" are spoken only when Lilli is the customer (recorded in her voice).

## A. Per-Activity requested lines (section B of the request list)

| Activity | cue | EN text (speaker) | wired at |
|---|---|---|---|
| acquario_magico | `find_octopus` | Find the octopus (tito) | acquarium_app.py:_on_mission_outcome (mission STARTED, find octopus; AquariumAudio.prompt, skipped while another line plays) |
| acquario_magico | `feed_turtle` | Feed the hungry turtle (tito) | acquarium_app.py:_on_mission_outcome (mission STARTED, feed turtle; AquariumAudio.prompt, skipped while another line plays) |
| alfabeto_leo | `trace_letter` | Trace the letter with your finger! (leo) | alfabeto_app.py:_enter_step (first TRACE step of a round, after the letter name, via SpeechQueue) |
| baia_delle_orche | `find_kiko` | Find Kiko (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `find_luna` | Find Luna (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `find_oskar` | Find Oskar (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `feed_kiko` | Feed Kiko (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `feed_luna` | Feed Luna (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `feed_oskar` | Feed Oskar (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `jump_kiko` | Make Kiko jump (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `jump_luna` | Make Luna jump (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| baia_delle_orche | `jump_oskar` | Make Oskar jump (tito) | orca_app.py:_on_mission_outcome (mission STARTED; PygameOrcaAudio.prompt, skipped while a fact plays) |
| bosco_numeri | `write_zero` | Let's write number 0! (tito) | bosco_app.py:_enter_step (TRACE step for 0, after count_0, via SpeechQueue) |
| bottega_delle_misure | `put_parcels` | Put both parcels on the scale. (dani) | measure_app.py:prompt_cue via _arrived / _on_listen / idle hint (WEIGH, loading phase) [voice: recorded as Dani, the guide and older prompts are Leo] |
| bottega_delle_misure | `which_heavier` | Which one is heavier? (dani) | measure_app.py:_landed_on_pan (both parcels on the pans, goal MORE) + _on_listen / idle hint [voice: recorded as Dani, the guide and older prompts are Leo] |
| bottega_delle_misure | `which_lighter` | Which one is lighter? (dani) | measure_app.py:_landed_on_pan (both parcels on the pans, goal LESS) + _on_listen / idle hint [voice: recorded as Dani, the guide and older prompts are Leo] |
| bottega_delle_misure | `line_up_blocks` | Line up the blocks under the parcel. No gaps! (dani) | measure_app.py:prompt_cue via _on_listen / idle hint (laying phase once a block is laid) [voice: recorded as Dani, the guide and older prompts are Leo] |
| bottega_delle_misure | `how_many_long` | How many blocks long is it? (dani) | measure_app.py:_next_step (MEASURE check correct -> counting phase) + _on_listen / idle hint [voice: recorded as Dani, the guide and older prompts are Leo] |
| casa_del_dieci | `friends_coming` | Some friends are coming! Bring them in. (dani) | ten_house_app.py:_guest_cue (ADD round, guests appear) + _on_listen / idle hint while arriving |
| casa_del_dieci | `fireflies_home` | Some fireflies are flying home! (dani) | ten_house_app.py:_start_round (TAKE_AWAY round, as the fireflies start leaving; ends before the question) |
| casa_del_dieci | `count_lights` | Count the lights with me! (dani) | ten_house_app.py:_demonstrate (counting demonstration after a wrong try, after the retry line; TenHouseAudio.say_if_quiet) |
| clinica_cuccioli | `where_hurt` | Where does it hurt? (momo) | clinic_app.py:_arrived (patient arrives, queued after the name via ClinicAudio.then) |
| clinica_cuccioli | `what_first` | What do we do first? (momo) | clinic_app.py:_on_part (sore place found, Momo points at the tray; ClinicAudio.then) |
| clinica_cuccioli | `whats_next` | What's next? (momo) | clinic_app.py:_step_done (a care step done, more remain; ClinicAudio.then) |
| clinica_cuccioli | `all_better` | All better! Bye bye! (momo) | clinic_app.py:_send_home (healed patient walks home, after the praise; ClinicAudio.then) |
| colline_allegre | `slow_down` | Slow down! (tito) | colline_app.py:_respawn (after a tumble at a drop: the sign glows and BRAKE pulses) |
| colline_allegre | `made_it_picnic` | You made it to the picnic! (tito) | colline_app.py:_finish_course (every picnic except the set's last, replacing generic praise.general) |
| corsa_bacche | `find_all_berries` | Find all the berries! (momo) | corsa_app.py:_start_garden (first garden of a visit, queued after "ready, go" via CorsaAudio.then) |
| corsa_bacche | `ladybird_passing` | Shh… wait, the ladybird is passing. (momo) | corsa_app.py:_on_garden_event WAIT in front of the ladybird (_critter_line: rate limited, say_if_quiet) |
| corsa_bacche | `hedgehog_sleeping` | The hedgehog is sleeping — tiptoe past! (momo) | corsa_app.py:_on_garden_event first hedgehog NAP of a garden (_critter_line) |
| corsa_bacche | `basket_full` | Basket full! (momo) | corsa_app.py:_cleared (garden cleared, replaces generic praise.general) |
| costruiamo_ponti | `long_enough` | Is it long enough? (tito) | ponti_app.py:_start_crossing (single-gap crossings, queued via BridgeAudio.then) |
| costruiamo_ponti | `pillar_on_rock` | Put a pillar on the rock! (tito) | ponti_app.py:_start_crossing (crossings with pillar rocks, BridgeAudio.then) |
| costruiamo_ponti | `lets_picnic` | Let's go to the picnic! (tito) | ponti_app.py:_on_go (first GO of a crossing, queued after "ready, go") |
| costruiamo_ponti | `just_right` | Just right! (tito) | ponti_app.py:_on_moment pass of a just-right plank (once per crossing, say_if_quiet) |
| costruiamo_ponti | `too_short` | Too short! (tito) | ponti_app.py:_stopped Failure.SHORT (replaces the generic retry line) |
| costruiamo_ponti | `too_heavy` | Too heavy — try a stone plank! (tito) | ponti_app.py:_stopped Failure.BEND (replaces the generic retry line) |
| cucciolo_mio | `hungry` | I'm hungry! (lilli) | cucciolo_app.py:_emerge (Need.HUNGRY appears; CuccioloAudio.then_line) |
| cucciolo_mio | `muddy` | I'm muddy! (lilli) | cucciolo_app.py:_emerge (Need.DIRTY appears) |
| cucciolo_mio | `play` | Let's play! (lilli) | cucciolo_app.py:_emerge (Need.PLAYFUL appears) |
| cucciolo_mio | `ouch` | Ouch! (lilli) | cucciolo_app.py:_emerge (Need.HURT appears) |
| cucciolo_mio | `sleepy` | I'm sleepy… (lilli) | cucciolo_app.py:_emerge (Need.SLEEPY appears) |
| cucciolo_mio | `not_now` | Not now, thank you (lilli) | cucciolo_app.py:_on_care (wrong care offered, on the misses that do not get Lilli's retry line) |
| cucciolo_mio | `thank_you` | Thank you! (lilli) | cucciolo_app.py:_finish_care (a need settled; Lilli's halfway cheer replaces it once) |
| cucciolo_mio | `time_for_bed` | Time for bed (lilli) | cucciolo_app.py:_enter_care (Care.BED chosen, before the bedroom slides in) |
| cucciolo_mio | `who_look_after` | Who will you look after? (lilli) | cucciolo_app.py:show_adopt (adoption screen opens) |
| cucciolo_mio | `choose_name` | Choose a name (lilli) | cucciolo_app.py:show_name (naming screen opens) |
| festa_delle_rime | `do_they_rhyme` | Do they rhyme? (leo) | rhyme_app.py:_on_wrong (rhyme match, first miss: after the target and the child's pick, via SpeechQueue) |
| festa_delle_rime | `listen_end_of_word` | Listen to the end of the word! (leo) | rhyme_app.py:_on_wrong (rhyme match demonstration: before the target and the answer, via SpeechQueue) |
| la_discesa_della_biglia | `pieces_in_spots` | Put the pieces in the shining spots! (tito) | ramp_app.py:_start_board (first board of a visit, queued via RampAudio.then) |
| la_discesa_della_biglia | `tap_ramp_turn` | Tap the ramp to turn it! (tito) | ramp_app.py:_placed (first ramp placed in a visit, say_if_quiet) |
| la_discesa_della_biglia | `oops_stopped` | Oops, it stopped! (tito) | ramp_app.py:_missed Outcome.STOPPED (replaces the generic retry line) |
| la_discesa_della_biglia | `into_basket` | Into the basket! (tito) | ramp_app.py:_board_solved (marble lands, replaces generic praise.general) |
| labirinto_magico | `help_tito_tent` | Help Tito find the way to his tent! (tito) | maze_app.py:_start_maze (first maze of a visit, queued after "ready, go" via LabyrinthAudio.then) |
| labirinto_magico | `found_star` | You found a star! (tito) | maze_app.py:_on_maze_event STAR (say_if_quiet) |
| labirinto_magico | `find_all_stars` | Find all the stars first! (tito) | maze_app.py:_tent_locked (closed tent; replaces the rate-limited retry line) |
| labirinto_magico | `find_key` | Find the key to open the door! (tito) | maze_app.py:_door_locked (locked door without the key; replaces the rate-limited retry line) |
| luci_di_momo | `watch_closely` | Watch closely! (momo) | firefly_app.py:_start_round (second round's glimpse, at the cue) + _on_replay ("look again") |
| luci_di_momo | `count_together` | Let's count them together. (momo) | firefly_app.py:_demonstrate (counting demonstration after a wrong card, after the retry line) |
| memory_meraviglie | `choose_album` | Choose an album! (lilli) | memory_app.py:_open_picker (album shelf shown; MemoryAudio.line) |
| memory_meraviglie | `find_two_same` | Find two the same! (lilli) | memory_app.py:_on_album (board of a chosen album, queued after "ready, go" via MemoryAudio.then_line) |
| mondo_contrari | `now_the_opposite` | Now the opposite! (flash) | contrari_app.py:_ask_word (second word of each pair, queued before the opposite word) |
| morbidi_mostriciattoli | `new_friend` | A new friend! (momo) | monster_app.py:_celebrate (a new friend saved, queued after the save cheer via MonsterAudio.host_then) |
| morbidi_mostriciattoli | `surprise` | Surprise! (momo) | monster_app.py:_on_surprise (surprise dice; MonsterAudio.host_says_if_quiet) |
| nanna_delle_nuvolette | `shh_sleepy` | Shh, sleepy time (momo) | cloud_app.py:_begin (the night begins; CloudAudio.whisper, softly, queued) |
| nanna_delle_nuvolette | `goodnight_cloud` | Goodnight, little cloud (momo) | cloud_app.py:_asleep (a cloud falls asleep, after Momo's praise; CloudAudio.whisper) |
| nascondino_bosco | `where_is` | Where is the…? (lilli) | woodland_app.py:_say_target -> WoodlandAudio.ask_where (round start, listen button, after each re-hide; name queued after it) |
| nascondino_bosco | `place_bush` | Behind the bush (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (friend found behind a bush/autumn bush/snowy bush, queued after the name) |
| nascondino_bosco | `place_rock` | Behind the rock (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found behind the rock) |
| nascondino_bosco | `place_log` | Behind the log (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found behind the log) |
| nascondino_bosco | `place_mushroom` | Behind the mushroom (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found behind the mushroom) |
| nascondino_bosco | `place_pumpkin` | Behind the pumpkin (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found behind the pumpkin) |
| nascondino_bosco | `place_leaves` | Under the leaves (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found under the leaves) |
| nascondino_bosco | `place_snow` | Under the snow (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found under the snow) |
| nascondino_bosco | `place_pond` | In the pond (lilli) | woodland_app.py:_found -> WoodlandAudio.say_place (found in the pond) |
| officina_dei_suoni | `find_another_sound` | Now find another sound in the word! (dani) | sound_app.py:_after_step (BUILD_WORD: first slot filled, before the word that re-anchors the later slot; SpeechQueue) |
| orchestra_animali | `listen` | Listen… (momo) | orchestra_app.py:invite (a musician steps into the spotlight, before the call; BandAudio.line) |
| orchestra_animali | `your_turn` | Your turn! (momo) | orchestra_app.py:_open_echo (echo opens; replaces the musician's generic "ready, go") |
| orchestra_animali | `loud` | Loud! (momo) | orchestra_app.py:set_dynamics (loud toggle) |
| orchestra_animali | `soft` | Soft! (momo) | orchestra_app.py:set_dynamics (soft toggle) |
| orchestra_animali | `fast` | Fast! (momo) | orchestra_app.py:set_tempo (fast toggle) |
| orchestra_animali | `slow` | Slow! (momo) | orchestra_app.py:set_tempo (slow toggle) |
| pasticceria_magica | `finish_pattern` | Finish the row! (lilli) | pasticceria_app.py:_say_order (pattern order when Lilli is the customer; recorded in Lilli's voice) |
| pasticceria_magica | `thank_you` | Thank you! (lilli) | pasticceria_app.py:_celebrate (Lilli served, queued after her cheer via BakeryAudio.line(after=True)) |
| pasticceria_magica | `count_together` | Let's count together. (lilli) | pasticceria_app.py:_not_yet (repeated miss with something to count: said first, the demonstration count waits for it) |
| piccola_serra | `pick_seed` | Pick a seed! (tito) | serra_app.py:_show_seeds (seed choice opens, queued after "ready, go" via SerraAudio.then) |
| piccola_serra | `thirsty` | The plant is thirsty! (tito) | serra_app.py:_present_need (Need.THIRSTY shown; SerraAudio.then) |
| piccola_serra | `needs_light` | It needs light! (tito) | serra_app.py:_present_need (Need.DARK shown, the cloth covers the pot) |
| piccola_serra | `too_much_water` | Too much water — let's wait. (tito) | serra_app.py:_present_need (Need.SOGGY shown) |
| piccola_serra | `ripe_pick` | It's ripe, let's pick it! (tito) | serra_app.py:_present_need (Need.RIPE shown) |
| piccola_serra | `what_comes_first` | What comes first? (tito) | serra_app.py:_start_sequence (stage pictures dealt, after the harvest praise) |
| posta_di_leo | `who_is_it_for` | Who is it for? (leo) | postcard_app.py:_opening_hint (blank card, Leo points at the friends; PostcardAudio.leo_says) |
| posta_di_leo | `pick_picture` | Pick a picture! (leo) | postcard_app.py:_go_step (friend chosen, the picture step opens; skipped while a voice plays) |
| posta_di_leo | `off_it_goes` | Off it goes! (leo) | postcard_app.py:_start_flight (the postcard flies to the mailbox) |
| quattro_amici | `make_three_in_row` | Make three in a row! (leo) | quattro_app.py:_begin_game (three-disc boards, queued after "ready, go" via QuattroAudio.line(after=True)) |
| quattro_amici | `make_four_in_row` | Make four in a row! (leo) | quattro_app.py:_begin_game (four-disc boards, queued after "ready, go") |
| quattro_amici | `your_turn` | Your turn! (leo) | quattro_app.py:_begin_turn (vs Leo: the child's turn after Leo's move; only when quiet) |
| quattro_amici | `leo_thinking` | Leo is thinking… (flash) | quattro_app.py:_leo_move (Flash, first Leo move of each game; only when quiet) |
| quattro_amici | `three_in_row` | Three in a row! (leo) | quattro_app.py:_cheer (a three-disc win; replaces the generic reaction so lines never stack) |
| quattro_amici | `i_stopped_you` | I stopped you! (leo) | quattro_app.py:_block_moment (Leo filled the child's winning hole) |
| quattro_amici | `you_blocked_me` | You blocked me! (leo) | quattro_app.py:_block_moment (vs Leo: the child filled Leo's winning hole) |
| quattro_amici | `draw` | It's a draw! (leo) | quattro_app.py:_game_draw (replaces encourage.progress; falls back to it when silent) |
| quattro_amici | `you_won_match` | You won the match! (leo) | quattro_app.py:_complete_match (vs Leo, the child won the match; queued after Flash's cheer) |
| quattro_stagioni | `belongs_here` | Yes, that belongs in this season! (tito) | tree_app.py:_place (right picture placed: queued after its name via TreeAudio.say_after; replaces generic praise when nothing was named) |
| quattro_stagioni | `not_this_season` | Hmm, not in this season. (tito) | tree_app.py:_not_here (wrong-season picture returns, on the misses without Tito's retry line) |
| shape_garden | `drag_shape` | Drag a shape into the garden! (dani) | garden_app.py:_maybe_hint (first empty-garden invitation, queued after "ready, go" via GardenSounds.then) |
| shape_garden | `beautiful_garden` | What a beautiful garden! (dani) | garden_app.py:_celebrate_progress (garden reaches PRAISE_AT shapes; replaces encourage.progress) |
| sillabe_magiche | `clap_beats` | Clap the beats! (leo) | sillabe_app.py:_speak_goal (first word of a round entering the clap phase: IT/ES/FR at the start, EN after the beats picture; SpeechQueue) |
| specchi_magici | `look_mirror_line` | Look at the mirror line. (lilli) | mirror_app.py:_play (first mosaic of a visit, the mirror line sparkles; MirrorAudio.say_if_quiet) |
| specchi_magici | `turn_it` | Turn it around! (lilli) | mirror_app.py:_declined (the unreflected copy of the right tile placed; replaces the retry line) |
| specchi_magici | `try_this_spot` | Try this spot! (lilli) | mirror_app.py:_explain (second miss: Lilli shows the spot; say_if_quiet) |
| stelle_incantate | `connect_in_order` | Connect the stars in order! (leo) | sky_app.py:_present_goal (ORDER/MISSING figures; queued after "ready, go" via SkyAudio.then; replayed by the goal button) |
| stelle_incantate | `start_at_four` | Start at four! (leo) | sky_app.py:_present_goal (COUNT_ON figure whose given star is 4; replaces saying "four") |
| stelle_incantate | `count_back` | Let's count back! (leo) | sky_app.py:_present_goal (COUNT_BACK figure, followed by the given star's number) |
| stelle_incantate | `which_missing` | Which number is missing? (leo) | sky_app.py:_on_star TapResult.ASK (the missing-number cards open) |
| storie_della_mia_voce | `order_pictures` | Put the pictures in order! (lilli) | voice_app.py:start_story (queued after "ready, go" via StoryAudio.line(after=True)) [voice: recorded as Lilli, on-screen host is Leo] |
| storie_della_mia_voce | `what_first` | What happens first? (lilli) | voice_app.py:_demonstrate + _maybe_hint step 1 (when the first place is the one shown; only when quiet) [Lilli voice / Leo host] |
| storie_della_mia_voce | `tell_story` | Now tell me your story! (lilli) | voice_app.py:start_telling (telling step opens) [Lilli voice / Leo host] |
| storie_della_mia_voce | `tell_picture` | Tell me about this picture! (lilli) | voice_app.py:_maybe_hint (idle on an untold picture, never while recording; only when quiet) [Lilli voice / Leo host] |
| storie_della_mia_voce | `great_story` | What a great story! (lilli) | voice_app.py:_complete (replaces Leo's praise.general, which stays the fallback) [Lilli voice / Leo host] |
| teatrino_fiabe | `three_two_one` | Three, two, one… action! (lilli) | teatrino_app.py:_start_recording (curtain countdown; replaces "ready, go", which stays the fallback; the mic opens only after the line ends, host.stop() guards _open_for_recording) |
| teatrino_fiabe | `stage_full` | The stage is full! (lilli) | teatrino_app.py:_tray_card (a puppet tapped while the stage is full; HostVoice.say_if_quiet) |
| torre_forme | `fill_shape_blocks` | Fill the shape with blocks! (dani) | torre_app.py:_play (first build of a set, queued after the build name / "ready, go" via TorreAudio.then) |
| torre_forme | `turn_it` | Turn it! (dani) | torre_app.py:_declined PlaceOutcome.NEEDS_TURN (replaces the retry line) |
| torre_forme | `it_fits` | It fits! (dani) | torre_app.py:_placed (every other placed block, replacing praise.general, which stays the fallback) |
| treno_numeri | `toot` | Toot toot! (dani) | treno_app.py:_start_station (the journey's first train arrives, with the whistle) |
| treno_numeri | `make_same` | Make this wagon the same! (dani) | treno_app.py:_present_order (SAME stations, queued after "go" via TrenoAudio.then) |
| treno_numeri | `too_many` | Too many! Take some out. (dani) | treno_app.py:_demonstrate GoResult.TOO_MANY (replaces "retry"; the voiced recount waits for it) |
| treno_numeri | `not_enough` | Not enough yet! (dani) | treno_app.py:_demonstrate GoResult.TOO_FEW (replaces "retry") |
| treno_numeri | `count_again` | Let's count again. (dani) | treno_app.py:_demonstrate (queued after the reason line, before the recount) |
| treno_numeri | `all_aboard` | All aboard! (dani) | treno_app.py:_depart (the loaded train leaves, queued after the praise) |
| viaggio_delfino | `swim_finish` | Swim to the finish and collect the pearls! (tito) | delfino_app.py:start_journey (first journey of a launch: the device-free spoken goal, replacing the older welcome, which stays the fallback) |
| viaggio_delfino | `choose_journey` | Choose a journey! (tito) | delfino_app.py:_advance_picker (journey map, once per launch, and with the idle picker hint when quiet) |
| volo_draghetto | `fly_rings` | Fly through the rainbow rings! (flash) | dragon_app.py:start_course (first flight of a visit, queued after "ready, go" via DragonAudio.then) |
| workshop_settings | `this_is_your_greia` | This is your Greia! (leo) | workshop_audio.py:MyGreiaAudio.welcome (queued after the "My Greia" title clip at launch) |
| workshop_settings | `pick_your_friend` | Pick your friend! (leo) | workshop_app.py:_on_tab (the friends tab opens) |
| workshop_settings | `bigger` | Bigger! (leo) | workshop_app.py:_describe (a larger size chosen; replaces the friend's cheer) |
| workshop_settings | `smaller` | Smaller! (leo) | workshop_app.py:_describe (a smaller size chosen; replaces the friend's cheer) |
| workshop_settings | `nice_picture` | What a nice picture! (leo) | workshop_app.py:_describe (a new picture chosen; replaces the friend's cheer) |

## B. Per-Activity counting and shape cues recorded as "wired" (verified)

| Activity | cues | played at | status |
|---|---|---|---|
| il_giardino_dei_numeri | `count_6`..`count_10`, `how_many` | giardino_audio.py:say_number (via `speech_paths`) from the recount; giardino_app.py `how_many` prompt | already wired |
| stelle_incantate | `count_1`..`count_20` | sky_audio.py:say_number from sky_app.py:_on_star / _lit / _present_goal | already wired |
| treno_numeri | `count_1`..`count_10` | treno_audio.py:say_number from treno_app.py:_landed / _pulse_slot | already wired |
| bosco_numeri | `count_0`, `ask_0` | bosco_app.py speech queue (meet / find / trace of 0) | already wired |
| luci_di_momo | `count_6`..`count_10` | firefly_audio.py:play_count via firefly_app.py:_celebrate (FIX: SPOKEN_COUNTS was 5, so the "wired" 6-10 clips never played) | **fixed** |
| specchi_magici | `shape_rhombus`, `shape_heart` | mirror_app.py:_pick -> MirrorAudio.shape_name (FIX: recorded as "wired" but filtered out by SPOKEN_SHAPES/PACKAGE_CUES until now) | **fixed** |

## C. Shared vocabulary bank (`assets/audio/vocab/v1/<locale>/<id>.wav`)

| id | EN | wired at |
|---|---|---|
| `acorn` | Acorn | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `apple` | Apple | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>cucciolo_mio: cucciolo_app.py:_on_name / start_day (the pet's name tag) |
| `banana` | Banana | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>pasticceria_magica: pasticceria_app.py:_say_order / _on_topping (order and topping names) |
| `bandage` | Bandage | clinica_cuccioli: clinic_app.py:_on_tool -> ClinicAudio.name (correct tool used; skipped while a line plays) |
| `bean` | Bean | piccola_serra: serra_app.py:_on_seed -> SerraAudio.say_if_quiet("name.<plant>") (seed packet chosen) |
| `bear` | Bear | clinica_cuccioli: clinic_app.py:_arrived (the patient's name)<br>nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend)<br>quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `bells` | Bells | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |
| `bicycle` | Bicycle | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `blueberry` | Blueberry | pasticceria_magica: pasticceria_app.py:_say_order / _on_topping (order and topping names) |
| `boat` | Boat | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `bus` | Bus | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `butterfly` | Butterfly | nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend)<br>quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `cake` | Cake | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `car` | Car | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `carrot` | Carrot | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>piccola_serra: serra_app.py:_on_seed -> SerraAudio.say_if_quiet("name.<plant>") (seed packet chosen) |
| `cat` | Cat | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `chair` | Chair | torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `cherry` | Cherry | pasticceria_magica: pasticceria_app.py:_say_order / _on_topping (order and topping names) |
| `chocolate` | Chocolate | pasticceria_magica: pasticceria_app.py:_say_order / _on_topping (order and topping names) |
| `colour_black` | Black | not wired: no Activity offers a black colour (Nanna's quilts and My Greia's swatches have none) |
| `colour_blue` | Blue | nanna_delle_nuvolette: cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt's colour, rungs where colour matters)<br>workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_brown` | Brown | workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_green` | Green | nanna_delle_nuvolette: cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt's colour, rungs where colour matters)<br>workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_orange` | Orange | nanna_delle_nuvolette: cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt's colour, rungs where colour matters)<br>workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_pink` | Pink | nanna_delle_nuvolette: cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt's colour, rungs where colour matters)<br>workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_purple` | Purple | nanna_delle_nuvolette: cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt's colour, rungs where colour matters)<br>workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_red` | Red | workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_white` | White | workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `colour_yellow` | Yellow | nanna_delle_nuvolette: cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt's colour, rungs where colour matters)<br>workshop_settings: workshop_app.py:_describe -> MyGreiaAudio.colour (accent or room colour chosen; turquoise and aqua have no word and keep the cheer) |
| `cookie` | Cookie | pasticceria_magica: pasticceria_app.py:_say_order / _on_topping (order and topping names) |
| `crab` | Crab | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `crown` | Crown | torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `deer` | Deer | nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend) |
| `dog` | Dog | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `dolphin` | Dolphin | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `drum` | Drum | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |
| `duck` | Duck | nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend) |
| `elephant` | Elephant | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `fish` | Fish | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `flower` | Flower | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>cucciolo_mio: cucciolo_app.py:_on_name / start_day (the pet's name tag)<br>quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `frog` | Frog | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend)<br>quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `grapes` | Grapes | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `guinea_pig` | Guinea pig | clinica_cuccioli: clinic_app.py:_arrived (the patient's name) |
| `hedgehog` | Hedgehog | nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend)<br>quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `house` | House | torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `ice_cream` | Ice cream | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `igloo` | Igloo | torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `jellyfish` | Jellyfish | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `keyboard` | Keyboard | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |
| `kite` | Kite | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `kitten` | Kitten | clinica_cuccioli: clinic_app.py:_arrived (the patient's name) |
| `leaf` | Leaf | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `lighthouse` | Lighthouse | torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `lion` | Lion | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `maracas` | Maracas | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |
| `medicine` | Medicine | clinica_cuccioli: clinic_app.py:_on_tool -> ClinicAudio.name (correct tool used; skipped while a line plays) |
| `moon` | Moon | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>cucciolo_mio: cucciolo_app.py:_on_name / start_day (the pet's name tag) |
| `mouse` | Mouse | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>clinica_cuccioli: clinic_app.py:_arrived (the patient's name)<br>nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend) |
| `mushroom` | Mushroom | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `mushrooms` | Mushrooms | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `octopus` | Octopus | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `pear` | Pear | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `penguin` | Penguin | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `pig` | Pig | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `pizza` | Pizza | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `plane` | Plane | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `pos_behind` | Behind | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_down` | Down | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_in` | In | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_in_front` | In front of | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_left` | Left | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_next_to` | Next to | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_on` | On | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_right` | Right | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_under` | Under | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_up` | Up | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pos_where_is` | Where is the…? | not wired: the requesting Activity (Nascondino) speaks the owner-approved full place phrases (`place_*`) and `where_is`; no Activity has a moment for a bare position word (Mondo dei Contrari keeps its own approved concept clips) |
| `pufferfish` | Pufferfish | acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `pumpkin` | Pumpkin | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `puppy` | Puppy | clinica_cuccioli: clinic_app.py:_arrived (the patient's name) |
| `rain` | Rain | not wired: Quattro Stagioni already speaks its own approved weather lines (package `rain` / `wind` / `snow`, all four languages) at that moment; the bank word would duplicate them |
| `rainbow` | Rainbow | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `rocket` | Rocket | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `scarf` | Scarf | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `seahorse` | Seahorse | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `shape_arch` | Arch | torre_forme: torre_app.py:_pick -> TorreAudio.block_name (a kit block picked; skipped while Dani speaks) |
| `shape_circle` | Circle | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks) |
| `shape_cylinder` | Cylinder | torre_forme: torre_app.py:_pick -> TorreAudio.block_name (a kit block picked; skipped while Dani speaks) |
| `shape_diamond` | Diamond | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks) |
| `shape_half_circle` | Half circle | torre_forme: torre_app.py:_pick -> TorreAudio.block_name (a kit block picked; skipped while Dani speaks) |
| `shape_heart` | Heart | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks) |
| `shape_oval` | Oval | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks) |
| `shape_rectangle` | Rectangle | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks)<br>torre_forme: torre_app.py:_pick -> TorreAudio.block_name (a kit block picked; skipped while Dani speaks) |
| `shape_square` | Square | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks)<br>torre_forme: torre_app.py:_pick -> TorreAudio.block_name (a kit block picked; skipped while Dani speaks) |
| `shape_star` | Star | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks) |
| `shape_triangle` | Triangle | shape_garden: garden_app.py:_plant -> GardenSounds.name (a shape planted; skipped while Dani speaks)<br>torre_forme: torre_app.py:_pick -> TorreAudio.block_name (a kit block picked; skipped while Dani speaks) |
| `snail` | Snail | nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `snow` | Snow | not wired: Quattro Stagioni already speaks its own approved weather lines (package `rain` / `wind` / `snow`, all four languages) at that moment; the bank word would duplicate them |
| `snowflake` | Snowflake | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name) |
| `snowman` | Snowman | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `sponge` | Sponge | clinica_cuccioli: clinic_app.py:_on_tool -> ClinicAudio.name (correct tool used; skipped while a line plays) |
| `squirrel` | Squirrel | clinica_cuccioli: clinic_app.py:_arrived (the patient's name)<br>nascondino_bosco: woodland_app.py:_say_target / _found (the wanted / found friend) |
| `starfish` | Starfish | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `stethoscope` | Stethoscope | clinica_cuccioli: clinic_app.py:_on_tool -> ClinicAudio.name (correct tool used; skipped while a line plays) |
| `strawberries` | Strawberries | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `strawberry` | Strawberry | pasticceria_magica: pasticceria_app.py:_say_order / _on_topping (order and topping names)<br>piccola_serra: serra_app.py:_on_seed -> SerraAudio.say_if_quiet("name.<plant>") (seed packet chosen) |
| `sun` | Sun | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>cucciolo_mio: cucciolo_app.py:_on_name / start_day (the pet's name tag)<br>quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `sunflower` | Sunflower | piccola_serra: serra_app.py:_on_seed -> SerraAudio.say_if_quiet("name.<plant>") (seed packet chosen) |
| `sunhat` | Sun hat | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `table` | Table | torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `tambourine` | Tambourine | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |
| `towel` | Towel | clinica_cuccioli: clinic_app.py:_on_tool -> ClinicAudio.name (correct tool used; skipped while a line plays) |
| `train` | Train | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name) |
| `trumpet` | Trumpet | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |
| `turtle` | Turtle | memory_meraviglie: memory_app.py:_celebrate (a matched pair's picture name)<br>torre_forme: torre_app.py:_play / _celebrate / _listen (the build's name)<br>acquario_magico: acquarium_app.py:_touch_creature -> AquariumAudio.name (creature tapped, no mission completed) |
| `watermelon` | Watermelon | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `wind` | Wind | not wired: Quattro Stagioni already speaks its own approved weather lines (package `rain` / `wind` / `snow`, all four languages) at that moment; the bank word would duplicate them |
| `winter_hat` | Woolly hat | quattro_stagioni: tree_app.py:_place (a placed picture's name) |
| `xylophone` | Xylophone | orchestra_animali: orchestra_app.py:play_musician / play_bar -> BandAudio.name (first play of each instrument in free play; skipped while a line plays) |

## D. Numbers bank 0-25 (`assets/audio/numbers/v1/<locale>/<n>.wav`)

| numbers | wired at |
|---|---|
| 1-10 | pasticceria_app.py:_say_order / _on_topping / _demo_step (orders and counting; the module now calls `localization.shared_number_audio_path` directly instead of probing for it) |
| 1-5 (nanna_delle_nuvolette) | cloud_app.py:_pick -> _name_quilt -> CloudAudio.name_quilt (picked quilt star count, rungs with stars; shared_number_audio_path) |
| 0-25 (viaggio_delfino) | delfino_app.py:_advance_count (pearl total spoken after the count-up via PygameDelfinoAudio.number; totals above 25 stay silent) |
| 0 | not wired: Bosco dei Numeri teaches zero with its own approved `count_0` / `ask_0` / `write_zero`, and Viaggio del Delfino stays quiet when no pearl was collected |

## E. Shared character takes (ES/FR) and introductions

The 180 ES/FR takes fill the same five families (`ready.go`, `praise.general`, `encourage.retry`, `encourage.progress`, `celebrate.success`) x six speakers that EN/IT already had; every speaker x family pair is requested by existing `shared_character_audio_path` callers in the Activities (sibling takes 02/03 by the modules that rotate takes), so no code change was needed. The six `_intros/<lang>/<id>.ogg` are played by `workshop_audio.py:MyGreiaAudio.react` (first avatar pick) and `src/greia_launcher/home_animator.py`.

## F. Other recordings (verified, no change)

| set | wired at |
|---|---|
| first-boot wizard (32) | `src/greia_launcher/first_profile_copy.py` / `first_profile_wizard.py` (`assets/audio/system/first-boot`) |
| launcher label `sea` (4) | `src/greia_launcher/spoken_labels.py` |
| Bottega / Casa ES-FR titles (4) | `LocalizedResources` `activity.title` convention (launcher spoken titles) |
| Submarine buttons, encounters, creatures, EN alarm (31) | sub_app.py:_speak_cue (`voice.btn.*`, `voice.enc.*`, creature cues); ES/FR and the new EN alarm resolve by locale projection of the existing IT/EN audio maps |
| literacy gaps: ES Ñ, ES/FR syllable praise, FR é syllables (16) | alfabeto_audio.py / sillabe_audio.py through `speech_paths` / `clip_path` (letter, `syl_*`, `find_*`, praise sets in `sillabe_content.py`) |

## G. Not recorded, therefore not wired

Lines listed in the request but without a recording (see PROGRESS 2026-10-17) stay pictorial: variable-number templates (`thats_n`, `write_n`, `show_n`, `order_n`, `order_n_toppings`), constellation names, story titles, shelf-full lines, per-friend thank-you, coloured-blanket wish, per-plant harvest lines, the 12 further aquarium missions, season mission prompts, monster name syllables, Sound Workshop stage-3 phonemes, new Word Forest lessons, `this_is_letter`, Sillabe `which_picture_fits_train` / `which_vowel`, the room-colour line, and the Delfino/Luci/Specchi/Bosco re-records the owner kept.
