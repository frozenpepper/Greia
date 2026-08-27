# Greia Encyclopedia — unified voice recording requests

**Authority:** this is the single coordination file for encyclopedia-specific prerecorded speech.  
**Created:** 2026-08-27  
**Initial locales:** Italian (`it`) and English (`en`)  
**Runtime rule:** the Greia child device does not synthesize these lines. Final accepted audio is packaged as static page assets.

---

## 1. Local recording agent instructions

Before recording anything, read:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Process only rows whose `STATUS` is `REQUESTED`.

For Lilli, Leo, Flash, Tito and Momo:

- use the exact canonical `VOICE_ID` listed in the row;
- use Chatterbox Multilingual V3 through the existing Greia production environment;
- verify the canonical reference hash through the Greia canonical voice manifest;
- pass the correct language code (`it` or `en`);
- load the model once for a batch;
- do not run concurrent inference workers;
- skip already-produced valid clips;
- call MLX cache clearing + Python GC after every generated clip;
- review a WAV master first;
- reject wrong words, invented words/sounds, clipping, bad stress, voice drift or tail hallucinations;
- convert only the accepted take to the final OGG asset;
- do not ship model weights, venvs, caches or reference masters.

For Dani:

- use `greia.dani.system-v1`;
- use the accepted deterministic/native system-TTS production path on the parent/development machine;
- create a static packaged file;
- do not run child-device TTS.

For pronunciation-critical pedagogical speech:

- use the deterministic/system production path, not a cloned mascot voice;
- human-review the pronunciation.

### Final format

Unless a newer Greia production authority explicitly overrides it:

```text
container: OGG/Vorbis
channels: mono
target sample rate: 22050 Hz where the current Greia production path already emits/converts to that standard
```

Do not normalize or aggressively process a take merely to make a bad generation pass.

### Status ownership

The recording agent may change only:

```text
STATUS
RECORDER_NOTES
```

and may add the requested audio files.

Do not change semantic IDs, texts, speakers, voice IDs or target paths. If a request appears wrong, mark it `BLOCKED` with a note instead of improvising a correction.

After producing a technically good take, set:

```text
RECORDED_UNREVIEWED
```

Only the owner/human listening gate sets:

```text
OWNER_ACCEPTED
```

A rejected take becomes:

```text
REJECTED_REDO
```

### Concurrency rule with ChatGPT work

Once a row is `RECORDED_UNREVIEWED` or later, future encyclopedia implementation must not edit its wording in place.

If wording needs to change:
- create a new cue revision/row;
- use a new output filename;
- mark old row `SUPERSEDED`.

---

## 2. Status vocabulary

```text
PLANNED
REQUESTED
RECORDED_UNREVIEWED
OWNER_ACCEPTED
REJECTED_REDO
SUPERSEDED
BLOCKED
```

---

## 3. Requested batch E0-NAV-01

