# Activity design audit — Group C1: creative making, performance, music

**Date:** 2026-10-15 · **Auditor:** design-c1 (Opus; game designer + early-years learning designer)
**Scope label:** SOURCE + DESKTOP VISUAL REVIEW. Real Pygame frames came from the Greia simulator bridge (`greia_simulator.python_activity`, the same path as `tools/headless_greia_activity.py`). A scratch multi-step driver sent clicks, drags, text and keys. Locale was `en`, at 1024×600 plus one 800×480 capture each, with 4–12 captures per Activity. Checkout `main` @ `5e7e089e`; no uncommitted edits in these nine Activity folders.

Activity storage went to a disposable `GREIA_STANDALONE_STORAGE_DIR`, so the developer store `~/.greia-simulator/standalone-storage` was not touched. Officina L2/L3 were reached by seeding that disposable store. Audio was not heard (dummy driver). Spoken texts come from voice receipts. There was no microphone, so recordings captured silence. There was no trusted Creations broker either, so Share/Import buttons are absent in standalone runs and the Creations paths were reviewed from source only. No simulator-Shell, VM, Acer or physical evidence.

**Activities (9):** painting, shape_garden, writing, posta_di_leo, storie_della_mia_voce, teatrino_fiabe, orchestra_animali, faccine_momo, officina_dei_suoni. `foresta_parole` was read for the merge evaluation only (§9).

**Bar used.** The creative tools (Painting, Shape Garden, Writing, Posta, Storie, Teatrino) are judged as tools, not as games. That means:
- low-friction making;
- large affordances;
- safe, finding-friendly persistence;
- deliberate sharing through My Creations;
- the cross-Activity journeys in `docs/plans/2026-10-07_CREATIONS_LIBRARY_AND_ACTIVITY_RELEASE/PLAN.md` §1;
- the Phase-0 contract in `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`.

For these tools, "Progression" means growth of expressive range and the library experience, not levels.

Score scale per dimension: 1 poor … 5 flagship. Dimensions, in order: **Obj** learning objective clarity/correctness · **Age** age fit 3–6 / pre-reader independence · **Loop** core-loop fun · **FB** feedback & juice · **Prog** progression/replay (for tools: expressive range + library) · **Vis** visual quality & on-model cast · **Use** usability/input/Home safety · **Tech** technical health.

## Summary (best → worst)

| Activity | Portfolio family | Score /40 | Verdict | Effort |
|---|---|---:|---|---|
| teatrino_fiabe | Creative making & performance | 28 | POLISH (puppet art is REWORK) | M |
| painting | Creative making (required anchor) | 27 | POLISH | S |
| officina_dei_suoni | Words & literacy | 26 | POLISH (absorbs foresta_parole, §9) | M |
| writing | Words & literacy / Create (required anchor) | 24 | POLISH | S |
| faccine_momo | Care & emotions | 24 | REWORK | M |
| orchestra_animali | Music & rhythm (singleton) | 21 | RETHINK → the one Music home (absorbs the Echo and Pattern proposals) | L |
| shape_garden | Creative making | 20 | REWORK | M |
| posta_di_leo | Words & literacy / Create | 20 | REWORK (picture + voice postcard); fallback MERGE → Writing "postcard paper" | M |
| storie_della_mia_voce | Creative making & performance | 19 | RETHINK → "Story Cards" sequenced narration; fallback MERGE → Teatrino | M |

**Bottom line.** Nothing here is flagship-ready, but the group has the best raw material in the catalogue:
- Teatrino is a genuinely delightful stage;
- Painting is fast and clean;
- Officina has the only phoneme-correct, owner-accepted literacy audio.

The common failure is not fun. It is **custody of the child's work**. I found five separate bugs that lose, hide or one-tap-delete creations:
- Painting shows 6 of 48 drawings;
- Writing shows 6 of 120 pages;
- Teatrino silently evicts the oldest show on the 17th save;
- Teatrino and Storie delete a whole show/story on one tap with no confirmation;
- Painting and Writing create a new blank entry on every New tap, so the visible 6 fill with empty pages.

That directly contradicts the Phase-0 and Creations rules ("never silently evict … older child work"; deletion by "deliberate hold/confirmation"). Fix this group-wide with one shared drafts gallery (§C), not nine patches.

The second failure is that the music and emotion Activities are toys without a learning loop:
- Orchestra is free tapping with a coin counter and no animals;
- Faccine's quiz speaks the answer.

---

## 1. teatrino_fiabe — Fairy Tale Puppet Theater (age 3+) · 28/40 · POLISH (puppet art REWORK)

Played: start stage (cottage, unicorn + dragon); added Leo and Dani from the tray; changed scene to Castle; REC; dragged puppets; FX trumpet; STOP (show saved); SHOW playback; STORIES modal (1 story, Watch/Delete). 800×480 is scaled and soft, and the "SCENE" caption is clipped.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 4 | 4 | 4 | 3 | 3 | 3 | 3 |

- **Obj 4:** pretend play plus oral narration over a puppet performance. It is the right creative-language objective, and it is the Creations image+audio consumer.
- **Age 4:** dragging puppets is natural for a 3-year-old. But the whole top bar is words (ON / STORIES / REC / SHOW), and status feedback is text ("Recording in progress... Tell your story!").
- **Loop 4:** place → move → record → watch is a complete, satisfying creative loop. FX buttons make puppets jump.
- **FB 4:** curtains, puppet hop/talk wobble and synthesized FX are lively. There is no curtain-open/countdown ritual before REC, and the recording timer is a tiny "35/45s".
- **Prog 3:**
  - 16 puppets on 3 tray pages;
  - 5 backdrops + an imported picture backdrop;
  - saved shows.

  Shows have no thumbnail of the stage, only icons.
