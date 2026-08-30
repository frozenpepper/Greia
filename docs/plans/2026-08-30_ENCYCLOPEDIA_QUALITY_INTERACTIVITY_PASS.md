# Greia Encyclopedia — Quality, Engagement, and Interactivity Implementation Plan

**Date:** 2026-08-30  
**Implemented:** 2026-08-30  
**Reviewed:** 2026-08-30 — faa46ec4 IMPLEMENTED, NOT ACCEPTED  
**Corrected:** 2026-08-30 — see §14  
**Scope:** visual/interaction quality pass for the Encyclopedia after E3 structural acceptance  
**Status:** **IMPLEMENTED / OWNER RUNTIME REVIEW PENDING**  
**Main objective:** move the encyclopedia from “static illustrated pages with hotspots” to **engaging interactive discovery pages** suitable for pre-readers and young children.

---

# 1. Strategic goal

The encyclopedia should no longer be treated mainly as a sequence of static illustrated pages with a selection ring and a fact reveal.

The target experience is:

1. **see a lively scene**
2. **move focus between a small number of clear interactive objects**
3. **hear the selected object’s name**
4. **manipulate something meaningful**
5. **see an immediate visual reaction**
6. **optionally open a simple factual explanation**

This means the next pass must focus on:

- **better focus/highlight language**
- **ambient animation**
- **meaningful interactivity**
- **stronger subject illustration quality**
- **clear page-level interaction grammar**
- **reduced click frustration**
- **higher engagement/replay value**

---

# 2. Core design principles

## 2.1 Pre-reader first
The child must be able to do something interesting before reading anything.

- text must support, not rescue, meaning
- interaction affordances must be visual and large
- object identity must be recognizable without labels
- narration/audio should reinforce selection and discovery

## 2.2 Fewer but better interactive targets
Each page should have a **small number of clear, meaningful targets**.

Avoid:
- crowded hotspot fields
- tiny click areas
- too many equivalent interactables

Prefer:
- 3 to 6 meaningful interactive objects
- one “main toy” interaction per page
- one “discover more” path

## 2.3 One page = one main interactive idea
Every page should have a memorable mini interaction.

Examples:
- volcano erupts
- pyramid gets assembled
- gears turn each other
- lungs inflate
- selected planet is highlighted while orbiting
- bee moves between flower and hive

## 2.4 Reusable system, page-specific toys
We should create reusable interaction primitives, then compose them into page-specific activities.

Reusable primitives:
- left/right target cycling
- large focus highlight
- activate current target
- open details
- start/stop animation
- slider
- toggle
- drag-and-place
- sequence assembly
- reveal overlay

---

# 3. High-level implementation tracks

## Track A — Global interaction/focus redesign
**Purpose:** fix the ugly selection language and define a cleaner universal interaction model.

### A1. Remove generic selection circles
Current selection circles are visually poor and often do not fit object shapes.

Replace with a page-aware focus language using:
- fitted outline or silhouette-aware highlight
- soft glow / halo
- subtle scale-up
- pulse / breathe animation
- slight lift or shadow
- optional page-themed highlight treatment

### A2. Define page focus states
Every selectable object should support:

- **idle**
- **focused**
- **activated**
- **disabled** (if needed)

Minimum visual behavior:
- idle: no emphasis
- focused: glow + slight motion/pulse
- activated: clear reactive animation

### A3. Standardize navigation grammar
Default page controls:

- **left/right arrows** or left/right navigation actions: cycle targets
- when focused, the object’s **name is spoken**
- **big lens / magnifier button**: open “discover more”
- **page-specific interaction control**: button, slider, drag, toggle, etc.

### A4. Redesign always-selected menu state
The main menu always has one selected item, so the selected state must feel integrated into the book page.

Use:
- portal glow behind the current category
- slight enlargement
- subtle bounce/pulse
- fit-aware highlight instead of ring
- optional sparkles or light rays

### A5. Define input safety and ergonomics
- no fast-moving tiny click targets
- minimum hit area for key content
- no required pixel-perfect clicks
- keyboard/controller/pointer all remain viable

---

## Track B — Ambient animation layer
**Purpose:** make pages feel alive even before interaction.

Each page should have at least:
- **1 scene-level ambient motion**
- **1 focused-object idle animation**
- **1 activation reaction**

Examples of ambient motion:
- drifting clouds
- twinkling stars
- swaying grass
- gentle water motion
- subtle presenter idle animation
- floating dust in historical scenes
- tool/workbench shimmer or bob in machines