These are navigation/orientation lines only. They intentionally avoid scientific factual claims, so recording can start before individual entry research is complete.

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.home.welcome` | character_dialogue | Leo | `greia.leo.v1` | it | Benvenuto! Qui ci sono tante cose da scoprire. Scegli un mondo e tocca quello che ti incuriosisce! | `welcome-leo.ogg` | `encyclopedia/pages/home/assets/audio/it/welcome-leo.ogg` | |
| REQUESTED | `encyclopedia.home.welcome` | character_dialogue | Leo | `greia.leo.v1` | en | Welcome! There are so many things to discover here. Choose a world and touch whatever makes you curious! | `welcome-leo.ogg` | `encyclopedia/pages/home/assets/audio/en/welcome-leo.ogg` | |
| REQUESTED | `encyclopedia.animals.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Andiamo a conoscere gli animali! Tocca quello che vuoi osservare più da vicino. | `section-intro-tito.ogg` | `encyclopedia/pages/animals/assets/audio/it/section-intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Let's meet the animals! Touch the one you want to look at more closely. | `section-intro-tito.ogg` | `encyclopedia/pages/animals/assets/audio/en/section-intro-tito.ogg` | |
| REQUESTED | `encyclopedia.space.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Guarda lassù! Esploriamo lo spazio. Tocca il Sole, un pianeta o la Luna per avvicinarti. | `section-intro-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/section-intro-leo.ogg` | |
| REQUESTED | `encyclopedia.space.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Look up there! Let's explore space. Touch the Sun, a planet, or the Moon to move closer. | `section-intro-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/section-intro-leo.ogg` | |
| REQUESTED | `encyclopedia.earth.intro` | character_dialogue | Tito | `greia.tito.v1` | it | La Terra è piena di cose da osservare! Tocca il cielo, l'acqua, una pianta o una roccia e vediamo cosa succede. | `section-intro-tito.ogg` | `encyclopedia/pages/earth/assets/audio/it/section-intro-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Earth is full of things to explore! Touch the sky, the water, a plant, or a rock and let's see what happens. | `section-intro-tito.ogg` | `encyclopedia/pages/earth/assets/audio/en/section-intro-tito.ogg` | |
| REQUESTED | `encyclopedia.body.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | Il tuo corpo fa tantissime cose! Tocca una parte e scopriamo insieme come funziona. | `section-intro-lilli.ogg` | `encyclopedia/pages/body/assets/audio/it/section-intro-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Your body does so many things! Touch a part and let's discover how it works. | `section-intro-lilli.ogg` | `encyclopedia/pages/body/assets/audio/en/section-intro-lilli.ogg` | |
| REQUESTED | `encyclopedia.machines.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Officina pronta! Tocca una macchina o un esperimento e scopriamo cosa la fa funzionare. | `section-intro-dani.ogg` | `encyclopedia/pages/machines/assets/audio/it/section-intro-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Workshop ready! Touch a machine or an experiment and let's discover what makes it work. | `section-intro-dani.ogg` | `encyclopedia/pages/machines/assets/audio/en/section-intro-dani.ogg` | |
| REQUESTED | `encyclopedia.history.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Facciamo un viaggio nel passato! Tocca una scena e andiamo a vedere com'era tanto tempo fa. | `section-intro-leo.ogg` | `encyclopedia/pages/history/assets/audio/it/section-intro-leo.ogg` | |
| REQUESTED | `encyclopedia.history.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Let's take a journey into the past! Touch a scene and we'll see what it was like long ago. | `section-intro-leo.ogg` | `encyclopedia/pages/history/assets/audio/en/section-intro-leo.ogg` | |

---

## 4. Requested batch E3-OCTOPUS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/octopus.md
```

The exact child-facing narration below is intentionally short and maps one-to-one to the four visible discovery interactions on `animals.octopus`.

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.octopus.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Guarda che polpo! Ha otto braccia morbide, piene di ventose. Tocca il polpo e scopri i suoi trucchi! | `intro-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Look at this octopus! It has eight soft arms covered in suckers. Touch it and discover its tricks! | `intro-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.arms` | character_dialogue | Tito | `greia.tito.v1` | it | Un polpo ha otto braccia, non tentacoli. Le ventose lungo le braccia lo aiutano a toccare e afferrare. | `arms-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/arms-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.arms` | character_dialogue | Tito | `greia.tito.v1` | en | An octopus has eight arms, not tentacles. Suckers along its arms help it touch and hold things. | `arms-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/arms-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.camouflage` | character_dialogue | Tito | `greia.tito.v1` | it | Molti polpi possono cambiare molto in fretta il colore e il disegno della pelle. Così possono confondersi con quello che hanno intorno. | `camouflage-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/camouflage-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.camouflage` | character_dialogue | Tito | `greia.tito.v1` | en | Many octopuses can change the color and pattern of their skin very quickly. That helps them blend into their surroundings. | `camouflage-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/camouflage-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.ink` | character_dialogue | Tito | `greia.tito.v1` | it | Se c'è pericolo, molti polpi possono spruzzare una nuvola d'inchiostro e scappare mentre il predatore è confuso. | `ink-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/ink-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.ink` | character_dialogue | Tito | `greia.tito.v1` | en | When danger comes, many octopuses can release a cloud of ink and escape while the predator is confused. | `ink-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/ink-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.hearts` | character_dialogue | Tito | `greia.tito.v1` | it | Sorpresa: un polpo ha tre cuori! Due spingono il sangue verso le branchie e uno lo manda nel resto del corpo. | `hearts-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/hearts-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.octopus.hearts` | character_dialogue | Tito | `greia.tito.v1` | en | Surprise: an octopus has three hearts! Two send blood to the gills, and one sends it around the rest of the body. | `hearts-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/hearts-tito.ogg` | |

---

## 5. Pending future batches

Do **not** record these yet.

Future batches are appended only after page research and wording are ready:

```text
E2-SECTION-*     additional section-page interaction cues if needed
E3-SATURN-*      space.saturn
E3-VOLCANO-*     earth.volcano
E3-HEART-*       body.heart
E3-GEARS-*       machines.gears
E3-FOSSILS-*     history.fossils
...
```

A future factual batch is not `REQUESTED` until its research provenance exists.