- **Vis 3:** a rich, coherent stage. The 6 cast puppets are off-model (asset audit S1: quadruped Lilli, orange-brown Flash), and FX buttons and the scene chip are emoji.
- **Use 3:**
  - Delete in the Stories modal is **one tap, no confirm**;
  - no way to remove a single puppet (only Clear-all);
  - puppet count on stage is **unbounded** (every tray tap appends);
  - the OS cursor is hidden and no Greia pointer is drawn (`teatrino_app.py:154`);
  - pointer only.
- **Tech 3:**
  - **the 17th saved show silently deletes the oldest show and its WAV** (`teatrino_model.py:145–170`);
  - `teatrino_app.py` is a 1,412-line god class;
  - its own microphone stack duplicates Storie's.

**Redesign spec**
- Target: the flagship "make a show" studio. A pre-reader can stage, perform, record and re-watch a 30-second show with no words on screen, and reuse their drawings and voice recordings.
- Chrome:
  - replace the text bar with kit icon buttons: mic, record (red dot), play (triangle), stories (film reel), clear (broom);
  - the record button grows a ring timer instead of "35/45s";
  - FX become `icon.hud.fx_*` glyphs.
- REC ritual:
  - curtain-open FX with a "3-2-1" pip count, then the curtains close at stop;
  - STOP saves and shows a poster thumbnail of the stage.
- Puppets:
  - cap at 6 on stage; a 7th tap bounces the tray card with a "full" wobble;
  - drag a puppet back onto the tray to remove it (dust-puff FX);
  - tapping a puppet makes it bow.
- Library:
  - poster cards (rendered stage snapshot 320×188, cached once at save);
  - delete = hold 1 s on the bin, then a big preview + confirm/cancel;
  - at 16 shows, Save is refused with a pictorial "shelf full" card that offers to open the library. **Never evict.**
- Creations:
  - add producer role `picture` (publish the poster PNG) so a show can feed Posta/Painting;
  - keep the existing PNG backdrop + `narration` WAV consumption.
- Engineering:
  - split the app into a `StageController` / `RecorderController` / `LibraryController`;
  - use the shared platform recorder (§C2).
- New art:
  - `character.<id>.puppet` × 6: canonical body on a rod, with talk/jump variants;
  - `bg.stage.{curtain_left,curtain_right,valance,boards}`;
  - `icon.hud.{rec,stop,play,film,broom,mic_on,mic_off,fx_trumpet,fx_magic,fx_clap,fx_giggle,fx_mystery,fx_boing}`;
  - `fx.{curtain_open,dust_puff,bow_sparkle}`.

  The 10 fairytale puppets are re-drawn to the style guide §20 grammar.
- Voice (EN, request): "Three, two, one… action!", "Bravo! What a show!", "The shelf is full, let's look at your shows." (3 lines.)
- Effort M (code S–M; puppet art M). Risk: puppet redraw must keep each puppet's rod pivot and talk-wobble anchor.

---

## 2. painting — Free Painting (age 3+, required anchor) · 27/40 · POLISH

