# Greia Activity Catalogue Strategy for Ages 3–5

**Status:** Product/curriculum strategy reference  
**Scope:** First-party Greia Activities for children approximately ages 3–5  
**Purpose:** Preserve the catalogue audit, developmental-learning research, missing curriculum areas, gameplay gaps, difficulty strategy, and proposed additions discussed during the September 2026 catalogue review.

This document is intentionally **not** an implementation plan and does not declare the current Activities production-ready. Visual quality, technical quality, individual gameplay quality, and per-Activity keep/fix/replace decisions require a separate review.

## Related Greia documents

- [ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md](./ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md)
- [CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md](./CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md)
- [ACTIVITY_INPUT_STANDARDS.md](./ACTIVITY_INPUT_STANDARDS.md)
- [ACTIVITY_SYSTEM_NAVIGATION.md](./ACTIVITY_SYSTEM_NAVIGATION.md)
- [PHASE0_CORE_CREATION_ACTIVITIES.md](./PHASE0_CORE_CREATION_ACTIVITIES.md)

---

## 1. Executive summary

Greia already has **enough raw first-party Activity count for a serious launch catalogue**. The current problem is not primarily that there are too few Activities. It is that the catalogue is uneven in:

- subject coverage;
- gameplay variety;
- challenge/difficulty progression;
- differentiation between similar Activities;
- metadata calibration;
- discoverability;
- and, separately, actual quality/polish.

At the time of this review, the repository contains **41 built-ins**:

- **40 child-content Activities**
- **1 My Greia/settings Activity**

The existing catalogue is strong in early numeracy, basic literacy, nature-themed exploration, creative/storytelling activities, and low-pressure play. It is much weaker in:

- executive-function games;
- sorting/classification/patterns;
- vocabulary and listening comprehension;
- sequencing and temporal reasoning;
- social problem solving;
- experimental/scientific reasoning;
- music/rhythm depth;
- true action games;
- adversarial/strategic games;
- meaningful failure/mastery loops;
- higher challenge appropriate to capable 4–5-year-olds.

The recommended product direction is therefore:

1. **Curate and improve the existing catalogue before simply increasing its size.**
2. Use two parallel taxonomies:
   - child-facing navigation: **Create / Play / Learn / Explore**;
   - portfolio planning: **Math / Literacy / Science / Logic & Spatial / Creative / Social & Care / Music / Action**.
3. Plan challenge in broad bands rather than trying to fill difficulty 1–10 uniformly:
   - **Foundation:** difficulty 1–2
   - **Developing:** difficulty 3–4
   - **Stretch:** difficulty 5–6
   - **7–10:** reserved for genuinely more demanding future content.
4. Aim for approximately:
   - **24–28 polished content Activities** as a credible minimum public-release catalogue;
   - **32–36 polished content Activities** as a strong/ideal first-party launch catalogue.
5. Prefer a smaller set of excellent Activities with distinct purposes over many overlapping counting, matching, or phonics games.
6. Add a small but strong set of real games that involve timing, planning, mastery, and recoverable failure.
7. Preserve Greia's core philosophy that users can create and add their own Activities; the first-party catalogue does not need to be exhaustive.

---

## 2. Current first-party catalogue snapshot

### 2.1 Launcher collection memberships

Memberships overlap, because the launcher collections describe how a child may approach an Activity rather than a mutually exclusive portfolio classification.

| Launcher collection | Current membership count |
|---|---:|
| Play | 28 |
| Learn | 26 |
| Create | 14 |
| Explore | 13 |
| My Greia | 1 |

These counts should **not** be mechanically equalized.

### 2.2 Primary portfolio families

For catalogue planning, the current Activities were manually classified by their dominant experience:

| Portfolio family | Approximate count |
|---|---:|
| Math & numeracy | 8 |
| Nature & science | 7 |
| Logic / spatial / physics | 7 |
| Creative arts / storytelling | 7 |
| Language / literacy | 5 |
| Care / social-emotional | 4 |
| Music / rhythm | 1 |
| Action / motor | 1 |
| System / personalization | 1 |

The clearest numerical gaps are therefore **Music/Rhythm** and **Action/Motor**.

However, raw family counts alone are insufficient. Some apparently well-populated families still lack important developmental concepts or higher-difficulty experiences.

### 2.3 Nominal difficulty distribution

| Nominal difficulty | Current Activity count |
|---|---:|
| 1 | 15 |
| 2 | 16 |
| 3 | 9 |
| 4 | 1 |
| 5–10 | 0 |

Eleven Activities declare adaptive ranges, with some reaching difficulty 5–6. Therefore the nominal distribution understates the maximum challenge somewhat, but the catalogue remains strongly bottom-heavy.