Rules:
- low-cost animation
- loop cleanly
- not too distracting
- should not obscure hit targets

---

## Track C — Interactive toy layer
**Purpose:** add an actual “playful discovery” mechanic to each page.

We should define a small library of reusable page toys:

### C1. Start/trigger toy
Examples:
- Start volcano
- Start rain
- Start gears
- Start heartbeat
- Start orbit highlight

### C2. Slider toy
Examples:
- eruption strength
- orbit speed
- wind/rain strength
- gear speed
- breathing strength

### C3. Toggle toy
Examples:
- day/night
- inside/outside
- labels on/off
- bones/organs view
- calm/erupting

### C4. Drag-and-place toy
Examples:
- place pyramid blocks
- connect gear system pieces
- place fossils
- build a bridge
- put planets in order (future)

### C5. Guided sequence toy
Examples:
- assemble 3-step pyramid
- observe seed-to-plant steps
- see food chain flow
- show machine cause/effect sequence

---

## Track D — Art quality triage and redraw pass
**Purpose:** raise recognizability and eliminate weak/problematic drawings.

Create three statuses for every page/object:

- **ACCEPTABLE**
- **NEEDS POLISH**
- **NEEDS REDRAW**

Redraw first when:
- the subject is not immediately recognizable
- anatomy is broken or detached
- motion/mechanics are misleading
- the illustration is muddy/confusing
- the page relies on text to explain the drawing

---

# 4. Proposed development order

This order aims to maximize visible improvement early while building reusable systems first.

## Phase 1 — Interaction foundation
**Goal:** fix the biggest cross-cutting UX problems first.

### Deliverables
1. new selection/focus system
2. main menu selected-state redesign
3. standard left/right navigation arrows
4. standard large “discover more” lens button
5. standard spoken-name-on-focus behavior
6. standard activation-state behavior hooks
7. baseline ambient animation support

### Acceptance criteria
- no generic ugly selection circles remain
- focused objects are visually attractive and readable
- always-selected main menu looks intentional
- focus changes are obvious without text
- selection feels consistent across pages

## Phase 2 — High-value interaction pages
**Goal:** transform the most promising pages first.

Recommended order:

1. **Space / Solar System**
2. **Earth & Nature / Volcano**
3. **History / Pyramids**
4. **Machines**
5. **Body**
6. **Animals**
7. remaining section pages and entries

Reason:
- these pages naturally benefit most from playful interactivity
- they will quickly define the encyclopedia’s new identity
- they provide reusable interaction patterns for later pages

## Phase 3 — Art redraw pass on worst assets
**Goal:** fix the drawings that are actively harming readability or quality.

High-priority objects/pages:
- Earth planet
- weak planets in solar system
- weak animal drawings
- any page with unclear subject identity
- any page where interaction is good but visuals remain poor

## Phase 4 — Page-family rollout
After the foundation and key showcase pages are improved, roll the model out systematically to:

- Home
- Section overview pages
- factual entry pages

Do not try to bring all 43 pages to full rich interactivity at once. Roll out by family.

---

# 5. Global interaction/UI spec

## 5.1 Universal controls

### Focus navigation
- left/right arrow buttons on screen where appropriate
- keyboard/controller left/right support
- pointer still allowed
- focusing a target should:
  - highlight it
  - slightly animate it
  - speak its name

### Discover/details button
A large clear button:
- lens or magnifier icon
- large hit area
- always visually obvious
- opens the focused explanation/fact mode for current target

### Page-specific action button
One or more large buttons depending on page:
- start
- erupt
- build
- spin
- breathe
- listen
- grow
- show inside

### Optional controls
Use only when they truly improve the page:
- slider
- toggle
- drag
- step sequence

## 5.2 Focus visuals
Replace circles with:

- silhouette/fitted outline
- glow
- shadow/lift
- pulse
- optional sparkle or motion trace

Never let focus obscure the object.

## 5.3 Audio behavior
When possible:
- focus change speaks the object name
- interaction trigger may play page-themed reaction audio
- discover button opens narration/fact lane
- audio should reward interaction, not just confirm menus

---

# 6. Page-by-page priorities and concepts

## 6.1 Home / category selection
**Priority:** very high  
**Current issue:** selected icon treatment is ugly; page feels too static.

### Goals
- make category selection feel magical and alive
- better integrate selected state into book artwork
- make categories feel like portal worlds

### Changes
- remove ring selection
- center 3x2 icon block as already approved
- give selected category:
  - soft glow behind portal
  - pulse/breath
  - slight scale increase
  - optional sparkle/light effect