Played: start (blank, colour/size bars); two strokes; colour change; eraser toggle; New ×3; tiny dot; gallery (5 cards, 2 of them empty blanks); opened a card; 800×480 reopen (the previous painting's round dot is now an oval).

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 4 | 4 | 2 | 3 | 4 | 3 | 3 |

- **Obj 4:** pure free expression, as the Phase-0 contract requires. Fast and uncluttered.
- **Age 4:**
  - immediate drawing;
  - 10 big swatches, 3 sizes;
  - the only text is the SAVED/SAVING pill.

  The brush-size buttons show the same tiny dot at three sizes, so they do not depict stroke width.
- **Loop 4:** instant, responsive strokes with no lag in captures.
- **FB 2:** silent. No brush sound, no "saved to My Creations" moment, and an eraser-on state that is only a thin orange border.
- **Prog 3:** the expressive range is deliberately small (correct), but there are no stamps or colouring pages for 3-year-olds who stall on a blank page.
- **Vis 4:** clean studio with SVG-sourced tool icons. The best tool chrome in the group.
- **Use 3:** pointer only (no keyboard/controller colour or tool cycling); the gallery problems are below.
- **Tech 3:**
  - **gallery draws and hit-tests only `records[:6]` of `MAX_PAINTINGS = 48`** (`painting_renderer.py:209`), so paintings 7–48 are unreachable;
  - **every New tap creates a stored blank record**;
  - at 48, New fails with a red pill and the child has no delete path;
  - resize/reopen decodes to the new canvas size **without preserving aspect** (stretched art).

**Redesign spec**
- Target: keep the instant blank-page studio. Add the two things 3-year-olds need: something to start from, and a library they can browse and tidy.
- Library:
  - adopt the shared drafts gallery (§C1): paged 2×3 cards with ◀ ▶, a hold-to-delete flow with a preview, and empty-state art;
  - New reuses the current record when it is still blank (no blank spam);
  - at the cap, New opens the gallery with the "full" card.
- Starters:
  - a 4th left-toolbar button opens 8 colouring-page outlines (cast and nature line art);
  - choosing one creates a new painting whose base canvas holds the outline;
  - the outline stays on top of paint as a non-erasable overlay layer that is flattened only on export (one overlay, not layers).
- Brush buttons draw true-size dots (8/18/34 px). The eraser gets a filled pink state plus a white brush-dot cursor while active.
- Juice:
  - soft brush loop SFX while drawing (procedural, bounded);
  - sparkle FX + Lilli `pose_cheer` corner pop when "Save to My Creations" succeeds.
- Input: arrow keys / D-pad move a focus ring across the palette and toolbar; Space/South selects. The canvas uses the platform virtual pointer.
- Aspect: decode with letterbox/fit into the canvas and store the native size in the record.
- New art:
  - `prop.colouring.{leo,lilli,momo,flower,house,fish,car,butterfly}`, line art 1024×600 at 4 px ink;
  - `icon.hud.{colouring_book}`;
  - `fx.sparkle`.
- Voice: none required (the shared platform "Saved in My Creations!" line is optional).
- Effort S (gallery via §C1; colouring overlay S–M). Risk: the overlay must stay one bounded surface; no layers UI.

---

## 3. officina_dei_suoni — Sound Workshop (age 5–7) · 26/40 · POLISH (merge host for foresta_parole)

Played:
- L1: hear /b/ and pick from pan / book / star (wrong pick, then right pick, then advance);
- L2 (seeded): the turtle picture with M / T / F tiles;
- L3 (seeded): "?AKE" then "?IG" with letter tiles;
- 800×480 OK (letterboxed).

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 2 | 4 | 2 | 4 | 4 |

- **Obj 4:** phoneme first (isolated /m/ etc., owner-accepted clips per `docs/reviews/2026-08-24_OFFICINA_DEI_SUONI_AUDIO_REVIEW.md`), then letter-sound, then initial-letter-in-word. It is correct, but only 8 consonants. L3 is the L2 task with the rest of the word shown, not "building".
- **Age 4–6 fit 3:** the icon prompt strip (🔊➡️🖼️❓) is clever. But L1 also shows the letter "B b", so non-phoneme readers can match by sight once they know letters.
- **Loop 3:** a three-choice quiz × 6. Solid but thin.
- **FB 2:**
  - a wrong pick only draws a blue outline, identical to keyboard focus;
  - a correct pick just advances (no visible celebration, Leo static);
  - completion uses the generic text card (Group A §C).
- **Prog 4:** real adaptive L1–L3 with bounded history (5/8 strong → up; 3 hinted misses → down).
- **Vis 2:**
  - emoji pictures are ambiguous for a sound task (frying pan reads "egg", log reads "wood", bulb for "lamp");
  - the pegboard pipe decoration is meaningless, and in L3 the word tiles sit on top of its rail and balls;
  - Leo is the on-model PNG.
- **Use 4:** pointer + ←/→/Space/R, big tiles.
- **Tech 4:** clean and bounded.

**Redesign spec**
- Target: the single letter-sound home for ages 4–6, with a short reward "catch" round. Every picture is unambiguous art, and every mistake becomes a spoken mini-lesson.
- Pictures: replace emoji with `prop.vocab.*` (Group A's shared noun set) for the 24 EN and 24 IT words. Pick nouns whose picture has one obvious name.
- L1 hides the letter tile until after the answer ("sound only"). The tile flips in on success, which links the sound to the letter.
- Wrong pick:
  - the card shakes and Leo `pose_point` points at the right card;
  - the feedback **is composed from existing clips**: `sound_b` → "book" (no new recordings);
  - the retry is unlimited.
- Right pick: the card pops into the workshop machine (replacing the pegboard), a gear spins, and Leo `pose_cheer` appears.
- L3 becomes real building: drag 2–3 letter tiles (first + last sound) into sound boxes for CVC words (pig, sun, map), spoken segment by segment from existing word clips.
- Catch reward round (from Foresta, §9) after every 2 sets.
- Completion: the shared cast completion scene.
- New art:
  - `prop.vocab.*` (~30 here, shared);
  - `prop.workshop.{machine,hopper,gear}`;
  - `ui.tile.letter` (shared);
  - `fx.{check_pop,gear_spin}`.
- Voice: none for EN/IT core loops (composed). New phoneme units beyond the 8 (d, n, r, h, g, z) need ~6 isolated phoneme clips per locale (owner approval).
- Effort M. Risk: L3 CVC needs medial-vowel phoneme clips that do not exist. Scope L3 to first + last consonant until vowel clips are approved.

---

## 4. writing — Writing & Words (age 5+, required anchor) · 24/40 · POLISH

Played: start (blank page, caret); typed mixed-case text with Return; emoji picker (7 category tabs, 6×3 grid); gallery (one text card); 800×480 emoji picker fits.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 4 | 3 | 3 | 2 | 2 | 3 | 3 | 4 |

- **Obj 4:** an authentic, uncluttered writing surface with 42 px text and first-class emoji, exactly as Phase-0 asks.
- **Age 3:** honest at 5+ (keyboard required), and emoji give younger children a path. But there is no letter feedback at all for an emergent writer.
- **Loop 3:** type → see → autosave. Calm and correct.
- **FB 2:** silent; save state is a lone green dot.
- **Prog 2:** **gallery draws only `records[:6]` of `MAX_DOCUMENTS = 120`** (`writing_renderer.py:222`); New spawns blank records; text-only cards are unidentifiable to a pre-reader.
- **Vis 3:** warm paper. The undo glyph renders as a broken hook, and the gallery cards are plain text.
- **Use 3:** keyboard + pointer with a large emoji picker. No controller path (acceptable for `text` profile, but toolbar focus would help).
- **Tech 4:** grapheme-aware undo/wrap is excellent engineering.

**Redesign spec**
- Target: stay the essential editor, add the two smallest things that make it work for 5-year-olds — hearing letters, and finding pages again.
- Library: shared drafts gallery (§C1) with paging and hold-delete. Cards show the first emoji large (or the first letter in a coloured "page colour") plus the first line, so a pre-reader can recognise "the dinosaur page".
- Page colour:
  - 6 paper tints chosen at New;
  - stored in the record;
  - used as the card colour.

  This is the cheapest identity cue.
- Optional letter echo (Parent-off by default, child toggle with an ear icon): on a letter keypress, play the letter **name** clip. Foresta's 26 EN letter-name clips (`a.wav … z.wav`) and the IT set move to a shared letter-audio bank (§9); no new recordings needed.
- Fix the undo icon (the shared `icon.hud.undo`). Show the save dot inside a small paper-plane icon with three states.
- Keep everything else; no formatting, no read-aloud of arbitrary text (no TTS assumption).
- New art: `icon.hud.{undo,ear,page}`, 6 paper-tint card frames (`ui.creation_card.document`).
- Voice: none (reuses the letter-name bank).
- Effort S. Risk: the letter echo must not lag typing; preload 26 clips (≈ 1 MiB) lazily on first toggle.

---

## 5. faccine_momo — Momo's Happy Faces (age 3+) · 24/40 · REWORK

Played: Free Mirror (Happy); Sad → tap cheek (comfort hearts); Angry (steam puffs); toggle to "How does it feel?" quiz (sleepy face, choices SLEEPY / SILLY).

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 4 | 3 | 4 | 1 | 2 | 3 | 4 |

- **Obj 3:**
  - naming 6 feelings is right for 3–4;
  - the voice lines model coping ("let's take a deep breath together: whooosh!"), which is excellent;
  - but **the quiz speaks the answer**: `momo_app.py:150–151` enqueues `game_prompt` and then the target emotion clip ("Yawn... so sleepy…").
- **Age 4:** big face; every emotion is spoken by Momo.
- **Loop 3:** mirror cycling and comforting Sad Momo are sweet. The quiz is a 1-of-2 forever.
- **FB 4:** hearts, confetti, puffs and zzz, plus character voice. The best feedback in the group.
- **Prog 1:** no stages and no scenarios. Recognition of isolated faces only, though the manifest claims social learning.
- **Vis 2:** Momo is a procedural purple oval with ears, **off-model** vs canonical Momo (antennae, fluffy body). The emotion buttons hold ~36 px emoji inside 92 px circles.
- **Use 3:** the mode toggle is a text pill; pointer only.
- **Tech 4:** small and bounded.

**Redesign spec**
- Target: from "name the face" to "understand the feeling". Recognise → explain (why does Momo feel this?) → help (what can we do?). The canonical Momo is the actor; other cast join in later stages.
- Stage 1, Mirror (free): the canonical `character.momo` expression set, big picture buttons (face art, no emoji, no words). Keep the cheek-comfort.
- Stage 2, Feelings detective:
  - Momo shows a face, and the prompt line is **only** `game_prompt`;
  - 3 face choices at age 4+;
  - a wrong pick plays the correct emotion clip as a model, then retry.
- Stage 3, What happened?
  - a 2-panel picture story: Momo's ice-cream falls, then Momo's face is blank;
  - the child picks the face;
  - 12 scenario cards, 2 per emotion.
- Stage 4, Help a friend:
  - Lilli/Tito/Dani shows a feeling with a scenario;
  - the child picks one of 2 helpful actions (hug, share, breathe, ask a grown-up);
  - the cast acts it out.
- This fills the P7b "empathy / social problem-solving" gap without a new Activity.
- Adaptive rule: 4 correct → next stage; 2 misses → stay with 2 choices. A stage chip uses progress dots.
- Completion: Momo `pose_cheer` + confetti.
- New art:
  - `character.momo.{sad,angry,silly}` expressions (then all 6 cast);
  - `scene.feelings.*` 12 two-panel cards (prop-scale 512×256);
  - `prop.help.{hug,share,breathe,grownup}`;
  - `icon.hud.mirror`.
- Voice (EN, request, Momo + 3 cast): 12 scenario narrations ("Oh no, my ice cream fell!"), 4 help lines ("Let's share!"), 3 cast feeling lines. About 20 lines.
- Effort M. Risk: the voice approval scope, and expression art for non-Momo cast.

---

## 6. orchestra_animali — Magic Orchestra (age 3+, music singleton) · 21/40 · RETHINK

Played: idle stage; tapped Drums and Trumpet; two rainbow keys; keys 5/6; coin counter rising per tap. 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 4 | 2 | 3 | 1 | 2 | 4 | 3 |

- **Obj 2:**
  - "music.rhythm.perception" is claimed, but there is no rhythm, pulse, echo or pattern task;
  - an 8-note C-major xylophone plus 5 one-shot instruments is a sound toy;
  - `feedback.perfect` and `prompt.free` strings are never used;
  - the Creations backing track is the only structured idea.
- **Age 4:** nothing can fail; big targets.
- **Loop 2:** free tapping is fun for ~60 s, then stops.
- **FB 3:** bounce and note particles.
- **Prog 1:** the coin counter goes up per tap and means nothing.
- **Vis 2:**
  - an "animal orchestra" **with no animals**;
  - emoji instruments in white discs;
  - a large empty dark stage.
- **Use 4:** pointer + 1–8 / A–K keys. The OS cursor is hidden and no Greia pointer is drawn (`main.py:78`).
- **Tech 3:** `draw_particles` renders an emoji glyph per particle per frame at shrinking sizes (`orchestra_renderer.py:155`). Rapid taps add 12 each, which means per-frame glyph rasterisation on the Acer.

**Redesign spec**
- Target: Greia's one Music home, "The Animal Band". The six cast are musicians, and the child plays *with* them through four short modes on one stage. This absorbs Group B's "Echo Drums" and the musical half of Group A's "Pattern Parade" instead of adding two Activities.
- Band:
  - Leo drum, Momo maracas, Lilli bells/xylophone, Tito trumpet, Flash tambourine, Dani keyboard;
  - each is a big tappable cast `pose_cheer` musician that plays its instrument;
  - the rainbow xylophone stays as the bottom bar.
- Mode picker is three picture doors on the stage: free / echo / pattern (no text).
- Modes:
  - **Jam (free):** current play; the band keeps a soft pulse (metronome bob) so taps feel on-beat.
  - **Echo:** a musician plays 2 → 6 beats (then soft/loud, then fast/slow) and the child repeats on the same musician. Tolerance is ±150 ms per onset at D1, then ±100 ms; 3 rounds per set.
  - **Pattern parade:** musicians march in AB / AAB / ABB / ABC, the child fills the gap and then extends the pattern; the finished pattern plays as a groove.
  - **Freeze** (see §B2): a stand-up mode where possible.
- Progression: echo length +1 after 3 clean echoes, −1 after 2 misses. Pattern type advances AB → AAB → ABB → ABC.
- Rewards: replace coins with stars earned per completed set (≤ 3 per set). The completion concert is the shared completion scene with the whole band.
- Creations:
  - keep the WAV backing-track consumer;
  - add a producer: "Record my song" renders the child's last 20 s of note events offline into a WAV (`role="music"`) for Teatrino shows.
- Perf: pre-render note/sparkle particles as `fx.note_burst` PNGs; draw the Greia pointer.
- New art:
  - `prop.instrument.{drum,maracas,bells,trumpet,tambourine,keyboard}` (hand-held, separate group per cast rules);
  - `character.<id>.pose_play` × 6 (a 2-frame strike pose);
  - `bg.stage.*` (shared with Teatrino);
  - `icon.hud.{door_jam,door_echo,door_pattern}`;
  - `fx.{note_burst,beat_ring}`.
- Voice (EN, request): "Listen… now you!", "Your turn!", "Again!", "What comes next?", "Let's play together!", 6 instrument names, "Freeze!", "Dance!". About 14 lines.
- Effort L. Risk: echo timing under the dummy/ALSA mixer latency on the Acer. Measure the onset-to-audio offset and calibrate it once per device.

---

## 7. shape_garden — Shape Garden (age 3+) · 20/40 · REWORK

Played: near-empty first screen (meadow, Dani in the lower-right corner); 8 taps planted random shapes on stems with pop-in and particles; reopen at 800×480 restored the project (letterboxed).

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 2 | 4 | 2 | 3 | 1 | 3 | 2 | 3 |

- **Obj 2:** the manifest claims `math.geometry.shape_recognition`, but **the shape, colour and size are random** (`garden_app.py:150–156`). Shapes are never named, and kind 2 is a **pentagon while the locale calls it "Triangle"**.
- **Age 4:** tap-anywhere is toddler-perfect.
- **Loop 2:** no choice, so no authorship.
- **FB 3:** pop-in and Dani hop, but silent.
- **Prog 1:** no clear, undo, move or delete. Beyond 120 shapes the oldest vanish silently.
- **Vis 3:** pleasant meadow (old v0.2 pack), primitive shapes, tiny Dani.
- **Use 2:**
  - **mouse cursor hidden with no Greia pointer drawn**;
  - no keyboard;
  - the Share/Import buttons (when brokered) are unlabeled arrow-in-box icons.
- **Tech 3:** a bounded, honest project model, a good base.

**Redesign spec**
- Target: a "shape sticker garden" where the child *chooses* each shape and colour, hears its name, moves it, and composes a picture that flows to Painting and Teatrino through My Creations.
- Tray: a bottom tray of 8 big shape buttons:
  - circle, square, triangle, rectangle, star, heart, oval, diamond;
  - the triangle is a real triangle;
  - plus 6 colour drops.

  A tap plants the selected shape. Dani names it ("Triangle!") on the first use per session and on long-press.
- Edit:
  - drag a planted shape to move it;
  - drag it onto the bin pot to remove it;
  - pinch/size via 3 size buttons;
  - undo (bounded 24).
- No silent eviction: at 120 the tray dims and a "garden full" picture appears.
- Shape-garden picture hints (optional, not a puzzle): a ghost picture (house = square + triangle, sun = circle + rays) can be toggled as a faint guide, for composition without failure.

  Silhouette *puzzles* stay with Group B's `torre_forme` rethink, to avoid overlap.
- Juice: a stem-grow animation, a per-shape chime pitch, and Dani `pose_cheer` after 5 shapes.
- Export: keep the flattened `composition` PNG and the PNG backdrop import. Label the buttons with `icon.hud.{share,import}`.
- Draw the Greia pointer; keyboard focus moves over the tray; the canvas uses the virtual pointer.
- Backdrop: switch to the promoted `bg.meadow_day.*` kit.
- New art:
  - `prop.shape.{circle,square,triangle,rectangle,star,heart,oval,diamond}` as flower-head variants;
  - `prop.garden.{bin_pot,watering_can}`;
  - `ui.ghost.{house,sun,car,tree}`.
- Voice (EN, request): 8 shape names, "Tap to plant a shape!", "What a beautiful garden!". 10 lines.
- Effort M. Risk: keep the project schema migration additive (`kind` indices change: map the old pentagon to `star`).

---

## 8. posta_di_leo — Leo's Post (age 5+) · 20/40 · REWORK (fallback: MERGE into Writing)

Played: editor (chalkboard postcard, 6 recipients, 6 emoji stamps); chose Momo + star; typed; SEND (the card clears, the counter goes to 1); MY POSTCARDS (one 160×100 card, preview text truncated without ellipsis); 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 2 | 2 | 2 | 2 | 3 | 3 | 3 |

- **Obj 3:** writing *to someone* (audience, "To:") is a genuinely distinct emergent-writing objective. As built, though, it is a second keyboard text box.
- **Age 2:**
  - requires a keyboard and reading;
  - every button is a word + emoji (SEND 💌, MY POSTCARDS 📬, CLEAR 🗑️);
  - the "Mailbox Full" dialog is a text paragraph.
- **Loop 2:** type → Send → the card simply disappears; there is no delivery.
- **FB 2:** synth beeps; **no send animation and no reply from the friend**.
- **Prog 2:** 20-card mailbox with tiny gallery cards.
- **Vis 3:** cast avatars are on-model PNGs, but **"PINA" is not a Greia cast member** (`postcard_content.py:30`, `character.pina` does not exist, a placeholder letter "P" disc is drawn) while Flash is missing.
- **Use 3:** big buttons; delete has a confirm (good).
- **Tech 3:** placeholder-asset bug; preview truncation.

**Redesign spec**
- Target: the pre-reader *communication* Activity. Make a postcard with a picture front and a voice or written back, send it, and watch the friend receive and react. Writing stays the free page.
- Card front: choose a picture through the trusted picker. Accept `image/png` roles `drawing` / `composition` / `picture`, so Painting / Shape Garden / Teatrino posters become cards. Otherwise choose one of 6 illustrated stamp-scenes.
- Card back, two equal routes:
  - (a) type (5+), as today, with the bounded grapheme-safe draft;
  - (b) **voice message**: hold the big mic for ≤ 15 s using the shared platform recorder (§C2); stored as a private WAV with the card.
- Recipients: the canonical six (replace Pina with Flash).
- Send:
  - the card folds into an envelope, Leo `pose_cheer` flies it off-screen, a mailbox flag pops;
  - after 2 s the recipient appears with `pose_cheer` and says their thank-you line.
- Mailbox: the shared drafts gallery (§C1) with big card fronts. Full = pictorial shelf card. Delete keeps its confirm, moved to hold-to-delete.
- Creations: keep the `document`/`postcard` UTF-8 import/export; add the PNG front consumer; voice postcards stay private in V1.
- Buttons become kit icons (send = envelope, mailbox, broom) with no words.
- Fallback if voice/picture is not funded: retire Posta and add a "postcard paper" template (recipient avatar + stamp row) to Writing's New. This avoids two keyboard editors.
- New art:
  - `prop.postcard.{front_frame,back_lines,envelope,mailbox,flag}`;
  - `prop.stamp.{heart,sun,star,rainbow,flower,butterfly}` (replace emoji);
  - `fx.envelope_fly`;
  - `icon.hud.{send,mailbox}`.
- Voice (EN, request): 6 cast thank-you lines ("A postcard for me? Thank you!"), Leo "Who is it for?", "Pick a picture!", "Tell your message!", "Off it goes!". 10 lines.
- Effort M. Risk: the voice-recording privacy scope (private only, never published, in V1).

---

## 9. foresta_parole → officina_dei_suoni merge: concrete evaluation

Group A (§11) proposed retiring Foresta and keeping its *catch* mechanic as Officina's reward round. **I accept the merge, with one correction about where Foresta's assets go:**

1. **Audio layers differ.** Foresta's 77 EN clips are letter **names** plus "X as Word" prompts ("G as Giraffe", "O as Owl"). Officina is **phoneme-first** (`sound_m` = /m/). Feeding Foresta's prompts into Officina would re-mix letter names into the phoneme ladder. Several of its exemplars also teach the wrong sound for a phonics task: Owl (/aʊ/), Island (/aɪ/), Giraffe (/dʒ/), Queen (/kw/).
2. **Asset routing:**

   | Foresta asset | Destination | Rule |
   |---|---|---|
   | `a … z` letter-name clips | Shared letter-audio bank, consumed by Alfabeto Leo (letter names, Group A owner) and Writing's optional letter echo (§4) | Letter names, not phonemes |
   | "X as Word" prompts | Alfabeto only | Same |
   | Word clips with a regular initial phoneme in Officina's 8 units | Officina word bank | EN flower, lion, penguin, tiger; IT pesce, tigre. Adds 4 EN and 2 IT words with no new recordings |
   | Other word clips | Officina distractor pool | Never targets |

3. **The catch round in Officina:**
   - 15 s after every 2 sets: picture bubbles drift up and the child pops every picture starting with the set's phoneme;
   - the phoneme clip is replayed on each correct pop;
   - Group A's motion rules apply (no overlap, ≤ 40 px/s, ≥ 72 px, focus-cycle for keyboard/controller);
   - **no letters in bubbles at D1**, so it stays phonemic;
   - stars from the round feed Officina's progress, not a separate score chip.
4. **Phonemes Foresta covers that Officina lacks** (d, g, h, n, r-EN, v, z and short vowels) still need new isolated phoneme recordings. Foresta cannot supply them. Until owner approval, the merged Officina keeps 8 units and grows by words, not sounds.
5. **Migration:** retire the Foresta package after the bank moves. Its progress becomes a one-time Officina star grant; nothing else is portable.

Net: the merge is correct and cheap (S for the catch round, S for the asset re-homing). It removes the fourth "letter that goes with a picture" loop without losing any approved audio.

---

## 10. storie_della_mia_voce — Stories of My Voice (age 4–7) · 19/40 · RETHINK (fallback: MERGE into Teatrino)

Played: scene picker (Forest / Sea / Sky / Friends as colour-block cards); tapped Forest (recording **starts immediately**, 30 s countdown); stopped; replay screen ("NICE!", Play / Try again / Next scene); Next auto-starts the Sea recording; after all four, "STORY SAVED!"; MY STORIES (one card of 4 coloured dots + duration, a red **X that deletes on one tap**). 800×480 OK.

| Obj | Age | Loop | FB | Prog | Vis | Use | Tech |
|---|---|---|---|---|---|---|---|
| 3 | 3 | 2 | 2 | 1 | 2 | 3 | 3 |

- **Obj 3:** oral narration is valuable, and it is the only WAV *producer* (for Teatrino/Orchestra). But "narrative.sequencing.scene_to_scene" is claimed while the four scenes are unrelated places with nothing to narrate.
- **Age 3:**
  - the big mic is good;
  - there is no spoken guidance (only the title clip);
  - headings are text ("PICK A SCENE! FOUR SCENES TO FILL WITH YOUR VOICE");
  - the recording starts with no "ready" beat.
- **Loop 2:** talk at an empty colour block.
- **FB 2:** a volume bar and "NICE!" text.
- **Prog 1:** fixed 4 scenes.
- **Vis 2:**
  - primitive half-white scene cards;
  - the placeholder icon (asset audit S1);
  - the story card has no identity.
- **Use 3:**
  - big targets;
  - **one-tap story delete**;
  - "Next scene" is any tap below y = 510;
  - an Activity-drawn back arrow sits top-right.
- **Tech 3:** a second private microphone implementation (`voice_microphone.py`) parallel to Teatrino's `teatrino_audio.py`.

**Redesign spec**
- Target: "Story Cards". The child tells a story *in order* from 3–4 picture cards. This becomes Greia's narrative-sequencing and oral-language Activity, distinct from Teatrino's free puppet play. It extends Group B's "First, Then, Last" proposal into a creative producer instead of a separate quiz.
- Stage A, order it: 4 cards of a mini-story arrive shuffled (Tito plants a seed → waters → sprout → flower); the child drags them onto 1-2-3-4 slots. Wrong order: cards gently swap back, unlimited.
- Stage B, tell it: each card enlarges in turn; a 3-2-1 pip ring; the child records ≤ 20 s per card; Play / Redo per card.
- Stage C, watch it: the cards play as a slideshow with the child's voice. Saved as one story with 4 WAVs.
- Content: 8 mini-stories (seed, rainy day, birthday cake, lost teddy, snowman, bath time, picnic, bedtime), all from shared cast + props. An "own picture" option takes PNG drawings from the picker as cards.
- Library: shared drafts gallery (§C1). The story card shows card 1's art; hold-to-delete.
- Creations: publish each narration as `narration` WAV (as now); add `image/png` consumer for own cards.
- Shared platform recorder (§C2); drop the private mic module.
- If not funded: merge into Teatrino as a "Story Cards" backdrop set (the 4 scene cards become sequential backdrops during REC) and retire the package.
- New art:
  - `scene.story.<story>.{1,2,3,4}` × 8 (512×300 card crops, Opus-authored from cast/props);
  - `ui.slot.numbered`;
  - `icon.hud.{mic,redo,slideshow}`;
  - a real Activity icon.
- Voice (EN, request): "Put the pictures in order!", "What happens first?", "Now tell me your story!", "Tell me about this picture!", "What a great story!", plus 8 one-line story titles. 13 lines.
- Effort M (art-heavy). Risk: art volume (32 cards). Start with 3 stories.

---

## Cross-Activity findings

### A. Duplicates and overlaps

| Overlap | Today | Recommendation |
|---|---|---|
| Voice recording ×2 (×3 with voice postcards) | Storie (`voice_microphone.py`) and Teatrino (`teatrino_audio.py`) each own capture, gain and WAV encoding | One platform recorder (C2). Storie = sequenced narration, Teatrino = performance, Posta = message. Differentiate by intent, not by mic code. |
| Text editors ×2 | Writing (anchor) and Posta (second keyboard editor) | Posta becomes picture + voice communication (§8), or merges into Writing as postcard paper. |
| Storytelling ×2 | Storie (talk over scenes) and Teatrino (talk over puppets) | Storie → ordered Story Cards (sequencing); Teatrino → free performance. Each can consume the other's outputs through Creations. |
| Shape making ×3 | Shape Garden (composition), Painting (free), torre_forme (Group B silhouette tower) | Shape Garden = free composition with named shapes and optional ghost hints; silhouette puzzles stay in torre_forme only. Share `prop.shape.*` / `prop.blocks.*`. |
| Letter↔picture | Officina, Foresta, Alfabeto, Festa D4 | Foresta merges per §9. Letter-*name* audio goes to Alfabeto/Writing, letter-*sound* to Officina. |
| Music | Orchestra only, plus two new-Activity proposals from Groups A/B (Pattern Parade, Echo Drums) | Fold both into the Orchestra rethink (§6) as modes. The Music family stays one strong Activity instead of three thin ones. |
| Emotions / care | Faccine (faces) vs Group B's Pet House (care routines) | Faccine owns feelings, empathy and helping (§5 stage 4); Pet House owns routines and needs. Do not add "pet feelings" quizzes. |

### B. Curriculum gaps for ages 3–6 (new Activity proposals, max 3)

Groups A and B already proposed patterns, sorting, blending, sequencing and rhythm echo. Two of those are absorbed here: rhythm echo and musical patterns go into Orchestra, and sequencing into Story Cards. The genuine remaining gaps in the creative/music/social area:

1. **Leo's Story Time** (Learn, age 3–6): listening comprehension and oral vocabulary.
   - Leo reads a 6–8-page picture book aloud (prerecorded), with tap-to-hear words on pictures.
   - Then 3 picture questions: who, what happened, what next. Every answer is a picture.
   - Greia has many *producing* language Activities and no *receptive* story Activity, yet listening comprehension is the strongest early-literacy predictor after phonology.
   - Reuses `scene.story.*` art from Story Cards.
   - Voice-heavy: about 8 books × 10 lines per locale, so it needs owner voice approval.
2. **Freeze Dance** (Play, age 3–6): executive function (stop/go inhibitory control) and gross motor away from the screen, which P7b lists explicitly as a gap.
   - The Animal Band plays; the cast dance. The music stops → "Freeze!" and the screen shows a frozen statue pose. Rule-switch variants: freeze on the drum only, dance slow or fast with the tempo.
   - No input is required (honour-system movement), with optional keyboard/controller "I froze" taps for the 5–6 rule-switch level.
   - It may launch as a fourth door inside Orchestra if the catalogue must not grow; it is listed here because its session pattern (stand up, 3 min) is different.
3. No third Activity. Social problem-solving and empathy are delivered by Faccine's stages 3–4 rather than a new card. This avoids catalogue inflation.

### C. Shared systems and assets to author once

**C1. Shared "drafts gallery" for Activity-private creations.**

This is the main cross-cutting fix. It extends the platform's existing `CreationsGalleryScreen` view model to Activity-private records.

Painting, Writing, Posta, Storie and Teatrino each hand-roll a gallery, and each has a custody bug:
- 6/48 and 6/120 hidden;
- one-tap delete ×2;
- silent eviction in Teatrino;
- blank spam from New ×2;
- tiny 160×100 cards in Posta.

The shared component provides:
- paged 2×3 big cards with ◀ ▶ (or kit progress dots);
- an empty-state card;
- hold-to-delete with a large preview, confirm/cancel and a brief undo;
- a "shelf full" refusal card (never evict);
- bounded per-page thumbnail cache;
- keyboard/controller focus.

Each Activity supplies only a `card_renderer` (thumbnail, poster, first emoji + page colour, story card 1).

**C2. One platform voice recorder** (`greia_platform` audio capture service): device discovery, bounded capture (≤ 45 s), gain, silence detection, WAV encoding and teardown on Home/stop. Consumers: Storie, Teatrino, Posta voice postcards. It removes two private mic stacks.

**C3. Pointer visibility.** Shape Garden, Teatrino and Orchestra call `pygame.mouse.set_visible(False)` and never call `draw_activity_pointer`, so a mouse or touchpad user sees no cursor (the same class as Group B's costruiamo_ponti note). Fix this in the runtime adapter: when an Activity hides the OS cursor, the platform overlay draws the Greia pointer.

**C4. Missing Creations edges** (journeys the plan wants that no Activity offers yet):

| Edge | Role |
|---|---|
| Painting / Shape Garden / Teatrino poster → Posta card front | `image/png` |
| Painting → Story Cards own card | `image/png` |
| Orchestra → Teatrino background song | `audio/wav`, role `music` |
| Teatrino → poster PNG | role `picture` |

Officina correctly stays a non-consumer (its pedagogy needs curated audio).

**C5. Shared assets** (SVG → PNG by `rsvg-convert`, per `GREIA_SVG_AUTHORING_RULES.md`):

| Semantic IDs | Kind | Consumers here (→ others) |
|---|---|---|
| `bg.stage.{curtain_left,curtain_right,valance,boards,wall_dark}` | scene layers 1024×600 | teatrino, orchestra, freeze dance → specchi_magici |
| `character.<id>.puppet` × 6 (rod + canonical body, talk/jump keys) | cast | teatrino, story cards |
| `character.<id>.{sad,angry,silly}` expressions (Momo first, then 6) | cast faces | faccine, teatrino puppets, wrong-answer feedback everywhere (pairs with Group A's `pose_think`) |
| `character.<id>.pose_play` × 6 + `prop.instrument.{drum,maracas,bells,trumpet,tambourine,keyboard}` | cast / prop | orchestra, freeze dance → Pattern Parade content |
| `prop.shape.{circle,square,triangle,rectangle,star,heart,oval,diamond}` | prop 256 | shape_garden, painting stamps (later) → torre_forme, specchi_magici |
| `prop.colouring.*` (8 line-art pages) | scene 1024×600 line art | painting |
| `prop.postcard.*`, `prop.stamp.*` (6) | prop | posta (stamps also as Writing emoji-free stickers later) |
| `scene.story.<story>.{1..4}` (8 stories) | card 512×300 | story cards (storie), Leo's Story Time, teatrino backdrops |
| `prop.vocab.*` (Group A set; Officina needs ~30 EN/IT nouns) | prop 256 | officina (+ foresta catch round) |
| `ui.creation_card.{drawing,document,voice,show,postcard}` + `ui.slot.numbered` | UI | drafts gallery (C1), story cards |
| `icon.hud.{share,import,new,undo,eraser,colouring_book,mic,mic_on,mic_off,rec,stop,play,redo,film,broom,send,mailbox,ear,page,slideshow,mirror,door_jam,door_echo,door_pattern,fx_*}` | HUD 96 | all nine (replaces text/emoji buttons) |
| `fx.{curtain_open,dust_puff,envelope_fly,note_burst,beat_ring,gear_spin,check_pop,sparkle,heart_pop}` | FX 128 | all nine |

### D. Top cross-cutting rules for the main agent

1. **Custody first, before any polish.**
   - Ship the shared drafts gallery (C1);
   - remove Teatrino's silent eviction;
   - put hold-to-delete in Teatrino and Storie;
   - stop New from spawning blanks in Painting and Writing.

   These are child-data bugs against the Phase-0 and Creations contracts, not design preferences.
2. **Turn the music and emotion toys into learning loops without growing the catalogue.**
   - Orchestra becomes the Animal Band, with Jam / Echo / Pattern (and Freeze) modes. This absorbs the Echo Drums and Pattern Parade proposals.
   - Faccine goes recognise → explain → help. Remove the spoken answer in its quiz now (a one-line fix).
3. **Make every creative tool word-free and on-model, then connect them.**
   - Kit icons instead of text buttons (Teatrino, Posta, Storie, Faccine);
   - canonical cast puppets and Momo;
   - one platform recorder (C2) and the Greia pointer (C3);
   - add the four missing Creations edges (C4), so Painting → Posta / Story Cards and Orchestra → Teatrino become real journeys.