Approximate family distribution:

- **Nature/science:** five at difficulty 1, two at difficulty 2.
- **Language/literacy:** two at difficulty 1, one at difficulty 2, two at difficulty 3.
- **Math:** two at difficulty 1, three at difficulty 2, three at difficulty 3.
- **Care/social:** two at difficulty 1, two at difficulty 2.
- **Logic/spatial:** one at difficulty 1, three at difficulty 2, two at difficulty 3, one at difficulty 4.
- **Creative:** two at difficulty 1, four at difficulty 2, one at difficulty 3.
- **Music:** one at difficulty 2.
- **Action:** one at difficulty 3.

**Logic/spatial/physics currently has the healthiest internal progression.**

### 2.4 Recommended minimum-age distribution

| Minimum recommended age | Current Activity count |
|---|---:|
| 2 | 2 |
| 3 | 19 |
| 4 | 11 |
| 5 | 9 |

No current first-party Activity begins above age 5.

Thirteen Activities omit a maximum recommended age, which is legitimate for genuinely open-ended creative, sensory, imaginative, or otherwise non-expiring experiences.

Approximate number of Activities passing the current `recommended_only` age range:

| Child age | Approximate eligible Activities |
|---|---:|
| 2 | 2 |
| 3 | 21 |
| 4 | 32 |
| 5 | 39 |
| 6 | 38 |
| 7 | 36 |
| 8 | 24 |
| 9 | 17 |
| 10 | 15 |

By age 5, almost the entire catalogue is considered age-appropriate. This makes **curation, grouping, metadata accuracy, and challenge differentiation** especially important.

A product decision remains necessary: is Greia truly intended to offer a substantial age-2 experience, or is it fundamentally a **3+ platform with a few 2+ Activities**? If age 2 is a real product promise, more genuinely toddler-appropriate content is needed; existing age ranges should not simply be lowered.

---

## 3. Do not confuse launcher taxonomy with curriculum taxonomy

Greia benefits from keeping two views of the catalogue.

### Child-facing/navigation view

Platform-owned launcher collections:

- Create
- Play
- Learn
- Explore
- My Greia

These describe child intent and can overlap.

### Portfolio-planning view

For internal curation:

- Math & numeracy
- Language & literacy
- Nature & science
- Logic / spatial / physics
- Creative arts / storytelling
- Care / social-emotional
- Music / rhythm
- Action / motor

These describe what the catalogue is actually teaching or exercising.

Do **not** force the two systems into a single mutually exclusive taxonomy. Existing educational categories and discovery tags should support portfolio analysis without creating a competing runtime classification system.

---

## 4. Current discovery/grouping problem

The launcher already supports adaptive grouping, but the real catalogue currently fails to produce a clean subdivision for the largest root collections.

At the time of review:

- Create: 14 Activities, no valid full subdivision.
- Play: 28 Activities, no valid full subdivision.
- Learn: 26 Activities, no valid full subdivision.
- Explore: 13 Activities, no valid full subdivision.

The planner correctly refuses a misleading partial grouping when selected discovery tags do not cover every Activity.

Examples include:

- Play having strong tags such as puzzles, nature, care, numbers, and words while other music/story/action/making Activities remain unassigned;
- Create containing memberships that may not represent genuine creation, making clean sub-grouping harder.

Before substantially enlarging the catalogue, Greia should eventually:

1. recalibrate Activity discovery tags;
2. correct questionable launcher memberships;
3. ensure adaptive grouping can actually divide large real collections;
4. avoid inventing tags solely to satisfy a grouping algorithm.

---

## 5. Important learning areas for ages 3–5 that are currently missing or weak

Preschool development is much broader than letters and counting. Major early-childhood frameworks treat language/literacy, mathematics, scientific reasoning, social-emotional development, approaches to learning/executive function, and perceptual/motor development as interconnected domains.

Greia currently covers parts of many of these, but several high-value areas deserve stronger first-party treatment.

### 5.1 Patterns, sorting, classification, and comparison — very high priority

Important concepts include:

- same / different;
- grouping by color, shape, size, function, habitat, or other properties;
- finding the object that does not belong;
- ordering small → medium → large;
- AB, AAB, ABB, ABC and later pattern recognition;
- switching the sorting rule;
- comparison by attribute.

This is foundational preschool mathematics and reasoning, not merely an extension of counting.

Greia touches some components indirectly, but lacks a strong systematic Activity built around **classification and pattern discovery**.

Possible concept:

**Momo's Sorting Workshop / Magic Sorting Train**

Progression:

- age 3: obvious color/shape sorting;
- age 4: two attributes and simple patterns;
- age 5: changing rules, exceptions, and more complex patterns.