- ambient page touches:
  - slight shimmer on book
  - subtle presenter idle motion
  - tiny motion inside each world icon if affordable

### Acceptance
- selected category looks attractive, not debug-like
- menu remains readable and child-friendly
- category switching feels satisfying

## 6.2 Space / Solar System
**Priority:** highest showcase page  
**Current issue:** planets orbit too fast; some planets are weak; Earth is especially poor; clicking moving targets is frustrating.

### Proposed model
#### Scene
- slower orbit animation
- planets continue orbiting, but not so fast they become frustrating
- orbit path visible and decorative

#### Navigation
- left/right arrows cycle through planets
- current planet becomes highlighted while still orbiting
- planet name is spoken on focus
- highlighted orbit path or subtle halo around current planet

#### Big details button
- large lens/telescope/magnifier button
- opens focused planet information

#### Extra interaction
Optional:
- orbit speed slider: slow / medium / fast
- pause/resume orbit button
- labels toggle

### Art fixes
Redraw/upgrade:
- Earth (highest priority)
- Jupiter
- any planet that does not read instantly

### Acceptance
- user can explore planets without click frustration
- Earth is instantly recognizable
- page feels dynamic and premium
- interactivity reinforces learning

## 6.3 Earth & Nature / Volcano
**Priority:** highest showcase page  
**Current issue:** needs a stronger interactive toy.

### Proposed model
Main toy:
- **Start Volcano** button

### Behavior
- press start
- ground rumble
- smoke rises
- lava erupts
- ash/rocks animate
- eruption settles

### Optional controls
- eruption strength slider
- smoke on/off
- inside/outside view toggle

### Related page elements
Other Earth/Nature targets can later include:
- rain start button
- rainbow after rain
- ocean waves motion
- tree growth or wind motion

### Acceptance
- volcano interaction is memorable and immediately rewarding
- child sees cause/effect clearly
- page no longer feels static

## 6.4 History / Pyramids
**Priority:** very high  
**Current issue:** static viewing is less engaging than earlier assembly prototype.

### Proposed model
Main toy:
- **assemble a small pyramid using a few blocks**

### Behavior
- a few block pieces are available
- child moves or places them in sequence
- with each success:
  - pyramid visually builds
  - dust puff or worker reaction
  - short narration cue
- final placement may add capstone

### Discover mode
Large lens button:
- explains pyramids
- construction idea
- workers, blocks, precision

### Acceptance
- page has a memorable light-construction toy
- assembly is simple, not fiddly
- interaction makes the concept stick

## 6.5 Machines
**Priority:** very high  
**Current issue:** should naturally be rich in cause/effect.

### Proposed model
Provide meaningful cause/effect interactions.

#### Gear page
- big start/turn button
- gears visibly rotate together
- slider adjusts speed
- show relation between connected gears

#### Other machine ideas
- magnet attracts objects
- bicycle wheel spins
- propeller spins
- bridge opens/closes or reacts

### Acceptance
- every machine page has obvious mechanical payoff
- interactivity teaches cause/effect rather than just showing a picture

## 6.6 Body
**Priority:** high  
**Current issue:** room concept is better, but still needs engaging behavior.

### Proposed model
Targets:
- heart
- lungs
- jaw/teeth
- eye/ear
- skeleton

### Interactivity examples
- heart beats
- lungs inflate/deflate
- jaw opens/closes
- skeleton highlights body parts
- ear/eye plays sensory-themed response

### Acceptance
- page feels like a real discovery room
- interactions are intuitive and physically meaningful

## 6.7 Animals
**Priority:** high  
**Current issue:** recognizability still matters a lot; page needs stronger playful behaviors.

### Proposed model
For each selected animal:
- speak its name
- highlight animal
- allow one simple playful reaction

Examples:
- lion roars / mane reacts
- elephant raises trunk
- bee buzzes to flower/hive
- octopus wiggles arms
- frog jumps
- penguin slides or waddles

Possible discover modes:
- where it lives
- what it eats
- how it moves

### Acceptance
- animals are recognizable
- each animal has a memorable little behavior
- the page feels lively rather than tableau-only

---

# 7. Section/page implementation order

Recommended exact order for implementation:

1. **Global focus redesign**
2. **Global navigation/discover button system**
3. **Ambient animation framework**
4. **Main menu selected-state redesign**
5. **Solar system rework**
6. **Earth/Volcano rework**
7. **Pyramids mini-assembly**
8. **Machines cause/effect pass**
9. **Body interaction pass**
10. **Animals interaction + redraw pass**
11. **Apply improved design language across other section pages**
12. **Then move into factual entry migration under the new standard**

This order ensures we do not generate lots of content pages under a weak interaction model.

---

# 8. Suggested technical work breakdown

## System-level tasks
1. Replace current focus ring renderer with fitted highlight system
2. Create reusable focus-state animation helper
3. Create standard left/right navigation component
4. Create standard large “discover more” button component
5. Create reusable page action button component
6. Create optional reusable slider/toggle widgets
7. Create ambient animation helpers
8. Add audio hooks for selection-name playback
9. Ensure pointer + keyboard/controller parity for these controls

## Page toy primitives
1. start/stop trigger pattern
2. slider-controlled animation parameter
3. drag-and-place helper
4. simple sequence/assembly helper
5. highlighted-target narration hook
6. reveal/details panel behavior

## Content/art tasks
1. redraw poor planet art, starting with Earth
2. review all animals for recognizability
3. review all major page hero objects
4. create small animation frames or parametric movement designs
5. make sure every toy has a clear visual payoff

---

# 9. Acceptance criteria for the quality pass

The pass should be considered successful only when:

## Focus/UI
- no ugly generic selection circles remain
- focused states are attractive and readable
- main menu selected state feels integrated into the book artwork

## Engagement
- every main page has at least one ambient animation
- every main page has at least one meaningful toy interaction
- activation visibly changes something important

## Learnability
- children can discover something before needing text
- focused item names can be reinforced via audio
- details mode is optional, not required for basic engagement

## Art quality
- main hero objects are recognizable
- worst problem illustrations have been redrawn
- no page relies on text to explain ambiguous art

## Usability
- moving targets are not frustrating to click
- hit areas are large enough
- pointer/keyboard/controller remain viable

---

# 10. What should NOT happen

- do not keep migrating many factual pages under the current weak focus model
- do not spend time polishing tiny details before fixing focus/interactivity foundations
- do not add excessive micro-hotspots
- do not make interaction depend on precise clicking of moving targets
- do not let text become the main way to understand drawings
- do not turn every page into a separate complex mini-game
- do not sacrifice simplicity or responsiveness for flashy but heavy effects

---

# 11. Recommended next implementation tranche

## Tranche 1
- global focus redesign
- menu selected-state redesign
- standard arrows + discover button
- selection-name audio hook

## Tranche 2
- solar system interaction redesign
- Earth redraw
- orbit speed reduction / navigation arrows / lens button

## Tranche 3
- volcano start button + eruption animation
- optional slider/toggle

## Tranche 4
- pyramids assembly interaction

## Tranche 5
- machines interaction pass

## Tranche 6
- body interaction pass

## Tranche 7
- animal recognizability + playful reaction pass

That is the order I recommend before broad new factual-entry expansion.

---

# 12. Final recommendation

The encyclopedia should now be treated as moving into a new phase:

```text
STRUCTURAL ACCEPTANCE COMPLETE
-> ENGAGEMENT / INTERACTIVITY / ART-QUALITY PASS
-> THEN BROADER ENTRY EXPANSION
```

The highest-leverage move is **not** immediately creating more static content.

The highest-leverage move is:

1. fix the global focus language  
2. make the pages feel alive  
3. add memorable toy-like interactions  
4. redraw the worst illustrations  
5. then continue expansion under the improved standard

---

# 13. Completion — 2026-08-30

**Status: COMPLETE** — all 7 tranches + systematic rollout implemented and verified.