This can naturally span difficulty 1–4.

### 5.2 Executive function: attention, inhibition, working memory, rule switching — very high priority

A major gap is play that explicitly requires the child to:

- remember a short rule;
- sustain attention;
- resist an immediate but incorrect response;
- change rules when instructed;
- persist after an error.

Possible concept:

**Momo Says / Stop-Go**

Examples:

- feed the creature only when fruit appears;
- do not act when the forbidden object appears;
- touch the moon when the game says "day";
- later switch the rule;
- remember two sequential instructions.

This creates a genuine game loop while exercising executive control.

### 5.3 Sequencing, temporal order, and causal order — high priority

Important concepts:

- first / next / last;
- before / after;
- cause → effect;
- routine ordering;
- predicting what comes next.

Examples:

- dirty hands → soap → rinse → towel;
- seed → sprout → flower;
- wake → breakfast → dress → leave;
- story images placed in chronological order.

This skill connects language comprehension, mathematics, routines, planning, and storytelling.

Possible concept:

**What Happens Next?**

The same Activity can scale from concrete three-step routines for age 3 to causal story sequencing for age 5.

### 5.4 Vocabulary and spoken-language comprehension — high priority

Greia's literacy catalogue currently emphasizes mechanics such as:

- letters;
- phonics;
- syllables;
- rhymes;
- word building.

A complementary need is simply **understanding and using language well**.

Useful targets include:

- nouns;
- verbs;
- adjectives;
- categories;
- object function;
- descriptive language;
- who / what / where / why questions;
- spatial terms such as inside, behind, between, beside;
- richer topic vocabulary.

Possible concept:

**Word Explorer**

This could use Greia's voice-first child interaction naturally and may be more valuable to a three-year-old than adding another alphabet Activity.

### 5.5 Story comprehension, not only story creation — high priority

Greia already has several storytelling/creative Activities. A distinct skill is listening to a short story and understanding:

- who did what;
- where something happened;
- what happened first;
- why something happened;
- what may happen next.

A single scalable Activity can combine:

- listening;
- vocabulary;
- memory;
- sequencing;
- causal reasoning;
- prediction.

### 5.6 Social problem solving — high priority

Greia has emotion recognition and caregiving content, but identifying "happy/sad/angry" is only one layer of social-emotional development.

Useful situations for ages 4–5 include:

- two characters want the same toy;
- waiting for a turn;
- asking for help;
- sharing;
- apologizing;
- distinguishing accident from intention;
- recognizing another character's perspective;
- coping with frustration;
- choosing a calming strategy;
- solving a small conflict.

Possible concept:

**Friends of Greia**

The objective is not to moralize at the child but to present understandable social situations and let the child reason through constructive responses.

### 5.7 Scientific prediction and experimentation — high priority, especially ages 4–5

The current science/nature catalogue is largely observational.

Greia should add more:

> predict → try → observe → revise

Possible experiments:

- what floats or sinks;
- which object rolls farther;
- how ramp angle affects a ball;
- which material absorbs water;
- what melts;
- how a shadow changes;
- what plants need;
- color mixing;
- simple magnetism.

Possible concept:

**Little Laboratory**

This should ideally be one expandable Activity with multiple experiment modules rather than many tiny single-concept science Activities.

### 5.8 Positional and spatial language — medium-high priority

Useful concepts:

- above / below;
- inside / outside;
- behind / in front;
- beside;
- between;
- near / far;
- around / through;
- first / last;
- left / right when developmentally appropriate.

Possible interaction:

> Put Flash behind the tree.  
> Put Lola between the two rocks.

This joins language comprehension with spatial reasoning.

### 5.9 Quantity concepts beyond counting — medium-high priority

Preschool mathematics should not collapse into numeral recognition and counting.

Useful concepts include:

- more / less;
- equal;
- none / some / all;
- bigger / smaller;
- longer / shorter;
- heavier / lighter;
- full / empty;
- part / whole;
- small-set estimation;
- comparing quantities.

Greia already covers parts of these. During catalogue curation, retain these differentiated concepts instead of preserving several Activities whose main loop is simply "count the objects."

### 5.10 Time and everyday routines — medium priority

Useful concepts:

- morning / afternoon / night;
- today / tomorrow / yesterday;
- before / after;
- recurring daily routines;
- days and seasons as cycles.

This may not require its own Activity if sequencing and existing seasons content cover it well.

**2026-10-08 cross-product clarification:** This narrow curriculum assessment
does **not** cover time as an everyday Greia computing utility. A child's real
clock, stopwatch and visual timer belong to a stronger *Time & Days* product
experience; a personal calendar can connect tomorrow and yesterday to
meaningful family events. The new **SOURCE-ONLY** Activity prototype lives
outside built-in release at `activity_incubator/tempo_di_greia/`. The exact
product proposal, permission/time-validity rules, pending bilingual audio,
calendar and background timer boundaries are in
[`CHILD_TIME_AND_ROUTINES.md`](./CHILD_TIME_AND_ROUTINES.md).
This addendum does not claim spoken/title audio, runtime/SIMULATOR review,
calendar production or release readiness.

### 5.11 Body, senses, health, and independence — medium priority

Possible topics:

- body parts;
- senses;
- washing hands;
- brushing teeth;
- healthy routines;
- dressing;
- sleep;
- recognizing when adult help is needed;
- basic household safety.

Greia should avoid pretending a screen can replace real-world skill practice. A body/senses Activity can nevertheless be useful and highly playable.

### 5.12 Physical development: support it, do not simulate it

Gross-motor skills are important, but many are better learned away from the screen:

- jumping;
- balancing;
- throwing/catching;
- dressing;
- manipulating real objects.

A Greia Activity can instead **prompt real movement**, for example through rhythm, dance, imitation, freeze/go, or action songs.

This strengthens the case for expanding the weak Music/Rhythm family.

---

## 6. Six high-value educational additions

If Greia added only six curriculum-oriented Activities, the strongest current set would be:

| Candidate | Core learning | Target age |
|---|---|---|
| Sorting & Patterns | classification, comparison, patterns, rule changes | 3–5 |
| Momo Says / Stop-Go | attention, inhibition, working memory, executive function | 3–5 |
| What Happens Next? | sequencing, temporal order, causal reasoning | 3–5 |
| Word Explorer | vocabulary, verbs, categories, positional language | 3–5 |
| Little Laboratory | prediction, experiments, cause/effect, scientific reasoning | 4–5+ |
| Friends of Greia | turn-taking, feelings, conflict solving, perspective-taking | 4–5 |

In addition, Greia should either substantially strengthen **Orchestra Animali** or add another strong music/rhythm Activity.

These additions would broaden Greia from a catalogue that can appear dominated by:

> letters + phonics + counting + cute educational games

toward:

> language + mathematics + reasoning + executive function + science + social-emotional development + creativity + play.

Not every learning goal requires a separate narrow Activity. Combining related concepts can keep the catalogue coherent:

- sorting + rule switching;
- vocabulary + positional language;
- sequencing + story comprehension;
- rhythm + real-world movement.

---

## 7. Real games, mastery, and recoverable failure

A separate catalogue gap is the lack of **real games** in which a child can meaningfully improve.

Greia needs a small number of experiences where children learn:

- timing;
- prediction;
- route planning;
- spatial planning;
- impulse control;
- strategic thinking;
- persistence;
- recovering from mistakes;
- mastery through replay.

This does **not** require punitive game-over design.

### Preschool-friendly failure principle

At low difficulties:

> mistake → funny consequence → immediate retry

rather than:

> mistake → harsh failure screen → restart from title

Examples:

- a car tumbles down a hill comically and is reset;
- the dragon hits a tree, leaves explode, one heart disappears, play continues;
- a creature is caught, briefly reacts, then restarts at the nearest safe point.

At higher difficulties, genuine finite-life or game-over conditions can appear.

This allows Greia to teach persistence without making every Activity impossible to lose.

---

## 8. Proposed action/strategy game family

The proposed games are valuable because they exercise **different forms of thinking** rather than merely reskinning the same mechanic.

### 8.1 Cute maze-chase game

Inspired by the broad maze-chase arcade archetype, but with original Greia characters, level design, visual identity, sounds, and mechanics.

Possible fiction:

- collect berries, stars, acorns, or magical objects;
- one or more cute creatures patrol or pursue;
- temporary power objects reverse the risk.

Skills:

- directional control;
- spatial mapping;
- route planning;
- anticipating opponents;
- inhibition;
- reaction;
- risk/reward decisions.

Possible progression:

- **D1:** no enemies, collect objects.
- **D2:** one extremely slow enemy with frequent pauses.
- **D3:** one real pursuer.
- **D4:** two enemies with distinct simple behaviours.
- **D5:** more complex maze, multiple pursuers, power objects.
- **D6:** genuinely challenging child-friendly play.

This single Activity can span almost the whole useful Greia action ladder.

### 8.2 Hill-climb vehicle physics game

A small cute vehicle must cross hills, bumps, jumps, and obstacles. The child learns when and how much to accelerate or brake based on terrain, momentum, vehicle orientation, and landing.

The useful property is direct visible causality:

> apply force → accelerate/rotate → terrain changes motion → landing succeeds or fails

Skills:

- timing;
- prediction;
- intuitive force/momentum understanding;
- motor control;
- risk management.