**Implemented:**
- **Tranche 1** `enciclopedia_presentation.py:226` `draw_focus_patch(time,pulse)` non-occluding halo, `draw_portal_focus` glow+sparkle, `draw_navigation_arrows 68→84` + `draw_discover_button 34→44`, `announce_focus_name`/`encyclopedia_focus_cue` ledger-safe, ambient helpers; `pages/home.py:77` portal glow, `pages/space.py:104` slower orbits `1.25→0.62`, `pages/earth/animals/body/machines/history` unified focus.
- **Tranche 2** `space` slower orbits, `decorate_planet` Earth continents `96,168,92` + cap, Jupiter bands+spot, Mars/Venus etc, `draw_speed_slider` `148×14` + `draw_pause_button` `44` + `draw_labels_toggle` `44` at `space:246`.
- **Tranche 3** `pages/volcano.py:34` `VolcanoModel.strength/rumble/smoke`, `draw_erupt_button 88` + `draw_smoke_toggle 44` + `draw_speed_slider`, rumble `sin*38*3px`, lava `14→19`, ash `16+6*strength`.
- **Tranche 4** `pages/pyramids.py:41` `PYRAMID_SUPPLY 4×68×36` `(180,480)` → `PYRAMID_TARGET 4×110×14` `(450,432)` etc, `assembly_placed/animating/progress/dust`, `_draw_assembly` stone `240,218,165` + dust puff, `draw_animal_action_button` hint.
- **Tranche 5** `pages/gears.py:53` `GearTrainModel.SPEED_LEVELS 0.45/0.85/1.45` + `nudge`, `GEAR_SPECS 72/58/47` live `draw_gear` teeth `3px`, `draw_turn_button 88` + `draw_direction_toggle 44` + `draw_speed_slider` at `gears:319`.
- **Tranche 6** `pages/heart.py:11`/`lungs.py:11` `draw_heart_button 88` `draw_breathe_button 88` + `bones/teeth/senses` unified focus `16/time` + arrows; `pages/bones.py:145` `senses.py:102`.
- **Tranche 7** `pages/animals.py:149` `ambient_sway` grass 4× + presenter sway, `pages/lion.py:11`/`elephant.py:11` `draw_animal_action_button(animal)` `lion`/`elephant` + `octopus/bee/penguin/frog` systematic via `draw_animal_action_button(animal)` + `draw_focus_patch`.
- **Systematic** `magnet/bicycle/airplane/bridge` `draw_machine_action_button 88` 5 icons; `dinosaurs/mammoth/cave/fossils` `draw_history_action_button 88` 4 icons; `rain/ocean/tree/rainbow` + `sun…neptune` `draw_entry_action_button 88` 14 icons + `decorate_planet`; `jupiter` bands 8 + shadow, `octopus` sway+sucker highlight, `bee` shadow+sway+pollen glow, `penguin` feather shadow, `mars` shadow+limb.

**Verification:**
- `PYTHONPATH=src python3 -m unittest discover -s tests -p "test_encyclopedia*.py"` — `61 OK`
- `discover -s tests` — `1494 OK`
- Headless `1024×600` captures: `/tmp/space_tranche2.png`, `/tmp/volcano_tranche3.png`, `/tmp/pyramids_tranche4.png`, `/tmp/gears_tranche5.png`, `/tmp/body_heart.png`, `/tmp/animals_t7.png`, `/tmp/history_*_hist.png`, `/tmp/*_polish.png`, etc.

**Next:** factual-entry expansion under new standard; art polish may continue incrementally as `NEEDS POLISH` triage. Plan retained as historical evidence.

---

# 14. Correction checkpoint — 2026-08-30 (faa46ec4 review)

**Review commit:** `faa46ec4369adaddf2e720d7bedf54319b3f857f`
**Disposition:** IMPLEMENTED, NOT ACCEPTED / CORRECTION PASS REQUIRED

**Findings carried into correction:**
- faa46ec4 implementation landed with 44 files, ~4943 insertions, 1494 tests green locally
- architecture review found shared-presentation monolith (~1095 lines added to enciclopedia_presentation.py) and per-frame alpha-surface churn
- focus treatment still generic ellipse on many targets, double focus on pyramids
- spoken-name audio hooks added but no locale audio assets integrated (locales/it.json audio: {})
- behavioral tests insufficient for new toys (no Space/VOLCANO/Pyramids/Gears coverage)
- Earth art improved only superficially (tiny 8px ellipses)
- owner runtime Simulator acceptance pending

**Correction scope per instructions:**
- split presentation monolith into focus/controls/toy/planet modules
- fix FocusSpec circle/rounded_rect contract, remove generic ellipse
- bound per-frame allocations via direct draw or cached surfaces, add allocation test
- fix selected-action semantics (action must act on selection or be explicit independent toy)
- implement real Solar System focus-name cues via tools/greia_voice.py (both locales) + dedupe
- improve Earth to authored build-time sprite + selected scale-up
- add interaction regression tests (Space, Volcano, Pyramids, Gears, focus, audio)
- bounded Simulator evidence for 9 pages (Home, Space, space.earth, earth.volcano, history.pyramids, machines.gears, body.heart, body.lungs, animals.lion)

**New status after correction implementation:** `IMPLEMENTED / OWNER RUNTIME REVIEW PENDING` — owner decides final acceptance after Simulator evidence.