Possible progression:

- **Age 3 / D1:** one GO control, forgiving terrain, no permanent failure.
- **Age 4 / D2–3:** throttle timing matters, larger slopes/jumps, optional brake.
- **Age 5 / D4–6:** momentum management, mid-air balance, obstacles, optional routes, challenge goals.

Comical rolling/crashing should be part of the appeal rather than a punishment.

This is especially attractive because it combines a genuinely fun game with intuitive physical reasoning.

### 8.3 Falling-shapes / Tetris-like spatial game

Do not begin with full classic Tetris rules for a three-year-old.

Progression:

#### Age 3
- pieces do not fall;
- child places shapes into forgiving spaces;
- near-correct pieces can snap into position;
- rotation can be automatic.

#### Age 4
- pieces descend slowly;
- child moves them horizontally;
- gaps reduce available space but are not heavily punished.

#### Age 5
- rotation appears;
- more complex shapes;
- complete rows disappear;
- speed gradually increases.

Skills:

- spatial composition;
- planning;
- geometry;
- mental rotation;
- prediction.

A Greia-specific design should have its own visual language and presentation rather than simply copying an existing commercial game.

### 8.4 Connect Three → Connect Four strategy game

For the lower end, begin with **Connect Three**, not immediately the full strategy requirements of classic Connect Four.

Progression:

- **D1:** make three in a row with no opponent.
- **D2:** play against a deliberately weak/silly opponent.
- **D3:** opponent begins blocking.
- **D4:** transition to Connect Four / larger vertical board.
- **D5+:** increasingly competent CPU.

Strong reasons to include it:

- turn-taking;
- planning;
- anticipating another player's move;
- simple adversarial reasoning;
- no twitch/reflex requirement.

It is also an excellent candidate for **same-computer two-player support**.

### 8.5 Upgrade Volo del Draghetto rather than discard it

The existing relaxed, impossible-to-lose flight can remain valuable as an introductory mode. The weakness is when that is the entire experience.

Recommended progression:

#### Relaxed Flight
- effectively impossible to lose;
- collect stars;
- exploratory and welcoming.

#### Adventure
- obstacles cost hearts;
- several hearts;
- frequent checkpoints;
- fast retry.

#### Challenge
- moving obstacles;
- narrower gaps;
- moving collectibles;
- faster scrolling;
- score/combo systems.

#### Expert
- genuinely demanding authored or procedural courses.

This would turn an existing Activity into a complete **reaction/fine-control** game spanning approximately difficulty 1–6.

### 8.6 Frogger-like timing/crossing game — optional future candidate

Use an original safe/cute setting rather than traffic:

- frog crossing streams;
- lily pads;
- moving logs;
- turtles;
- butterflies;
- moving platforms.

The key skill is deciding:

> I can move now, but should I wait?

This creates a strong inhibitory-control/timing game.

### 8.7 Breakout/Arkanoid-like trajectory game — optional future candidate

A simple horizontal paddle game can scale naturally:

- age 3: enormous forgiving paddle;
- later: smaller paddle, different surfaces, multiple balls, increasingly meaningful angles.

Skills:

- anticipation;
- trajectory;
- fine control;
- cause/effect.

### 8.8 Local cooperative game — desirable future direction

Greia should eventually include at least one game in which **two children cooperate on the same computer**.

Examples:

- each controls one character and both must reach switches;
- one controls movement while the other activates tools;
- complementary abilities are needed to progress.

This adds a type of social play almost absent from the current first-party catalogue.

---

## 9. Recommended core gameplay archetypes

A compact, differentiated first-party game library could deliberately cover:

| Activity/archetype | Primary challenge | Secondary value | Useful range |
|---|---|---|---:|
| Volo del Draghetto | reaction + fine control | attention | D1–D6 |
| Maze Chase | navigation + pursuit | planning, inhibition | D1–D6 |
| Hill Vehicle | timing + momentum | intuitive physics | D1–D6 |
| Falling Shapes | spatial placement | planning, geometry | D2–D6 |
| Connect 3/4 | strategic planning | turn-taking, prediction | D2–D6 |

These are intentionally different:

- Dragon: **react**
- Vehicle: **feel and predict physics**
- Maze: **navigate and evade**
- Shapes: **plan spatially**
- Connect: **anticipate another player's move**

This is enough to give Greia a credible real-game layer without turning the catalogue into a collection of arcade clones.

---

## 10. Filling the higher-difficulty gap

For ages 3–5, Greia should not attempt to manufacture difficulty-10 preschool content simply to fill a numeric scale.

A strong D4–D6 launch layer could be formed by:

1. **Costruiamo Ponti** — engineering/problem solving.
2. **Labirinto Magico** at harder adaptive levels — spatial puzzles.
3. **Maze Chase** — real-time planning/action.
4. **Hill Vehicle** — physics/timing.
5. **Falling Shapes** — spatial planning.
6. **Connect 3/4** — adversarial strategy.
7. **Volo del Draghetto**, upgraded to support real challenge modes.

That is sufficient to let a capable five-year-old encounter Activities that remain genuinely challenging after months of use.

The desired child reaction is:

> "This is hard. I want to try again."

not merely:

> "The game always lets me succeed."

---

## 11. Catalogue size and balance targets

These are planning targets, not rigid quotas.

| Portfolio family | Suggested polished first-party target |
|---|---:|
| Math & numeracy | 4–5 |
| Language & literacy | 4–5 |
| Nature & science | 4–5 |
| Logic / spatial / physics | 4–5 |
| Creative arts / storytelling | 5–6 |
| Care / social-emotional | 3–4 |
| Music / rhythm | ~3 |
| Action / motor / real games | ~3+ |

Because individual Activities can legitimately span multiple purposes, these figures are **portfolio guidance**, not a requirement that every Activity receive one exclusive category.

### Minimum credible release

Approximately **24–28 excellent child-content Activities**, plus My Greia/system surfaces.

### Strong first-party launch

Approximately **32–36 polished child-content Activities**.

A public Greia release with 26 excellent, distinct Activities is preferable to one with 40 mediocre or substantially overlapping Activities.

Greia explicitly encourages people to build and add their own Activities, so the first-party set should model quality, breadth, and good design rather than attempt to contain every possible children's game.

---

## 12. Areas where new Activities should *not* be added blindly

### Early numeracy

Review overlap before adding more.

Current cluster includes:

- Bosco Numeri
- Il Giardino dei Numeri
- Luci di Momo
- Treno Numeri
- plus more advanced math Activities

Do not remove them based on names or manifests alone; inspect actual gameplay loops and unique value first. However, avoid adding more generic counting Activities until this cluster is curated.

### Literacy

The literacy family may represent a legitimate developmental progression rather than redundancy:

> alphabet → rhyme → syllables → phoneme/word building → words

Again, actual implementation should determine what stays.

### Nature/science

There is plenty of nature-themed content numerically. The need is **deeper scientific interaction and higher challenge**, not simply more animals/plants/seasons.

### Creative content

Painting and Writing are explicit Phase-0 first-party anchors and should not be casually removed during curation.

---

## 13. Metadata calibration work identified by the audit

A later catalogue pass should review:

- whether difficulty numbers have a consistent meaning across different domains;
- whether `recommended_age_min` and `recommended_age_max` are truthful;
- whether adaptive difficulty ranges are genuinely implemented;
- whether baseline difficulty sits properly inside those ranges;
- whether launcher collections reflect actual child intent;
- whether discovery tags support real launcher subdivision.

Specific examples that deserve inspection:

- **Sillabe Magiche** is nominal difficulty 1 despite age-5+ literacy material while related Activities are higher.
- **Acquario Magico** appears in Create even though its loop may be more accurately Explore/cause-and-effect.
- **Sottomarino Giramondo** may similarly have a questionable Create membership.

These are audit leads, not final decisions.

---

## 14. Source tree versus release catalogue

At the time of review, Greia's image-composition path installs the first-party `activities/` tree wholesale and builds the built-in index from the same source.

That effectively makes:

> present in source tree ≈ ships in release image

This should eventually be separated.

Greia needs an explicit release-catalogue/profile mechanism so that:

- experiments can remain in the repository;
- unfinished Activities can be tested without shipping;
- replaced or deprecated Activities can remain available for development/history if appropriate;
- release composition is deliberate and reviewable.

This is especially important while the catalogue is undergoing curation.

---

## 15. Recommended next catalogue-review step

Before implementing wholesale additions or deletions, build a per-Activity curation matrix for all current child-content Activities.

For each Activity record:

- current name/id;
- actual gameplay loop;
- intended age range;
- nominal and adaptive difficulty;
- child-facing launcher collections;
- portfolio family/families;
- learning/developmental value;
- unique value compared with other Activities;
- overlap/redundancy;
- challenge/mastery potential;
- solo/two-player potential where relevant;
- whether metadata appears calibrated;
- later, separately, visual quality;
- later, separately, technical/runtime quality.

Then assign a release-oriented disposition such as:

- **Anchor / keep**
- **Keep but improve**
- **Merge or replace**
- **Do not ship**
- **New Activity needed to fill gap**

The decisions should be made from the actual game, not from manifest names alone.

---

## 16. Research basis and external references

This strategy is informed by the following early-childhood development resources and the Greia repository's own Activity metadata/architecture.

### Head Start / Early Childhood Learning & Knowledge Center

- Head Start Early Learning Outcomes Framework: Ages Birth to Five  
  https://headstart.gov/interactive-head-start-early-learning-outcomes-framework-ages-birth-five
- Approaches to Learning / executive-function practice guidance  
  https://headstart.gov/school-readiness/effective-practice-guides/approaches-learning
- Head Start Approach to School Readiness  
  https://headstart.gov/school-readiness/article/head-start-approach-school-readiness-faqs

### NAEYC

- Mathematics in early childhood / sorting, patterning, measurement and related concepts  
  https://www.naeyc.org/node/1251
- Preparing Young Children for School / vocabulary and broad developmental readiness  
  https://www.naeyc.org/resources/blog/preparing-young-children-school
- Spatial reasoning and design-copying mathematics  
  https://www.naeyc.org/resources/pubs/yc/mar2018/design-copying-mathematics

### CDC developmental milestones

- Milestones by 3 Years  
  https://www.cdc.gov/act-early/milestones/3-years.html
- Milestones by 5 Years  
  https://www.cdc.gov/act-early/milestones/5-years.html

These references should be treated as guidance for age-appropriate design, not as a claim that Greia replaces preschool teaching, physical play, caregivers, teachers, or real-world developmental experiences.

---

## 17. Product principle

The first-party Greia catalogue should not be judged primarily by the question:

> "How many Activities do we ship?"

A better test is:

> "Does a child aged roughly 3–5 encounter a small but rich set of genuinely different things to create, learn, explore, practice, master, and replay — with enough progression that the computer remains interesting as the child develops?"

That means balancing:

- foundational learning;
- creative freedom;
- playful exploration;
- social/emotional understanding;
- scientific curiosity;
- music and movement;
- real games;
- challenge and mastery;
- age-appropriate failure;
- and space for families and creators to add entirely new Activities.

That is the catalogue strategy this review recommends.


---

## Appendix A. Current built-in Activity inventory used for this review

This appendix records the manifest-level inventory that informed the September 2026 analysis. Portfolio family is a planning classification, not a new runtime taxonomy.

| Activity | Launcher collections | Planning family | Difficulty | Recommended age | Adaptive range / note |
|---|---|---|---:|---|---|
| `acquario_magico` | Explore, Create | Nature & science | 1 | 3+ | Non-adaptive; Create membership deserves review |
| `alfabeto_leo` | Learn, Play | Language & literacy | 1 | 2–4 | Adaptive 1–3 |
| `baia_delle_orche` | Play, Explore, Learn | Nature & science | 1 | 3–7 | Marine life, empathy, coordination, rhythm/music |
| `bosco_numeri` | Learn, Play | Math & numeracy | 1 | 3–5 | Counting / fine motor |
| `bottega_delle_misure` | Learn, Explore | Math & numeracy | 3 | 5–7 | Adaptive 1–5; measurement/comparison |
| `casa_del_dieci` | Learn, Play | Math & numeracy | 3 | 5–7 | Adaptive 1–5; number composition/operations |
| `clinica_cuccioli` | Play, Learn | Care / social-emotional | 2 | 3–7 | Empathy, caregiving, hygiene/health |
| `costruiamo_ponti` | Create, Play | Logic / spatial / physics | 4 | 5–10 | Adaptive 2–6; engineering/construction |
| `cucciolo_mio` | Play, Create | Care / social-emotional | 2 | 3–7 | Empathy, routines, creativity |
| `enciclopedia_greia` | Explore, Learn | Nature & science | 1 | 3–8 | Science curiosity / world knowledge |
| `faccine_momo` | Play, Learn | Care / social-emotional | 1 | 3+ | Emotion recognition/social learning |
| `festa_delle_rime` | Learn, Play | Language & literacy | 2 | 4–6 | Adaptive 1–4; rhyme/phonological awareness |
| `foresta_parole` | Learn, Play | Language & literacy | 3 | 5–8 | Phonics / word-oriented literacy |
| `il_giardino_dei_numeri` | Learn, Play | Math & numeracy | 1 | 2–4 | Adaptive 1–3; counting/subitizing |
| `la_discesa_della_biglia` | Play, Learn | Logic / spatial / physics | 2 | 4–7 | Adaptive 1–4; intuitive physics/construction |
| `labirinto_magico` | Play, Explore | Logic / spatial | 3 | 4–10 | Adaptive 1–6; spatial problem solving |
| `luci_di_momo` | Learn, Play | Math & numeracy | 2 | 4–6 | Adaptive 1–4; subitizing/quantity comparison |
| `memory_meraviglie` | Learn, Play | Logic / cognition | 2 | 3–8 | Working memory / visual matching |
| `mondo_contrari` | Play, Learn | Logic / language concepts | 1 | 3+ | Contrasts / early concepts |
| `morbidi_mostriciattoli` | Create, Play | Creative arts | 1 | 3+ | Open-ended making/drawing |
| `nanna_delle_nuvolette` | Play, Explore | Care / calm / early reasoning | 1 | 3+ | Sequencing, cause/effect, matching |
| `nascondino_bosco` | Explore, Play | Logic / observation | 2 | 3–7 | Visual attention / nature vocabulary |
| `officina_dei_suoni` | Learn, Play | Language & literacy | 3 | 5–7 | Adaptive 1–3; phonemic awareness / word building |
| `orchestra_animali` | Play, Learn | Music / rhythm | 2 | 3+ | Only clear dedicated music/rhythm Activity |
| `painting` | Create | Creative arts | 1 | 3+ | Phase-0 first-party anchor |
| `pasticceria_magica` | Learn, Create | Math / creative | 3 | 4–8 | Counting, problem solving, making |
| `piccola_serra` | Explore, Create | Nature & science | 2 | 4–9 | Gardening / nature cycles / cause-effect |
| `posta_di_leo` | Create, Learn | Creative / literacy | 2 | 5+ | Writing / print concepts / expression |
| `quattro_stagioni` | Explore, Play, Learn | Nature & science | 1 | 3+ | Seasons / weather / nature cycles |
| `shape_garden` | Create, Learn | Creative / geometry | 2 | 3+ | Art, geometry, fine motor |
| `sillabe_magiche` | Learn, Play | Language & literacy | 1 | 5–8 | Difficulty calibration deserves review |
| `sottomarino_giramondo` | Create, Explore | Nature & science | 1 | 3–8 | Create membership deserves review |
| `specchi_magici` | Learn, Create | Logic / spatial / geometry | 3 | 5–7 | Adaptive 1–5; symmetry |
| `stelle_incantate` | Explore, Learn | Math / science crossover | 2 | 4–7 | Numbers, counting, shapes, science curiosity |
| `storie_della_mia_voce` | Create, Play | Creative / storytelling | 2 | 4–7 | Narrative sequencing / creativity |
| `teatrino_fiabe` | Create, Play | Creative / storytelling | 2 | 3+ | Storytelling / visual composition |
| `treno_numeri` | Learn, Play | Math & numeracy | 2 | 4–7 | Counting / fine motor |
| `viaggio_delfino` | Play, Explore | Nature / action | 2 | 4–8 | Motor skills / reaction / science curiosity |
| `volo_draghetto` | Play, Explore | Action / motor | 3 | 4–9 | Current challenge/failure model should be expanded |
| `writing` | Create, Learn | Creative / literacy | 3 | 5+ | Phase-0 first-party anchor |
| `workshop_settings` | My Greia | System / personalization | 1 | 3+ | Not child-content catalogue material |

### Appendix A.1 Current clusters that deserve close curation

#### Early numeracy cluster
Potential overlap must be judged from actual gameplay, not names:

- Bosco Numeri
- Il Giardino dei Numeri
- Luci di Momo
- Treno Numeri

More advanced math Activities such as Bottega delle Misure and Casa del Dieci appear more differentiated.

#### Literacy progression
The current sequence may be complementary rather than redundant:

- Alfabeto Leo
- Festa delle Rime
- Sillabe Magiche
- Officina dei Suoni
- Foresta Parole

The curation question is whether the implemented loops actually create a meaningful developmental progression.

#### Existing science/nature cluster
Greia has substantial nature-themed breadth, but much less experimental science and higher challenge. New work should favor **prediction, experimentation, variables, and causal reasoning** over additional passive observation themes.

#### Existing creative anchors
Painting and Writing are explicit Phase-0 Greia anchors. Other creative/storytelling Activities should be assessed relative to the distinct value they add around those anchors.

### Appendix A.2 Known portfolio holes after inventory

The inventory makes the most obvious gaps visible:

- only one clear dedicated Music/Rhythm Activity;
- only one clear dedicated Action/Motor Activity;
- no strong dedicated sorting/patterning progression;
- little explicit executive-function play;
- little general spoken-vocabulary/listening-comprehension practice;
- limited social problem-solving beyond emotion/care recognition;
- science is primarily observational rather than experimental;
- little same-device multiplayer or cooperative play;
- very little true adversarial strategy;
- few Activities with meaningful mastery/failure loops;
- weak nominal D4–D6 coverage.

These gaps are the reason the proposed additions in this document prioritize **different forms of cognition and play**, rather than simply adding more first-party Activities.
