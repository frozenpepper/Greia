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

---

## 4. Requested batch E4-LION-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/lion.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.lion.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Ecco il leone! Guarda la criniera, le zampe forti e il grande ruggito. Tocca i simboli e scopri come vive. | `intro-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Here is the lion! Look at its mane, strong front legs, and mighty roar. Touch the symbols and discover how it lives. | `intro-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.mane` | character_dialogue | Tito | `greia.tito.v1` | it | Molti leoni maschi adulti hanno una grande criniera intorno alla testa e al collo. Colore e grandezza possono cambiare da un leone all'altro. | `mane-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/mane-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.mane` | character_dialogue | Tito | `greia.tito.v1` | en | Many adult male lions have a large mane around the head and neck. Its color and size can vary from one lion to another. | `mane-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/mane-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.pride` | character_dialogue | Tito | `greia.tito.v1` | it | I leoni sono i felini più sociali. Spesso vivono in gruppi chiamati branchi, dove diversi leoni restano in contatto e crescono i piccoli. | `pride-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/pride-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.pride` | character_dialogue | Tito | `greia.tito.v1` | en | Lions are the most social cats. They often live in groups called prides, where several lions stay connected and raise their young. | `pride-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/pride-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.roar` | character_dialogue | Tito | `greia.tito.v1` | it | Il ruggito aiuta i leoni a comunicare e a segnalare il loro territorio. È così potente che può sentirsi da molto lontano. | `roar-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/roar-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.roar` | character_dialogue | Tito | `greia.tito.v1` | en | A roar helps lions communicate and signal their territory. It is so powerful that it can be heard from very far away. | `roar-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/roar-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.forelegs` | character_dialogue | Tito | `greia.tito.v1` | it | Il leone ha zampe anteriori molto forti. Insieme al corpo compatto, lo aiutano a muoversi e ad afferrare con forza. | `forelegs-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/forelegs-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.lion.forelegs` | character_dialogue | Tito | `greia.tito.v1` | en | A lion has very strong front legs. Together with its compact body, they help it move and grip powerfully. | `forelegs-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/forelegs-tito.ogg` |  |

---

## 5. Requested batch E4-ELEPHANT-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/elephant.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.elephant.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Ecco l'elefante! La proboscide è forte e delicata, le grandi orecchie aiutano a rinfrescarsi e il contatto serve anche per comunicare. | `intro-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Here is the elephant! Its trunk is strong and delicate, its large ears help it cool down, and touch is also part of elephant communication. | `intro-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.trunk` | character_dialogue | Tito | `greia.tito.v1` | it | La proboscide unisce naso e labbro superiore. È piena di muscoli e serve per annusare, toccare, prendere il cibo e spostare oggetti. | `trunk-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/trunk-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.trunk` | character_dialogue | Tito | `greia.tito.v1` | en | The trunk combines the nose and upper lip. It is packed with muscles and is used to smell, touch, pick up food, and move objects. | `trunk-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/trunk-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.water` | character_dialogue | Tito | `greia.tito.v1` | it | L'elefante aspira l'acqua nella proboscide e poi la spruzza dentro la bocca per bere. Può usarla anche per fare il bagno. | `water-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/water-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.water` | character_dialogue | Tito | `greia.tito.v1` | en | An elephant draws water into its trunk and then squirts it into its mouth to drink. It can also use the trunk for bathing. | `water-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/water-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.ears` | character_dialogue | Tito | `greia.tito.v1` | it | Le grandi orecchie hanno molti vasi sanguigni. Quando l'elefante le muove, possono aiutarlo a disperdere calore e rinfrescarsi. | `ears-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/ears-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.ears` | character_dialogue | Tito | `greia.tito.v1` | en | Large elephant ears contain many blood vessels. Flapping them can help move heat away and cool the elephant. | `ears-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/ears-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.social` | character_dialogue | Tito | `greia.tito.v1` | it | Gli elefanti sono animali molto sociali. Si toccano spesso con la proboscide per salutarsi, esplorare e comunicare. | `social-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/social-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.elephant.social` | character_dialogue | Tito | `greia.tito.v1` | en | Elephants are very social animals. They often touch with their trunks to greet, explore, and communicate. | `social-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/social-tito.ogg` |  |

---

## 6. Requested batch E3-OCTOPUS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/octopus.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.octopus.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Guarda che polpo! Ha otto braccia morbide, piene di ventose. Tocca il polpo e scopri i suoi trucchi! | `intro-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Look at this octopus! It has eight soft arms covered in suckers. Touch it and discover its tricks! | `intro-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.arms` | character_dialogue | Tito | `greia.tito.v1` | it | Un polpo ha otto braccia, non tentacoli. Le ventose lungo le braccia lo aiutano a toccare e afferrare. | `arms-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/arms-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.arms` | character_dialogue | Tito | `greia.tito.v1` | en | An octopus has eight arms, not tentacles. Suckers along its arms help it touch and hold things. | `arms-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/arms-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.camouflage` | character_dialogue | Tito | `greia.tito.v1` | it | Molti polpi possono cambiare molto in fretta il colore e il disegno della pelle. Così possono confondersi con quello che hanno intorno. | `camouflage-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/camouflage-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.camouflage` | character_dialogue | Tito | `greia.tito.v1` | en | Many octopuses can change the color and pattern of their skin very quickly. That helps them blend into their surroundings. | `camouflage-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/camouflage-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.ink` | character_dialogue | Tito | `greia.tito.v1` | it | Se c'è pericolo, molti polpi possono spruzzare una nuvola d'inchiostro e scappare mentre il predatore è confuso. | `ink-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/ink-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.ink` | character_dialogue | Tito | `greia.tito.v1` | en | When danger comes, many octopuses can release a cloud of ink and escape while the predator is confused. | `ink-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/ink-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.hearts` | character_dialogue | Tito | `greia.tito.v1` | it | Sorpresa: un polpo ha tre cuori! Due spingono il sangue verso le branchie e uno lo manda nel resto del corpo. | `hearts-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/it/hearts-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.octopus.hearts` | character_dialogue | Tito | `greia.tito.v1` | en | Surprise: an octopus has three hearts! Two send blood to the gills, and one sends it around the rest of the body. | `hearts-tito.ogg` | `encyclopedia/pages/animals/octopus/assets/audio/en/hearts-tito.ogg` |  |

---

## 7. Requested batch E4-BEE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/bee.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.bee.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Guarda l'ape tra i fiori! Cerca nettare e polline e, volando da un fiore all'altro, può aiutare le piante a riprodursi. | `intro-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Look at the bee among the flowers! It searches for nectar and pollen and, by flying from flower to flower, can help plants reproduce. | `intro-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.food` | character_dialogue | Tito | `greia.tito.v1` | it | I fiori offrono due cibi importanti: il nettare è ricco di zuccheri, mentre il polline contiene sostanze nutritive importanti per le api. | `food-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/food-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.food` | character_dialogue | Tito | `greia.tito.v1` | en | Flowers offer two important foods: nectar is rich in sugars, while pollen contains important nutrients for bees. | `food-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/food-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.pollen` | character_dialogue | Tito | `greia.tito.v1` | it | Quando un'ape visita un fiore, un po' di polline può restare sul suo corpo. Sul fiore successivo, parte di quel polline può essere trasferita. | `pollen-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/pollen-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.pollen` | character_dialogue | Tito | `greia.tito.v1` | en | When a bee visits a flower, some pollen can stick to its body. At the next flower, some of that pollen can be transferred. | `pollen-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/pollen-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.pollination` | character_dialogue | Tito | `greia.tito.v1` | it | Questo trasporto di polline si chiama impollinazione. Per molte piante è un passaggio importante per formare nuovi semi e frutti. | `pollination-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/pollination-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.pollination` | character_dialogue | Tito | `greia.tito.v1` | en | This movement of pollen is called pollination. For many plants it is an important step in making new seeds and fruits. | `pollination-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/pollination-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.homes` | character_dialogue | Tito | `greia.tito.v1` | it | Non tutte le api vivono in un alveare. La maggior parte delle api selvatiche vive da sola; le api da miele, invece, vivono in grandi colonie. | `homes-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/homes-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.bee.homes` | character_dialogue | Tito | `greia.tito.v1` | en | Not all bees live in a hive. Most wild bees live alone, while honey bees live together in large colonies. | `homes-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/homes-tito.ogg` |  |

---

## 8. Requested batch E4-PENGUIN-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/penguin.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.penguin.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Il pinguino è un uccello che non vola nell'aria: le sue ali sono diventate pinne fortissime per nuotare. Tocca i simboli e tuffiamoci! | `intro-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.intro` | character_dialogue | Tito | `greia.tito.v1` | en | A penguin is a bird that does not fly through the air: its wings have become powerful flippers for swimming. Touch the symbols and let's dive in! | `intro-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.swim` | character_dialogue | Tito | `greia.tito.v1` | it | Sott'acqua le pinne spingono il pinguino in avanti, mentre piedi e coda aiutano a cambiare direzione. | `swim-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/it/swim-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.swim` | character_dialogue | Tito | `greia.tito.v1` | en | Underwater, a penguin's flippers push it forward while its feet and tail help it steer. | `swim-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/en/swim-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.feathers` | character_dialogue | Tito | `greia.tito.v1` | it | Il pinguino ha tante penne corte e sovrapposte che aiutano a tenere fuori l'acqua. Le penne e uno strato di grasso aiutano anche a trattenere il calore. | `feathers-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/it/feathers-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.feathers` | character_dialogue | Tito | `greia.tito.v1` | en | A penguin has many short overlapping feathers that help keep water out. Feathers and a layer of body fat also help hold in heat. | `feathers-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/en/feathers-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.world` | character_dialogue | Tito | `greia.tito.v1` | it | Non tutti i pinguini vivono sul ghiaccio! Vivono nell'emisfero sud, ma alcune specie abitano zone temperate o perfino molto calde. | `world-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/it/world-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.world` | character_dialogue | Tito | `greia.tito.v1` | en | Not every penguin lives on ice! Penguins live in the Southern Hemisphere, but some species live in temperate or even very warm places. | `world-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/en/world-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.breeding` | character_dialogue | Tito | `greia.tito.v1` | it | Molte specie si riuniscono in colonie per riprodursi, ma non fanno tutte lo stesso nido. I pinguini imperatore e reale tengono perfino l'uovo sopra i piedi. | `breeding-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/it/breeding-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.penguin.breeding` | character_dialogue | Tito | `greia.tito.v1` | en | Many penguin species gather in colonies to breed, but they do not all make the same kind of nest. Emperor and king penguins even keep the egg on top of their feet. | `breeding-tito.ogg` | `encyclopedia/pages/animals/penguin/assets/audio/en/breeding-tito.ogg` |  |

---

## 9. Requested batch E4-FROG-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/frog.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.frog.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Le rane sono anfibi e durante la crescita possono cambiare tantissimo. Segui una trasformazione molto comune: dall'uovo al girino, poi alla piccola rana! | `intro-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Frogs are amphibians and can change enormously as they grow. Follow one very common transformation: from egg to tadpole and then to a little frog! | `intro-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.cycle` | character_dialogue | Tito | `greia.tito.v1` | it | In un ciclo molto comune, dall'uovo nasce un girino che vive nell'acqua. Crescendo diventa una ranocchietta e poi una rana adulta. | `cycle-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/it/cycle-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.cycle` | character_dialogue | Tito | `greia.tito.v1` | en | In one very common life cycle, an egg hatches into a tadpole that lives in water. As it grows, it becomes a froglet and then an adult frog. | `cycle-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/en/cycle-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.metamorphosis` | character_dialogue | Tito | `greia.tito.v1` | it | Questa grande trasformazione si chiama metamorfosi. Nel ciclo classico il girino sviluppa le zampe e i polmoni, mentre la coda diventa sempre più piccola. | `metamorphosis-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/it/metamorphosis-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.metamorphosis` | character_dialogue | Tito | `greia.tito.v1` | en | This big transformation is called metamorphosis. In the classic cycle, the tadpole grows legs and lungs while its tail becomes smaller and smaller. | `metamorphosis-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/en/metamorphosis-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.skin` | character_dialogue | Tito | `greia.tito.v1` | it | La pelle delle rane è umida e permeabile e partecipa anche alla respirazione. Per questo l'acqua e l'umidità sono molto importanti per molti anfibi. | `skin-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/it/skin-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.skin` | character_dialogue | Tito | `greia.tito.v1` | en | Frog skin is moist and permeable and also helps with breathing. That is why water and moisture are very important for many amphibians. | `skin-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/en/skin-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.variety` | character_dialogue | Tito | `greia.tito.v1` | it | Attenzione: non tutte le rane crescono nello stesso modo! Molte usano acqua e girini, ma altre depongono le uova in nidi umidi molto diversi. | `variety-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/it/variety-tito.ogg` |  |
| REQUESTED | `encyclopedia.animals.frog.variety` | character_dialogue | Tito | `greia.tito.v1` | en | But not every frog grows in exactly the same way! Many use water and tadpoles, while others lay eggs in very different moist nurseries. | `variety-tito.ogg` | `encyclopedia/pages/animals/frog/assets/audio/en/variety-tito.ogg` |  |

---

## 10. Requested batch E5-SUN-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/sun.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.sun.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questa è la nostra stella: il Sole! È una gigantesca palla di plasma caldissimo e tiene il Sistema Solare unito con la sua gravità. | `intro-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This is our star: the Sun! It is a gigantic ball of extremely hot plasma, and its gravity helps hold the solar system together. | `intro-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.plasma` | character_dialogue | Leo | `greia.leo.v1` | it | Il Sole è l'unica stella del nostro Sistema Solare. Non ha una superficie solida come la Terra: è fatto soprattutto di plasma, idrogeno ed elio. | `plasma-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/it/plasma-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.plasma` | character_dialogue | Leo | `greia.leo.v1` | en | The Sun is the only star in our solar system. It has no solid surface like Earth; it is made mostly of plasma, hydrogen, and helium. | `plasma-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/en/plasma-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.scale` | character_dialogue | Leo | `greia.leo.v1` | it | Il Sole è enorme: è largo circa cento volte la Terra. Guarda quante piccole Terre servono per attraversare il suo diametro! | `scale-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/it/scale-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.scale` | character_dialogue | Leo | `greia.leo.v1` | en | The Sun is enormous: it is about one hundred times wider than Earth. Look how many tiny Earth widths fit across its diameter! | `scale-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/en/scale-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.fusion` | character_dialogue | Leo | `greia.leo.v1` | it | Nel nucleo del Sole, l'idrogeno si unisce e forma elio. Questo processo si chiama fusione e libera l'energia che ci arriva come luce e calore. | `fusion-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/it/fusion-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.fusion` | character_dialogue | Leo | `greia.leo.v1` | en | In the Sun's core, hydrogen joins together to form helium. This process is called fusion, and it releases the energy that reaches us as light and heat. | `fusion-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/en/fusion-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.rotation` | character_dialogue | Leo | `greia.leo.v1` | it | Il Sole non è solido, quindi non gira tutto alla stessa velocità. Vicino all'equatore ruota più in fretta che vicino ai poli. | `rotation-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/it/rotation-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.sun.rotation` | character_dialogue | Leo | `greia.leo.v1` | en | The Sun is not solid, so it does not all rotate at the same speed. Near its equator it turns faster than near its poles. | `rotation-leo.ogg` | `encyclopedia/pages/space/sun/assets/audio/en/rotation-leo.ogg` |  |

---

## 11. Requested batch E5-MERCURY-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/mercury.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.mercury.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questo piccolo mondo è Mercurio, il pianeta più vicino al Sole. È il più piccolo dei pianeti principali e corre intorno al Sole molto velocemente. | `intro-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This small world is Mercury, the planet closest to the Sun. It is the smallest major planet, and it races around the Sun very quickly. | `intro-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.place` | character_dialogue | Leo | `greia.leo.v1` | it | Mercurio è il pianeta più vicino al Sole ed è anche il più piccolo degli otto pianeti principali. | `place-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/it/place-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.place` | character_dialogue | Leo | `greia.leo.v1` | en | Mercury is the planet closest to the Sun, and it is also the smallest of the eight major planets. | `place-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/en/place-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.orbit` | character_dialogue | Leo | `greia.leo.v1` | it | Mercurio completa un giro intorno al Sole in appena ottantotto giorni terrestri. Il suo anno è molto più corto del nostro. | `orbit-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/it/orbit-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.orbit` | character_dialogue | Leo | `greia.leo.v1` | en | Mercury goes around the Sun in only eighty-eight Earth days. Its year is much shorter than ours. | `orbit-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/en/orbit-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.temperature` | character_dialogue | Leo | `greia.leo.v1` | it | Mercurio non ha una spessa atmosfera che trattenga il calore. Al Sole può diventare caldissimo, mentre nella notte può diventare freddissimo. | `temperature-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/it/temperature-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.temperature` | character_dialogue | Leo | `greia.leo.v1` | en | Mercury does not have a thick atmosphere to hold heat. In sunlight it can become extremely hot, while at night it can become extremely cold. | `temperature-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/en/temperature-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.craters` | character_dialogue | Leo | `greia.leo.v1` | it | La superficie di Mercurio è piena di crateri. E c'è una sorpresa: nei crateri polari che restano sempre in ombra può conservarsi ghiaccio d'acqua. | `craters-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/it/craters-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mercury.craters` | character_dialogue | Leo | `greia.leo.v1` | en | Mercury's surface is covered with craters. And there is a surprise: water ice can survive in polar craters that stay permanently in shadow. | `craters-leo.ogg` | `encyclopedia/pages/space/mercury/assets/audio/en/craters-leo.ogg` |  |

---

## 12. Requested batch E5-VENUS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/venus.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.venus.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questa è Venere. Da lontano sembra avvolta da nuvole tranquille, ma sotto quelle nuvole c'è un mondo roccioso caldissimo. | `intro-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This is Venus. From far away it looks wrapped in calm clouds, but beneath those clouds is an extremely hot rocky world. | `intro-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.compare` | character_dialogue | Leo | `greia.leo.v1` | it | Venere è il secondo pianeta dal Sole ed è quasi grande quanto la Terra. Per questo i due pianeti vengono spesso confrontati. | `compare-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/it/compare-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.compare` | character_dialogue | Leo | `greia.leo.v1` | en | Venus is the second planet from the Sun and is nearly the same size as Earth, so the two planets are often compared. | `compare-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/en/compare-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.heat` | character_dialogue | Leo | `greia.leo.v1` | it | Venere è il pianeta più caldo del Sistema Solare. La sua atmosfera molto densa, ricca di anidride carbonica, intrappola tantissimo calore. | `heat-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/it/heat-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.heat` | character_dialogue | Leo | `greia.leo.v1` | en | Venus is the hottest planet in the solar system. Its very dense, carbon-dioxide-rich atmosphere traps an enormous amount of heat. | `heat-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/en/heat-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.clouds` | character_dialogue | Leo | `greia.leo.v1` | it | Spesse nuvole nascondono la superficie di Venere. Sotto ci sono rocce, montagne, valli e tantissime forme vulcaniche. | `clouds-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/it/clouds-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.clouds` | character_dialogue | Leo | `greia.leo.v1` | en | Thick clouds hide Venus's surface. Underneath are rocks, mountains, valleys, and many volcanic features. | `clouds-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/en/clouds-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.rotation` | character_dialogue | Leo | `greia.leo.v1` | it | Venere gira molto lentamente e ruota al contrario rispetto alla maggior parte dei pianeti. Lì il Sole sembrerebbe sorgere a ovest e tramontare a est. | `rotation-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/it/rotation-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.venus.rotation` | character_dialogue | Leo | `greia.leo.v1` | en | Venus turns very slowly and rotates backward compared with most planets. There, the Sun would appear to rise in the west and set in the east. | `rotation-leo.ogg` | `encyclopedia/pages/space/venus/assets/audio/en/rotation-leo.ogg` |  |

---

## 13. Requested batch E5-EARTH-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/earth.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.earth.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questa è casa nostra vista dallo spazio: la Terra, il terzo pianeta dal Sole. È un mondo roccioso con oceani, aria e vita. | `intro-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This is our home seen from space: Earth, the third planet from the Sun. It is a rocky world with oceans, air, and life. | `intro-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.rotation` | character_dialogue | Leo | `greia.leo.v1` | it | La Terra gira continuamente. La parte rivolta verso il Sole è illuminata e vive il giorno; quella girata dall'altra parte vive la notte. | `rotation-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/it/rotation-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.rotation` | character_dialogue | Leo | `greia.leo.v1` | en | Earth is always turning. The side facing the Sun is lit and has daytime; the side turned away has nighttime. | `rotation-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/en/rotation-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.water` | character_dialogue | Leo | `greia.leo.v1` | it | La maggior parte della superficie terrestre è coperta d'acqua. Quasi tutta l'acqua del pianeta si trova negli oceani. | `water-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/it/water-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.water` | character_dialogue | Leo | `greia.leo.v1` | en | Most of Earth's surface is covered by water. Almost all of the planet's water is held in the oceans. | `water-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/en/water-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.seasons` | character_dialogue | Leo | `greia.leo.v1` | it | L'asse della Terra è inclinato. Mentre la Terra gira intorno al Sole, questa inclinazione cambia quanta luce ricevono i due emisferi e crea le stagioni. | `seasons-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/it/seasons-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.seasons` | character_dialogue | Leo | `greia.leo.v1` | en | Earth's axis is tilted. As Earth travels around the Sun, that tilt changes how much sunlight each hemisphere receives and creates the seasons. | `seasons-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/en/seasons-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.life` | character_dialogue | Leo | `greia.leo.v1` | it | La Terra è avvolta da un'atmosfera di gas. È anche l'unico mondo che conosciamo finora dove esiste la vita. | `life-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/it/life-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.earth.life` | character_dialogue | Leo | `greia.leo.v1` | en | Earth is wrapped in an atmosphere of gases. It is also the only world we currently know that has life. | `life-leo.ogg` | `encyclopedia/pages/space/earth/assets/audio/en/life-leo.ogg` |  |

---

## 14. Requested batch E5-MOON-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/moon.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.moon.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Ecco la Luna, il satellite naturale della Terra. Le gira intorno e ci mostra quasi sempre la stessa faccia, ma la Luna gira davvero anche su se stessa. | `intro-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Here is the Moon, Earth's natural satellite. It travels around Earth and shows us almost the same face, but the Moon really does spin on its axis too. | `intro-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.phases` | character_dialogue | Leo | `greia.leo.v1` | it | La Luna non cambia forma. Il Sole ne illumina sempre metà e, mentre la Luna gira intorno alla Terra, noi vediamo porzioni diverse della metà illuminata: sono le fasi lunari. | `phases-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/it/phases-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.phases` | character_dialogue | Leo | `greia.leo.v1` | en | The Moon does not change shape. The Sun always lights half of it, and as the Moon travels around Earth we see different portions of that lit half. Those are the Moon's phases. | `phases-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/en/phases-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.rotation` | character_dialogue | Leo | `greia.leo.v1` | it | La Luna ruota una volta mentre completa un giro intorno alla Terra. Per questo ci mostra quasi sempre lo stesso lato. Il lato lontano non è sempre buio: riceve anche lui la luce del Sole. | `rotation-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/it/rotation-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.rotation` | character_dialogue | Leo | `greia.leo.v1` | en | The Moon rotates once while it completes one orbit around Earth. That is why it shows us almost the same side. The far side is not always dark; it receives sunlight too. | `rotation-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/en/rotation-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.surface` | character_dialogue | Leo | `greia.leo.v1` | it | La Luna è un mondo roccioso coperto di polvere e crateri da impatto. Le grandi zone scure sono antiche pianure riempite molto tempo fa da lava. | `surface-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/it/surface-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.surface` | character_dialogue | Leo | `greia.leo.v1` | en | The Moon is a rocky world covered with dust and impact craters. Its large dark areas are ancient plains that were filled by lava long ago. | `surface-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/en/surface-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.gravity` | character_dialogue | Leo | `greia.leo.v1` | it | Sulla Luna la gravità in superficie è circa un sesto di quella terrestre. Per questo gli astronauti possono sembrare molto più leggeri quando si muovono. | `gravity-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/it/gravity-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.moon.gravity` | character_dialogue | Leo | `greia.leo.v1` | en | Surface gravity on the Moon is about one-sixth as strong as Earth's. That is why astronauts can look much lighter as they move around. | `gravity-leo.ogg` | `encyclopedia/pages/space/moon/assets/audio/en/gravity-leo.ogg` |  |

---

## 15. Requested batch E6-MARS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/mars.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.mars.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questo è Marte, il pianeta rosso. Il suo terreno contiene minerali di ferro che si sono ossidati, un po' come la ruggine, e gli danno quel colore speciale. | `intro-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This is Mars, the red planet. Its soil contains iron minerals that oxidized, a little like rust, helping give the surface its special color. | `intro-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.red` | character_dialogue | Leo | `greia.leo.v1` | it | Marte non è rosso perché brucia. Nel terreno ci sono minerali ricchi di ferro che si sono ossidati: per questo molta polvere e molte rocce appaiono rossastre. | `red-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/it/red-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.red` | character_dialogue | Leo | `greia.leo.v1` | en | Mars is not red because it is burning. Iron-rich minerals in the ground oxidized, so much of the dust and rock looks reddish. | `red-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/en/red-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.day` | character_dialogue | Leo | `greia.leo.v1` | it | Un giorno su Marte dura circa ventiquattro ore e mezza, quasi come sulla Terra. I giorni marziani si chiamano sol. | `day-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/it/day-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.day` | character_dialogue | Leo | `greia.leo.v1` | en | A day on Mars lasts about twenty-four and a half hours, almost like an Earth day. Martian solar days are called sols. | `day-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/en/day-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.water` | character_dialogue | Leo | `greia.leo.v1` | it | Oggi Marte è freddo e molto secco, ma antiche valli, delta e letti di laghi mostrano che miliardi di anni fa molta acqua liquida scorreva sulla sua superficie. | `water-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/it/water-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.water` | character_dialogue | Leo | `greia.leo.v1` | en | Mars is cold and very dry today, but ancient valleys, deltas, and lakebeds show that lots of liquid water flowed across its surface billions of years ago. | `water-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/en/water-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.olympus` | character_dialogue | Leo | `greia.leo.v1` | it | Su Marte c'è Olympus Mons, il vulcano più grande del Sistema Solare. Dalla base alla cima supera i quaranta chilometri di altezza. | `olympus-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/it/olympus-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.mars.olympus` | character_dialogue | Leo | `greia.leo.v1` | en | Mars is home to Olympus Mons, the largest volcano in the solar system. From its base to its summit it rises more than forty kilometers. | `olympus-leo.ogg` | `encyclopedia/pages/space/mars/assets/audio/en/olympus-leo.ogg` |  |

---

## 16. Requested batch E6-JUPITER-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/jupiter.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.jupiter.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Ecco Giove, il pianeta più grande del Sistema Solare! È un gigante gassoso pieno di nuvole, fasce e tempeste. | `intro-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Here is Jupiter, the largest planet in the solar system! It is a gas giant full of clouds, bands, and storms. | `intro-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.scale` | character_dialogue | Leo | `greia.leo.v1` | it | Giove è enorme: è largo circa undici Terre. Se fosse un guscio vuoto, al suo interno ci sarebbe spazio per circa mille Terre. | `scale-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/it/scale-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.scale` | character_dialogue | Leo | `greia.leo.v1` | en | Jupiter is enormous: it is about eleven Earths wide. If it were a hollow shell, roughly one thousand Earths could fit inside. | `scale-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/en/scale-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.day` | character_dialogue | Leo | `greia.leo.v1` | it | Giove gira velocissimo. Un giorno dura solo circa dieci ore: è il giorno più corto di tutti i pianeti del Sistema Solare. | `day-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/it/day-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.day` | character_dialogue | Leo | `greia.leo.v1` | en | Jupiter spins very fast. A day lasts only about ten hours, the shortest day of any planet in the solar system. | `day-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/en/day-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.storm` | character_dialogue | Leo | `greia.leo.v1` | it | La Grande Macchia Rossa è una gigantesca tempesta nell'atmosfera di Giove. Dura da moltissimo tempo ed è ancora più grande della Terra. | `storm-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/it/storm-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.storm` | character_dialogue | Leo | `greia.leo.v1` | en | The Great Red Spot is a gigantic storm in Jupiter's atmosphere. It has lasted a very long time and is still larger than Earth. | `storm-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/en/storm-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.gas` | character_dialogue | Leo | `greia.leo.v1` | it | Le fasce che vediamo sono nuvole, non continenti. Giove è un gigante gassoso e non ha una superficie solida come quella della Terra. | `gas-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/it/gas-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.jupiter.gas` | character_dialogue | Leo | `greia.leo.v1` | en | The bands we see are clouds, not continents. Jupiter is a gas giant and does not have a solid surface like Earth. | `gas-leo.ogg` | `encyclopedia/pages/space/jupiter/assets/audio/en/gas-leo.ogg` |  |

---

## 17. Requested batch E3-SATURN-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/saturn.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.saturn.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Ecco Saturno, il gigante con gli anelli! Tocca il pianeta e i suoi anelli per scoprire come sono fatti. | `intro-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Here is Saturn, the giant with rings! Touch the planet and its rings to discover what they are made of. | `intro-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.place` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno è il sesto pianeta dal Sole ed è il secondo pianeta più grande del nostro Sistema Solare. | `place-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/place-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.place` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn is the sixth planet from the Sun and the second-largest planet in our solar system. | `place-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/place-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.gas` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno è un gigante gassoso fatto soprattutto di idrogeno ed elio. Non ha una superficie solida come la Terra. | `gas-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/gas-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.gas` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn is a gas giant made mostly of hydrogen and helium. It does not have a solid surface like Earth. | `gas-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/gas-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.rings` | character_dialogue | Leo | `greia.leo.v1` | it | Gli anelli di Saturno non sono cerchi solidi. Sono formati da miliardi di pezzetti di ghiaccio e roccia che orbitano intorno al pianeta. | `rings-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/rings-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.rings` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn's rings are not solid hoops. They are made of billions of pieces of ice and rock orbiting the planet. | `rings-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/rings-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.tilt` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno è inclinato e i suoi anelli sono inclinati con lui. Mentre gira intorno al Sole, dalla Terra vediamo gli anelli da angolazioni diverse. | `tilt-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/tilt-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.saturn.tilt` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn is tilted, and its rings are tilted with it. As Saturn travels around the Sun, from Earth we see the rings at different angles. | `tilt-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/tilt-leo.ogg` |  |

---

## 18. Requested batch E6-URANUS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/uranus.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.uranus.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questo è Urano, un gigante ghiacciato che sembra girare quasi sdraiato su un fianco. È uno dei mondi più strani del Sistema Solare. | `intro-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This is Uranus, an ice giant that appears to spin almost on its side. It is one of the strangest-looking worlds in the solar system. | `intro-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.tilt` | character_dialogue | Leo | `greia.leo.v1` | it | L'asse di Urano è inclinato di quasi novantotto gradi. Per questo, mentre ruota, il pianeta sembra quasi rotolare lungo la sua orbita. | `tilt-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/it/tilt-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.tilt` | character_dialogue | Leo | `greia.leo.v1` | en | Uranus's axis is tilted by almost ninety-eight degrees. As it spins, the planet therefore looks almost as if it is rolling along its orbit. | `tilt-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/en/tilt-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.seasons` | character_dialogue | Leo | `greia.leo.v1` | it | Un anno su Urano dura circa ottantaquattro anni terrestri. Con il pianeta così inclinato, le stagioni sono lunghissime e un polo può restare rivolto verso il Sole per molti anni. | `seasons-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/it/seasons-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.seasons` | character_dialogue | Leo | `greia.leo.v1` | en | A year on Uranus lasts about eighty-four Earth years. With the planet tilted so far sideways, its seasons are extremely long and one pole can face the Sun for many years. | `seasons-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/en/seasons-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.color` | character_dialogue | Leo | `greia.leo.v1` | it | L'atmosfera di Urano contiene metano. Questo gas assorbe parte della luce rossa e contribuisce al colore azzurro-verde del pianeta. | `color-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/it/color-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.color` | character_dialogue | Leo | `greia.leo.v1` | en | Uranus's atmosphere contains methane. This gas absorbs some red light and helps give the planet its blue-green color. | `color-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/en/color-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.rings` | character_dialogue | Leo | `greia.leo.v1` | it | Anche Urano ha degli anelli. Sono molto più deboli e scuri di quelli luminosi di Saturno, ma circondano comunque il pianeta. | `rings-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/it/rings-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.uranus.rings` | character_dialogue | Leo | `greia.leo.v1` | en | Uranus has rings too. They are much fainter and darker than Saturn's bright rings, but they still circle the planet. | `rings-leo.ogg` | `encyclopedia/pages/space/uranus/assets/audio/en/rings-leo.ogg` |  |

---

## 19. Requested batch E6-NEPTUNE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/neptune.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.neptune.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Ecco Nettuno, l'ottavo e più lontano dei pianeti principali. È un gigante ghiacciato blu, freddo e pieno di venti potentissimi. | `intro-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Here is Neptune, the eighth and most distant major planet. It is a cold blue ice giant with incredibly powerful winds. | `intro-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.distance` | character_dialogue | Leo | `greia.leo.v1` | it | Nettuno è circa trenta volte più lontano dal Sole della Terra. La luce del Sole impiega circa quattro ore per arrivare fin laggiù. | `distance-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/it/distance-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.distance` | character_dialogue | Leo | `greia.leo.v1` | en | Neptune is about thirty times farther from the Sun than Earth is. Sunlight takes roughly four hours to travel all the way there. | `distance-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/en/distance-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.year` | character_dialogue | Leo | `greia.leo.v1` | it | Nettuno gira su se stesso in circa sedici ore, ma per fare un intero giro intorno al Sole impiega circa centosessantacinque anni terrestri. | `year-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/it/year-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.year` | character_dialogue | Leo | `greia.leo.v1` | en | Neptune spins once in about sixteen hours, but it takes about one hundred sixty-five Earth years to complete one orbit around the Sun. | `year-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/en/year-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.winds` | character_dialogue | Leo | `greia.leo.v1` | it | Nettuno è il mondo più ventoso del Sistema Solare. Alcuni venti superano i duemila chilometri all'ora. | `winds-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/it/winds-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.winds` | character_dialogue | Leo | `greia.leo.v1` | en | Neptune is the windiest world in the solar system. Some winds race faster than two thousand kilometers per hour. | `winds-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/en/winds-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.blue` | character_dialogue | Leo | `greia.leo.v1` | it | Nettuno è un gigante ghiacciato senza una superficie solida come la Terra. Il metano nella sua atmosfera contribuisce al colore blu, e intorno al pianeta ci sono anche anelli molto deboli. | `blue-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/it/blue-leo.ogg` |  |
| REQUESTED | `encyclopedia.space.neptune.blue` | character_dialogue | Leo | `greia.leo.v1` | en | Neptune is an ice giant without a solid surface like Earth's. Methane in its atmosphere contributes to the blue color, and faint rings also circle the planet. | `blue-leo.ogg` | `encyclopedia/pages/space/neptune/assets/audio/en/blue-leo.ogg` |  |

---

## 20. Requested batch E3-VOLCANO-01

Research/provenance authority for this batch:

```text
encyclopedia/research/earth/volcano.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.earth.volcano.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Dentro un vulcano può esserci roccia fusa chiamata magma. Tocca la camera magmatica e vediamo come può iniziare un'eruzione! | `intro-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Inside a volcano there can be melted rock called magma. Touch the magma chamber and let's see how an eruption can begin! | `intro-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.magma` | character_dialogue | Tito | `greia.tito.v1` | it | Sotto la superficie si chiama magma. Quando esce sulla superficie, la roccia fusa si chiama lava. | `magma-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/magma-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.magma` | character_dialogue | Tito | `greia.tito.v1` | en | Below the surface it is called magma. When the melted rock comes out onto the surface, it is called lava. | `magma-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/magma-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.vent` | character_dialogue | Tito | `greia.tito.v1` | it | Il magma può risalire e raccogliersi sotto il vulcano, poi spingersi verso l'alto attraverso crepe e condotti. | `vent-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/vent-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.vent` | character_dialogue | Tito | `greia.tito.v1` | en | Magma can rise and collect beneath a volcano, then push upward through cracks and vents. | `vent-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/vent-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.style` | character_dialogue | Tito | `greia.tito.v1` | it | Se i gas riescono a uscire facilmente, la lava può scorrere. Se restano intrappolati in un magma molto denso, la pressione può aumentare e l'eruzione può essere esplosiva. | `style-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/style-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.style` | character_dialogue | Tito | `greia.tito.v1` | en | If gases can escape easily, lava may flow out. If gas stays trapped in very thick magma, pressure can build and the eruption can be explosive. | `style-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/style-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.ash` | character_dialogue | Tito | `greia.tito.v1` | it | In un'eruzione esplosiva il magma può rompersi in tanti frammenti. I pezzetti più piccoli formano la cenere vulcanica. | `ash-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/ash-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.volcano.ash` | character_dialogue | Tito | `greia.tito.v1` | en | In an explosive eruption, magma can break into many fragments. The tiniest pieces form volcanic ash. | `ash-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/ash-tito.ogg` |  |

---

## 21. Requested batch E7-RAIN-01

Research/provenance authority for this batch:

```text
encyclopedia/research/earth/rain.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.earth.rain.intro` | character_dialogue | Tito | `greia.tito.v1` | it | L'acqua sulla Terra è sempre in viaggio. Il Sole può far evaporare l'acqua, in alto si formano le nuvole e poi l'acqua può tornare giù come pioggia. | `intro-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Water on Earth is always on the move. The Sun can make water evaporate, clouds can form above, and water can come back down as rain. | `intro-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.evaporation` | character_dialogue | Tito | `greia.tito.v1` | it | L'energia del Sole può trasformare una parte dell'acqua liquida in vapore acqueo invisibile che sale nell'atmosfera. Questo processo si chiama evaporazione. | `evaporation-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/it/evaporation-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.evaporation` | character_dialogue | Tito | `greia.tito.v1` | en | Energy from the Sun can turn some liquid water into invisible water vapor that moves into the atmosphere. This process is called evaporation. | `evaporation-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/en/evaporation-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.condensation` | character_dialogue | Tito | `greia.tito.v1` | it | Quando il vapore acqueo si raffredda può condensare in minuscole goccioline. Le nuvole sono formate da tantissime piccole gocce d'acqua e, quando fa abbastanza freddo, anche da cristalli di ghiaccio. | `condensation-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/it/condensation-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.condensation` | character_dialogue | Tito | `greia.tito.v1` | en | When water vapor cools, it can condense into tiny droplets. Clouds are made of huge numbers of tiny water droplets and, when it is cold enough, ice crystals too. | `condensation-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/en/condensation-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.precipitation` | character_dialogue | Tito | `greia.tito.v1` | it | Nelle nuvole le goccioline possono unirsi e crescere. Quando diventano abbastanza grandi e pesanti, l'acqua cade verso terra: la pioggia è una forma di precipitazione. | `precipitation-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/it/precipitation-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.precipitation` | character_dialogue | Tito | `greia.tito.v1` | en | Inside clouds, droplets can join and grow. When they become large and heavy enough, water falls toward the ground. Rain is one form of precipitation. | `precipitation-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/en/precipitation-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.ground` | character_dialogue | Tito | `greia.tito.v1` | it | Dopo la pioggia, una parte dell'acqua scorre in discesa verso ruscelli, fiumi e oceano. Un'altra parte può infiltrarsi nel terreno e continuare il suo viaggio sottoterra. | `ground-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/it/ground-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rain.ground` | character_dialogue | Tito | `greia.tito.v1` | en | After rain, some water runs downhill toward streams, rivers, and the ocean. Some can soak into the ground and continue its journey underground. | `ground-tito.ogg` | `encyclopedia/pages/earth/rain/assets/audio/en/ground-tito.ogg` |  |

---

## 22. Requested batch E7-OCEAN-01

Research/provenance authority for this batch:

```text
encyclopedia/research/earth/ocean.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.earth.ocean.intro` | character_dialogue | Tito | `greia.tito.v1` | it | L'oceano copre più del settanta per cento della Terra. I nomi Pacifico, Atlantico, Indiano, Artico e Meridionale indicano grandi regioni, ma tutta quest'acqua forma un unico oceano collegato. | `intro-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.intro` | character_dialogue | Tito | `greia.tito.v1` | en | The ocean covers more than seventy percent of Earth. Pacific, Atlantic, Indian, Arctic, and Southern are names for large regions, but all that water forms one connected global ocean. | `intro-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.salt` | character_dialogue | Tito | `greia.tito.v1` | it | L'acqua del mare contiene molti sali disciolti. In media, in mille parti di acqua di mare ce ne sono circa trentacinque di sali, anche se la salinità cambia da luogo a luogo. | `salt-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/it/salt-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.salt` | character_dialogue | Tito | `greia.tito.v1` | en | Seawater contains many dissolved salts. On average, about thirty-five parts out of every thousand are dissolved salts, although salinity changes from place to place. | `salt-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/en/salt-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.light` | character_dialogue | Tito | `greia.tito.v1` | it | La luce del Sole penetra soprattutto nella parte più alta dell'oceano. Sotto circa duecento metri diventa molto più debole e, oltre circa mille metri, la luce del Sole non arriva più. | `light-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/it/light-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.light` | character_dialogue | Tito | `greia.tito.v1` | en | Sunlight reaches mainly through the upper ocean. Below about two hundred meters it becomes much weaker, and below roughly one thousand meters sunlight from the surface no longer reaches. | `light-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/en/light-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.deep` | character_dialogue | Tito | `greia.tito.v1` | it | Il mare profondo è buio, freddo e sottoposto a una pressione enorme, ma non è vuoto. Tanti organismi sono adattati a vivere proprio in questi ambienti profondi. | `deep-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/it/deep-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.deep` | character_dialogue | Tito | `greia.tito.v1` | en | The deep ocean is dark, cold, and under enormous pressure, but it is not empty. Many organisms are adapted to live in these deep environments. | `deep-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/en/deep-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.water` | character_dialogue | Tito | `greia.tito.v1` | it | Quasi tutta l'acqua della Terra si trova nell'oceano: circa il novantasette per cento. Il resto è distribuito soprattutto tra ghiaccio, acqua sotterranea, laghi, fiumi e atmosfera. | `water-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/it/water-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.ocean.water` | character_dialogue | Tito | `greia.tito.v1` | en | Almost all of Earth's water is in the ocean: about ninety-seven percent. The rest is found mostly in ice, groundwater, lakes, rivers, and the atmosphere. | `water-tito.ogg` | `encyclopedia/pages/earth/ocean/assets/audio/en/water-tito.ogg` |  |

---

## 23. Requested batch E7-TREE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/earth/tree.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.earth.tree.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Un albero continua anche sotto terra. Le radici lo tengono ancorato, assorbono acqua e sali minerali, e le foglie usano la luce del Sole per costruire il cibo dell'albero. | `intro-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.intro` | character_dialogue | Tito | `greia.tito.v1` | en | A tree continues below the ground. Its roots anchor it and absorb water and minerals, while its leaves use sunlight to make food for the tree. | `intro-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.roots` | character_dialogue | Tito | `greia.tito.v1` | it | Le radici hanno tanti rami sottili che assorbono acqua e sostanze minerali dal terreno. Le radici più grandi aiutano anche a tenere l'albero ben fermo. | `roots-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/it/roots-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.roots` | character_dialogue | Tito | `greia.tito.v1` | en | Roots have many fine branches that absorb water and minerals from the soil. Larger roots also help hold the tree firmly in place. | `roots-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/en/roots-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.water` | character_dialogue | Tito | `greia.tito.v1` | it | L'acqua assorbita dalle radici viaggia verso l'alto attraverso il tronco e i rami fino alle foglie. Un albero deve trasportare continuamente acqua alle sue parti vive. | `water-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/it/water-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.water` | character_dialogue | Tito | `greia.tito.v1` | en | Water absorbed by the roots travels upward through the trunk and branches to the leaves. A tree must keep moving water to its living parts. | `water-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/en/water-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.photosynthesis` | character_dialogue | Tito | `greia.tito.v1` | it | Nelle foglie, l'energia della luce aiuta a usare acqua e anidride carbonica per produrre zuccheri. Questo processo si chiama fotosintesi e produce anche ossigeno. | `photosynthesis-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/it/photosynthesis-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.photosynthesis` | character_dialogue | Tito | `greia.tito.v1` | en | In the leaves, light energy helps use water and carbon dioxide to make sugars. This process is called photosynthesis, and it also produces oxygen. | `photosynthesis-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/en/photosynthesis-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.transpiration` | character_dialogue | Tito | `greia.tito.v1` | it | Una parte dell'acqua esce dalle foglie nell'aria come vapore acqueo. Questo processo si chiama traspirazione ed è anche una parte del ciclo dell'acqua. | `transpiration-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/it/transpiration-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.transpiration` | character_dialogue | Tito | `greia.tito.v1` | en | Some water leaves the leaves and enters the air as water vapor. This process is called transpiration, and it is also part of the water cycle. | `transpiration-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/en/transpiration-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.seasons` | character_dialogue | Tito | `greia.tito.v1` | it | Gli alberi non cambiano tutti allo stesso modo. Molti alberi a foglia larga perdono le foglie nella stagione fredda, mentre molte conifere restano verdi; in altri climi le foglie possono cadere durante la stagione secca. | `seasons-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/it/seasons-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.tree.seasons` | character_dialogue | Tito | `greia.tito.v1` | en | Trees do not all change the same way. Many broad-leaved trees lose their leaves in a cold season, while many conifers stay green; in other climates leaves may fall during a dry season. | `seasons-tito.ogg` | `encyclopedia/pages/earth/tree/assets/audio/en/seasons-tito.ogg` |  |

---

## 24. Requested batch E7-RAINBOW-01

Research/provenance authority for this batch:

```text
encyclopedia/research/earth/rainbow.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.earth.rainbow.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Un arcobaleno appare quando la luce del Sole incontra tante goccioline d'acqua nell'aria e noi le guardiamo dalla posizione giusta. Proviamo a mettere Sole, pioggia e osservatore al posto giusto! | `intro-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/it/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.intro` | character_dialogue | Tito | `greia.tito.v1` | en | A rainbow appears when sunlight meets many water droplets in the air and we look from the right position. Let's place the Sun, rain, and observer in the right arrangement! | `intro-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/en/intro-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.position` | character_dialogue | Tito | `greia.tito.v1` | it | Per vedere un normale arcobaleno, il Sole deve stare dietro di noi e le goccioline d'acqua davanti. L'arcobaleno che vediamo dipende anche dalla posizione di chi guarda. | `position-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/it/position-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.position` | character_dialogue | Tito | `greia.tito.v1` | en | To see a typical rainbow, the Sun needs to be behind us and water droplets in front. The rainbow we see also depends on where the observer is standing. | `position-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/en/position-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.droplet` | character_dialogue | Tito | `greia.tito.v1` | it | Quando la luce entra in una gocciolina cambia direzione. Poi una parte si riflette all'interno e la luce si piega di nuovo quando esce. | `droplet-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/it/droplet-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.droplet` | character_dialogue | Tito | `greia.tito.v1` | en | When light enters a water droplet, it changes direction. Some of it then reflects inside, and the light bends again as it leaves. | `droplet-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/en/droplet-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.colors` | character_dialogue | Tito | `greia.tito.v1` | it | La luce bianca del Sole contiene tanti colori. Nella gocciolina i diversi colori si piegano in modo leggermente diverso e così arrivano ai nostri occhi separati. | `colors-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/it/colors-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.colors` | character_dialogue | Tito | `greia.tito.v1` | en | White sunlight contains many colors. Inside the droplet, different colors bend by slightly different amounts, so they reach our eyes separated. | `colors-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/en/colors-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.circle` | character_dialogue | Tito | `greia.tito.v1` | it | Un arcobaleno completo forma in realtà un cerchio. Da terra, però, il terreno e l'orizzonte di solito ne nascondono una parte e noi vediamo soprattutto un arco. | `circle-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/it/circle-tito.ogg` |  |
| REQUESTED | `encyclopedia.earth.rainbow.circle` | character_dialogue | Tito | `greia.tito.v1` | en | A complete rainbow is actually a circle. From the ground, though, the land and horizon usually hide part of it, so we mostly see an arc. | `circle-tito.ogg` | `encyclopedia/pages/earth/rainbow/assets/audio/en/circle-tito.ogg` |  |

---

## 25. Requested batch E3-HEART-01

Research/provenance authority for this batch:

```text
encyclopedia/research/body/heart.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.body.heart.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | Il cuore è un muscolo grande più o meno come il tuo pugno. Lavora senza sosta per spingere il sangue in tutto il corpo. | `intro-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Your heart is a muscle about the size of your fist. It keeps working to pump blood around your whole body. | `intro-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.chambers` | character_dialogue | Lilli | `greia.lilli.v1` | it | Dentro il cuore ci sono quattro camere. Le due in alto ricevono il sangue e le due in basso lo spingono fuori dal cuore. | `chambers-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/chambers-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.chambers` | character_dialogue | Lilli | `greia.lilli.v1` | en | Inside the heart there are four chambers. The two on top receive blood, and the two below pump it out of the heart. | `chambers-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/chambers-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.circulation` | character_dialogue | Lilli | `greia.lilli.v1` | it | Una parte del cuore manda il sangue ai polmoni per prendere ossigeno. Poi l'altra parte lo spinge verso tutto il corpo. | `circulation-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/circulation-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.circulation` | character_dialogue | Lilli | `greia.lilli.v1` | en | One side of the heart sends blood to the lungs to pick up oxygen. Then the other side pumps it out to the rest of the body. | `circulation-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/circulation-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.beat` | character_dialogue | Lilli | `greia.lilli.v1` | it | Ogni battito è una contrazione che spinge il sangue. Le valvole si chiudono e aiutano a fare il famoso suono: lub-dub! | `beat-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/beat-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.beat` | character_dialogue | Lilli | `greia.lilli.v1` | en | Each heartbeat is a squeeze that pumps blood. Valves close and help make the familiar sound: lub-dub! | `beat-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/beat-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.exercise` | character_dialogue | Lilli | `greia.lilli.v1` | it | Quando corri o giochi con energia, il cuore batte più in fretta per portare più ossigeno ai muscoli. | `exercise-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/exercise-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.heart.exercise` | character_dialogue | Lilli | `greia.lilli.v1` | en | When you run or play energetically, your heart beats faster to bring more oxygen to your muscles. | `exercise-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/exercise-lilli.ogg` |  |

---

## 26. Requested batch E8-LUNGS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/body/lungs.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.body.lungs.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | I polmoni sono due organi morbidi nel torace. Quando respiri, l'aria entra ed esce e nei polmoni il sangue prende ossigeno e lascia anidride carbonica. | `intro-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/it/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Your lungs are two soft organs in your chest. When you breathe, air moves in and out, and inside the lungs your blood picks up oxygen and leaves carbon dioxide behind. | `intro-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/en/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.breath` | character_dialogue | Lilli | `greia.lilli.v1` | it | Per inspirare, il diaframma sotto i polmoni si contrae e scende, creando più spazio nel torace. Quando si rilassa, lo spazio diminuisce e l'aria può uscire. | `breath-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/it/breath-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.breath` | character_dialogue | Lilli | `greia.lilli.v1` | en | To breathe in, the diaphragm below your lungs contracts and moves downward, making more room in your chest. When it relaxes, the space becomes smaller and air can flow out. | `breath-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/en/breath-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.airways` | character_dialogue | Lilli | `greia.lilli.v1` | it | L'aria passa dal naso o dalla bocca nelle vie respiratorie. Dentro i polmoni i tubi si dividono in rami sempre più piccoli fino a raggiungere minuscole sacche d'aria. | `airways-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/it/airways-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.airways` | character_dialogue | Lilli | `greia.lilli.v1` | en | Air travels from your nose or mouth into the airways. Inside your lungs, the tubes branch into smaller and smaller passages until they reach tiny air sacs. | `airways-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/en/airways-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.exchange` | character_dialogue | Lilli | `greia.lilli.v1` | it | Nelle minuscole sacche chiamate alveoli, l'ossigeno passa dall'aria al sangue. Nello stesso momento l'anidride carbonica passa dal sangue all'aria e poi viene espirata. | `exchange-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/it/exchange-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.exchange` | character_dialogue | Lilli | `greia.lilli.v1` | en | In tiny air sacs called alveoli, oxygen moves from the air into your blood. At the same time, carbon dioxide moves from the blood into the air and is then breathed out. | `exchange-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/en/exchange-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.exercise` | character_dialogue | Lilli | `greia.lilli.v1` | it | Quando corri o giochi con energia, i muscoli usano più ossigeno e producono più anidride carbonica. Per questo di solito respiri più velocemente e più profondamente. | `exercise-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/it/exercise-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.lungs.exercise` | character_dialogue | Lilli | `greia.lilli.v1` | en | When you run or play energetically, your muscles use more oxygen and make more carbon dioxide. That is why you usually breathe faster and more deeply. | `exercise-lilli.ogg` | `encyclopedia/pages/body/lungs/assets/audio/en/exercise-lilli.ogg` |  |

---

## 27. Requested batch E8-BONES-01

Research/provenance authority for this batch:

```text
encyclopedia/research/body/bones.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.body.bones.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | Sotto la pelle c'è lo scheletro. Le ossa sostengono il corpo, lavorano con i muscoli per farci muovere e alcune proteggono organi importanti. | `intro-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/it/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Under your skin is your skeleton. Bones support your body, work with muscles to help you move, and some protect important organs. | `intro-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/en/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.joints` | character_dialogue | Lilli | `greia.lilli.v1` | it | Le articolazioni sono i punti dove due o più ossa si incontrano. Alcune, come il gomito, si piegano soprattutto in una direzione; altre, come la spalla, possono muoversi in molte direzioni. | `joints-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/it/joints-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.joints` | character_dialogue | Lilli | `greia.lilli.v1` | en | Joints are places where two or more bones meet. Some, like your elbow, mostly bend one way, while others, like your shoulder, can move in many directions. | `joints-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/en/joints-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.protect` | character_dialogue | Lilli | `greia.lilli.v1` | it | Alcune ossa fanno anche da scudo. Il cranio protegge il cervello e le costole circondano e aiutano a proteggere cuore e polmoni. | `protect-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/it/protect-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.protect` | character_dialogue | Lilli | `greia.lilli.v1` | en | Some bones also act like shields. Your skull protects your brain, and your ribs surround and help protect your heart and lungs. | `protect-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/en/protect-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.living` | character_dialogue | Lilli | `greia.lilli.v1` | it | Le ossa non sono pezzi morti e immobili: sono tessuto vivo. Crescono durante l'infanzia e il corpo continua a rinnovare piccole parti dell'osso per tutta la vita. | `living-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/it/living-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.living` | character_dialogue | Lilli | `greia.lilli.v1` | en | Bones are not dead, unchanging pieces. They are living tissue. They grow during childhood, and your body keeps renewing small parts of bone throughout life. | `living-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/en/living-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.marrow` | character_dialogue | Lilli | `greia.lilli.v1` | it | Dentro alcune ossa c'è il midollo osseo. In questo tessuto morbido il corpo produce nuove cellule del sangue. | `marrow-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/it/marrow-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.bones.marrow` | character_dialogue | Lilli | `greia.lilli.v1` | en | Inside some bones is bone marrow. In this soft tissue, your body makes new blood cells. | `marrow-lilli.ogg` | `encyclopedia/pages/body/bones/assets/audio/en/marrow-lilli.ogg` |  |

---

## 28. Requested batch E8-TEETH-01

Research/provenance authority for this batch:

```text
encyclopedia/research/body/teeth.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.body.teeth.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | I denti non hanno tutti la stessa forma. Quelli davanti tagliano, i canini aiutano ad afferrare e strappare, e i molari larghi schiacciano e macinano il cibo. | `intro-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/it/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Your teeth do not all have the same shape. Front teeth cut, canines help grip and tear, and broad molars crush and grind food. | `intro-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/en/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.jobs` | character_dialogue | Lilli | `greia.lilli.v1` | it | Gli incisivi hanno un bordo adatto a tagliare. I canini sono più appuntiti. I molari hanno superfici larghe che aiutano a schiacciare e masticare. | `jobs-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/it/jobs-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.jobs` | character_dialogue | Lilli | `greia.lilli.v1` | en | Incisors have an edge suited for cutting. Canines are more pointed. Molars have broad surfaces that help crush and chew food. | `jobs-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/en/jobs-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.sets` | character_dialogue | Lilli | `greia.lilli.v1` | it | I bambini hanno prima i denti da latte. Un insieme completo ne ha di solito venti. Crescendo, questi denti vengono sostituiti poco alla volta dai denti permanenti. | `sets-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/it/sets-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.sets` | character_dialogue | Lilli | `greia.lilli.v1` | en | Children first have primary, or baby, teeth. A complete set usually has twenty. As you grow, those teeth are gradually replaced by permanent teeth. | `sets-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/en/sets-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.layers` | character_dialogue | Lilli | `greia.lilli.v1` | it | La parte visibile del dente è coperta dallo smalto, uno strato molto duro che lo protegge. Più all'interno ci sono dentina e polpa, dove arrivano nervi e vasi sanguigni. | `layers-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/it/layers-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.layers` | character_dialogue | Lilli | `greia.lilli.v1` | en | The visible part of a tooth is covered by enamel, a very hard layer that protects it. Deeper inside are dentin and pulp, where nerves and blood vessels are found. | `layers-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/en/layers-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.care` | character_dialogue | Lilli | `greia.lilli.v1` | it | Spazzolare delicatamente tutti i lati dei denti aiuta a togliere la placca. Il dentifricio al fluoro aiuta a rendere lo smalto più resistente alla carie. | `care-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/it/care-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.teeth.care` | character_dialogue | Lilli | `greia.lilli.v1` | en | Gently brushing all sides of your teeth helps remove plaque. Fluoride toothpaste helps make enamel more resistant to tooth decay. | `care-lilli.ogg` | `encyclopedia/pages/body/teeth/assets/audio/en/care-lilli.ogg` |  |

---

## 29. Requested batch E8-SENSES-01

Research/provenance authority for this batch:

```text
encyclopedia/research/body/senses.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.body.senses.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | Il corpo raccoglie informazioni in tanti modi. Occhi, orecchie, naso, bocca e nervi della pelle inviano segnali al cervello, che li usa per costruire quello che vediamo, sentiamo e percepiamo. | `intro-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/it/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Your body collects information in many ways. Eyes, ears, nose, mouth, and sensory nerves send signals to your brain, which uses them to build what you see, hear, and feel. | `intro-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/en/intro-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.sight` | character_dialogue | Lilli | `greia.lilli.v1` | it | La luce entra nell'occhio e raggiunge la retina, sensibile alla luce. La retina trasforma la luce in segnali elettrici che viaggiano lungo il nervo ottico fino al cervello. | `sight-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/it/sight-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.sight` | character_dialogue | Lilli | `greia.lilli.v1` | en | Light enters your eye and reaches the light-sensitive retina. The retina turns light into electrical signals that travel along the optic nerve to your brain. | `sight-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/en/sight-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.hearing` | character_dialogue | Lilli | `greia.lilli.v1` | it | Le onde sonore fanno vibrare il timpano e minuscole ossa dell'orecchio. Nell'orecchio interno queste vibrazioni vengono trasformate in segnali che il nervo uditivo porta al cervello. | `hearing-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/it/hearing-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.hearing` | character_dialogue | Lilli | `greia.lilli.v1` | en | Sound waves make your eardrum and tiny ear bones vibrate. In the inner ear, those vibrations are turned into signals that the auditory nerve carries to your brain. | `hearing-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/en/hearing-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.flavor` | character_dialogue | Lilli | `greia.lilli.v1` | it | Dolce, acido, salato, amaro e umami possono essere percepiti in molte zone della lingua: la famosa mappa della lingua è sbagliata. E quando mangi, gusto e olfatto lavorano molto insieme per creare il sapore. | `flavor-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/it/flavor-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.flavor` | character_dialogue | Lilli | `greia.lilli.v1` | en | Sweet, sour, salty, bitter, and umami can be sensed across many parts of the tongue; the famous tongue taste map is wrong. When you eat, taste and smell also work closely together to create flavor. | `flavor-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/en/flavor-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.touch` | character_dialogue | Lilli | `greia.lilli.v1` | it | I nervi sensoriali portano al cervello informazioni come il tocco, la pressione e la temperatura. Persone diverse possono percepire il mondo in modi un po' diversi, ed è normale. | `touch-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/it/touch-lilli.ogg` |  |
| REQUESTED | `encyclopedia.body.senses.touch` | character_dialogue | Lilli | `greia.lilli.v1` | en | Sensory nerves carry information such as touch, pressure, and temperature to your brain. Different people can experience the world in somewhat different ways, and that is normal. | `touch-lilli.ogg` | `encyclopedia/pages/body/senses/assets/audio/en/touch-lilli.ogg` |  |

---

## 30. Requested batch E3-GEARS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/machines/gears.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.machines.gears.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Ingranaggi pronti! I denti si incastrano e fanno passare il movimento da una ruota all'altra. Prova a farli girare! | `intro-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/intro-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Gears ready! Their teeth mesh together and pass motion from one wheel to the next. Try turning them! | `intro-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/intro-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.teeth` | dani_system_speech | Dani | `greia.dani.system-v1` | it | I denti di due ingranaggi si incontrano. Quando uno gira, spinge i denti dell'altro e lo fa girare. | `teeth-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/teeth-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.teeth` | dani_system_speech | Dani | `greia.dani.system-v1` | en | The teeth of two gears meet. When one turns, it pushes the teeth of the other and makes it turn. | `teeth-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/teeth-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.direction` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Due ingranaggi che si toccano girano in direzioni opposte. Se il primo gira a destra, il vicino gira a sinistra. | `direction-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/direction-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.direction` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Two gears that mesh turn in opposite directions. If the first turns one way, its neighbor turns the other way. | `direction-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/direction-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.ratio` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Se un ingranaggio grande fa girare uno piccolo, quello piccolo gira più veloce. Se uno piccolo fa girare uno grande, quello grande gira più lentamente. | `ratio-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/ratio-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.ratio` | dani_system_speech | Dani | `greia.dani.system-v1` | en | When a large gear drives a small gear, the small one turns faster. When a small gear drives a large gear, the large one turns more slowly. | `ratio-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/ratio-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.rack` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Un ingranaggio rotondo può anche spingere una barra con denti e trasformare un movimento che gira in un movimento diritto. | `rack-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/rack-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.gears.rack` | dani_system_speech | Dani | `greia.dani.system-v1` | en | A round gear can also push a toothed rack and turn spinning motion into straight-line motion. | `rack-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/rack-dani.ogg` |  |

---

## 31. Requested batch E9-MAGNET-01

Research/provenance authority for this batch:

```text
encyclopedia/research/machines/magnet.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.machines.magnet.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Magnete rilevato! Ogni calamita ha due poli. Poli diversi si attirano, mentre poli uguali si respingono anche senza toccarsi. | `intro-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/it/intro-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Magnet detected! Every magnet has two poles. Different poles attract, while matching poles repel even without touching. | `intro-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/en/intro-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.poles` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Se avvicini un polo nord a un polo sud, i magneti si attirano. Nord contro nord, oppure sud contro sud, invece si respingono. | `poles-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/it/poles-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.poles` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Bring a north pole near a south pole and the magnets attract. North facing north, or south facing south, makes them repel instead. | `poles-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/en/poles-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.materials` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Attenzione: non tutto il metallo è attirato da una calamita. Ferro, nichel, cobalto e molti materiali che li contengono reagiscono fortemente; alluminio e rame, per esempio, no. | `materials-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/it/materials-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.materials` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Careful: a magnet does not attract every metal. Iron, nickel, cobalt, and many materials containing them respond strongly; aluminum and copper, for example, do not. | `materials-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/en/materials-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.distance` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Due magneti possono tirarsi o spingersi anche con un piccolo spazio in mezzo. La forza magnetica agisce attraverso il campo che circonda il magnete. | `distance-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/it/distance-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.distance` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Two magnets can pull or push each other even with a small gap between them. Magnetic force acts through the field around the magnet. | `distance-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/en/distance-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.field` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Il campo magnetico non si vede direttamente. Le linee che disegniamo intorno alla calamita sono un modo utile per mostrare dove e come può agire la forza. | `field-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/it/field-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.magnet.field` | dani_system_speech | Dani | `greia.dani.system-v1` | en | A magnetic field cannot be seen directly. The lines we draw around a magnet are a useful way to show where and how its force can act. | `field-dani.ogg` | `encyclopedia/pages/machines/magnet/assets/audio/en/field-dani.ogg` |  |

---

## 32. Requested batch E9-BICYCLE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/machines/bicycle.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.machines.bicycle.intro` | character_dialogue | Flash | `greia.flash.v1` | it | Via! Quando giri i pedali, fai girare la pedivella e la corona. La catena porta quel movimento fino all'ingranaggio della ruota posteriore. | `intro-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/it/intro-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.intro` | character_dialogue | Flash | `greia.flash.v1` | en | Go! When you turn the pedals, you turn the crank and front chainring. The chain carries that motion to the gear on the rear wheel. | `intro-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/en/intro-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.drive` | character_dialogue | Flash | `greia.flash.v1` | it | Segui il movimento: pedali, corona, catena, pignone posteriore e infine ruota. Ogni parte passa il movimento alla successiva. | `drive-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/it/drive-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.drive` | character_dialogue | Flash | `greia.flash.v1` | en | Follow the motion: pedals, chainring, chain, rear sprocket, and finally the wheel. Each part passes motion to the next. | `drive-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/en/drive-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.ratio` | character_dialogue | Flash | `greia.flash.v1` | it | Cambiando la grandezza degli ingranaggi cambia il rapporto. Una marcia più facile richiede meno forza ma fa girare meno la ruota per ogni giro dei pedali; una più dura fa il contrario. | `ratio-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/it/ratio-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.ratio` | character_dialogue | Flash | `greia.flash.v1` | en | Changing gear sizes changes the ratio. An easier gear needs less force but turns the wheel less for each pedal turn; a harder gear does the opposite. | `ratio-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/en/ratio-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.travel` | character_dialogue | Flash | `greia.flash.v1` | it | Con lo stesso giro completo dei pedali, rapporti diversi possono far girare la ruota posteriore di quantità diverse. Gli ingranaggi cambiano il rapporto tra movimento e forza. | `travel-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/it/travel-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.travel` | character_dialogue | Flash | `greia.flash.v1` | en | With the same complete pedal turn, different gear ratios can make the rear wheel turn by different amounts. Gears change the relationship between motion and force. | `travel-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/en/travel-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.energy` | character_dialogue | Flash | `greia.flash.v1` | it | Gli ingranaggi non creano energia gratis. Possono rendere più comodo usare più forza o più movimento, ma c'è sempre uno scambio tra le due cose. | `energy-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/it/energy-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.bicycle.energy` | character_dialogue | Flash | `greia.flash.v1` | en | Gears do not create free energy. They can make it more useful to trade force for motion or motion for force, but there is always a tradeoff. | `energy-flash.ogg` | `encyclopedia/pages/machines/bicycle/assets/audio/en/energy-flash.ogg` |  |

---

## 33. Requested batch E9-AIRPLANE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/machines/airplane.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.machines.airplane.intro` | character_dialogue | Flash | `greia.flash.v1` | it | Pronti al decollo! Un aereo vola grazie a diverse forze che lavorano insieme. Le ali interagiscono con l'aria in movimento e producono portanza, mentre il motore o l'elica forniscono spinta. | `intro-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/it/intro-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.intro` | character_dialogue | Flash | `greia.flash.v1` | en | Ready for takeoff! An airplane flies because several forces work together. Its wings interact with moving air to produce lift, while an engine or propeller provides thrust. | `intro-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/en/intro-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.lift` | character_dialogue | Flash | `greia.flash.v1` | it | Quando l'aria scorre intorno a un'ala, l'ala cambia il movimento dell'aria e si crea una distribuzione di pressione che produce una forza verso l'alto: la portanza. | `lift-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/it/lift-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.lift` | character_dialogue | Flash | `greia.flash.v1` | en | When air flows around a wing, the wing changes the motion of the air and creates a pressure pattern that produces an upward force: lift. | `lift-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/en/lift-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.myth` | character_dialogue | Flash | `greia.flash.v1` | it | Una cosa importante: l'aria che passa sopra e sotto l'ala non deve ritrovarsi nello stesso momento dietro l'ala. La famosa storia del percorso più lungo non spiega correttamente la portanza. | `myth-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/it/myth-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.myth` | character_dialogue | Flash | `greia.flash.v1` | en | One important thing: air passing above and below a wing does not have to meet again at the same time behind it. The famous longer-path story does not correctly explain lift. | `myth-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/en/myth-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.forces` | character_dialogue | Flash | `greia.flash.v1` | it | In volo agiscono quattro forze principali: portanza verso l'alto, peso verso il basso, spinta in avanti e resistenza dell'aria all'indietro. Se cambiano, cambia anche il movimento dell'aereo. | `forces-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/it/forces-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.forces` | character_dialogue | Flash | `greia.flash.v1` | en | Four main forces act in flight: lift upward, weight downward, thrust forward, and drag backward. When their balance changes, the airplane's motion changes too. | `forces-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/en/forces-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.thrust` | character_dialogue | Flash | `greia.flash.v1` | it | Il motore o l'elica spingono l'aereo in avanti attraverso l'aria. Le ali fanno il lavoro principale di portanza: infatti anche un aliante senza motore può volare mentre si muove nell'aria. | `thrust-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/it/thrust-flash.ogg` |  |
| REQUESTED | `encyclopedia.machines.airplane.thrust` | character_dialogue | Flash | `greia.flash.v1` | en | An engine or propeller pushes the airplane forward through the air. The wings do the main lifting work; even an engine-free glider can fly while it moves through the air. | `thrust-flash.ogg` | `encyclopedia/pages/machines/airplane/assets/audio/en/thrust-flash.ogg` |  |

---

## 34. Requested batch E9-BRIDGE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/machines/bridge.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.machines.bridge.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Ponte pronto! Un ponte non deve solo stare fermo: deve prendere il peso del ponte stesso e di ciò che passa sopra, poi portare quelle forze fino ai sostegni e al terreno. | `intro-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/it/intro-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Bridge ready! A bridge does more than stay still. It must carry its own weight and whatever travels across it, then transfer those forces to its supports and the ground. | `intro-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/en/intro-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.load` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Quando metti un peso sul ponte, la forza entra attraverso l'impalcato. Le parti collegate del ponte la trasferiscono verso i sostegni ai lati. | `load-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/it/load-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.load` | dani_system_speech | Dani | `greia.dani.system-v1` | en | When you place a load on a bridge, the force enters through the deck. Connected parts of the bridge transfer it toward the supports at the sides. | `load-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/en/load-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.shapes` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Una trave, un arco e una capriata non portano il peso nello stesso modo. La forma cambia il percorso delle forze attraverso la struttura. | `shapes-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/it/shapes-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.shapes` | dani_system_speech | Dani | `greia.dani.system-v1` | en | A beam, an arch, and a truss do not carry a load in the same way. The shape changes the path forces take through the structure. | `shapes-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/en/shapes-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.forces` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Alcune parti di una struttura vengono compresse, cioè spinte insieme. Altre sono in tensione, cioè vengono tirate. In un ponte vero il disegno decide dove agiscono queste forze. | `forces-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/it/forces-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.forces` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Some parts of a structure are in compression, meaning they are pushed together. Others are in tension, meaning they are pulled. In a real bridge, the design determines where those forces act. | `forces-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/en/forces-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.path` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Segui le frecce: il carico passa da una parte collegata alla successiva fino ai sostegni. Un ponte funziona come un sistema di percorsi per le forze. | `path-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/it/path-dani.ogg` |  |
| REQUESTED | `encyclopedia.machines.bridge.path` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Follow the arrows: the load passes through connected parts until it reaches the supports. A bridge works as a system of paths for forces. | `path-dani.ogg` | `encyclopedia/pages/machines/bridge/assets/audio/en/path-dani.ogg` |  |

---

## 35. Requested batch E10-DINOSAURS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/history/dinosaurs.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.history.dinosaurs.intro` | character_dialogue | Leo | `greia.leo.v1` | it | I dinosauri non erano tutti uguali. Ce n'erano di piccoli e giganteschi, a due o quattro zampe, mangiatori di piante e mangiatori di altri animali. Facciamo un salto indietro nel tempo! | `intro-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Dinosaurs were not all alike. Some were small and some enormous, some walked on two legs or four, and they included plant-eaters and meat-eaters. Let's travel far back in time! | `intro-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.diversity` | character_dialogue | Leo | `greia.leo.v1` | it | Guarda quanto erano diversi. Un tirannosauro camminava su due zampe ed era carnivoro, un Triceratops era erbivoro e camminava su quattro zampe, e i sauropodi avevano colli e code lunghissimi. | `diversity-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/it/diversity-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.diversity` | character_dialogue | Leo | `greia.leo.v1` | en | Look how different they could be. A tyrannosaur walked on two legs and ate meat, Triceratops was a four-legged plant-eater, and sauropods had extremely long necks and tails. | `diversity-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/en/diversity-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.time` | character_dialogue | Leo | `greia.leo.v1` | it | I dinosauri non aviani scomparvero circa sessantasei milioni di anni fa. Gli esseri umani arrivarono moltissimo tempo dopo: persone e tirannosauri non hanno mai vissuto insieme. | `time-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/it/time-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.time` | character_dialogue | Leo | `greia.leo.v1` | en | Non-avian dinosaurs disappeared about sixty-six million years ago. Humans arrived vastly later, so people and tyrannosaurs never lived together. | `time-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/en/time-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.birds` | character_dialogue | Leo | `greia.leo.v1` | it | Però una parte della storia dei dinosauri continua ancora oggi: gli uccelli sono dinosauri viventi. Quando guardi un passero o una gallina, stai guardando un ramo sopravvissuto dei dinosauri. | `birds-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/it/birds-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.birds` | character_dialogue | Leo | `greia.leo.v1` | en | But part of the dinosaur story is still alive today: birds are living dinosaurs. When you look at a sparrow or a chicken, you are seeing a surviving branch of the dinosaur family. | `birds-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/en/birds-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.evidence` | character_dialogue | Leo | `greia.leo.v1` | it | I paleontologi ricostruiscono i dinosauri usando fossili: ossa, denti, impronte e altri indizi. Alcuni dettagli, come molti colori della pelle, restano incerti e possono cambiare quando troviamo nuove prove. | `evidence-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/it/evidence-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.dinosaurs.evidence` | character_dialogue | Leo | `greia.leo.v1` | en | Paleontologists reconstruct dinosaurs from fossils such as bones, teeth, footprints, and other clues. Some details, including many skin colors, remain uncertain and can change when new evidence is found. | `evidence-leo.ogg` | `encyclopedia/pages/history/dinosaurs/assets/audio/en/evidence-leo.ogg` |  |

---

## 36. Requested batch E3-FOSSILS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/history/fossils.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.history.fossils.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Sotto questi strati può nascondersi una traccia di vita antica. Usa il pennello e scopri che cosa è rimasto nel tempo! | `intro-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Under these layers there may be a clue from ancient life. Use the brush and discover what has lasted through time! | `intro-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.definition` | character_dialogue | Leo | `greia.leo.v1` | it | Un fossile è una prova di vita del passato conservata nelle rocce, nei sedimenti o in un altro ambiente geologico. | `definition-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/definition-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.definition` | character_dialogue | Leo | `greia.leo.v1` | en | A fossil is evidence of past life preserved in rock, sediment, or another geologic setting. | `definition-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/definition-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.types` | character_dialogue | Leo | `greia.leo.v1` | it | Un osso, un dente o una conchiglia possono diventare fossili del corpo. Un'impronta o una tana possono diventare fossili di traccia. | `types-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/types-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.types` | character_dialogue | Leo | `greia.leo.v1` | en | A bone, tooth, or shell can become a body fossil. A footprint or burrow can become a trace fossil. | `types-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/types-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.burial` | character_dialogue | Leo | `greia.leo.v1` | it | Essere coperti rapidamente dai sedimenti aiuta a conservare i resti. Le parti dure, come ossa, denti e conchiglie, si conservano più facilmente. | `burial-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/burial-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.burial` | character_dialogue | Leo | `greia.leo.v1` | en | Being buried quickly by sediment helps preserve remains. Hard parts such as bones, teeth, and shells are more likely to survive. | `burial-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/burial-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.rare` | character_dialogue | Leo | `greia.leo.v1` | it | Diventare un fossile è raro. Per questo i fossili sono indizi preziosi, ma non raccontano ogni cosa vissuta nel passato. | `rare-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/rare-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.rare` | character_dialogue | Leo | `greia.leo.v1` | en | Becoming a fossil is rare. Fossils are precious clues, but they do not record every living thing from the past. | `rare-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/rare-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.clues` | character_dialogue | Leo | `greia.leo.v1` | it | Studiando fossili e rocce, gli scienziati possono capire meglio quali esseri vivevano tanto tempo fa e com'era il loro ambiente. | `clues-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/clues-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.fossils.clues` | character_dialogue | Leo | `greia.leo.v1` | en | By studying fossils and rocks, scientists can learn what lived long ago and what those ancient environments were like. | `clues-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/clues-leo.ogg` |  |

---

## 37. Requested batch E10-MAMMOTH-01

Research/provenance authority for this batch:

```text
encyclopedia/research/history/mammoth.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.history.mammoth.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Questo è un mammut lanoso, un parente estinto degli elefanti. Viveva in ambienti freddi e aveva un corpo pieno di adattamenti per trattenere il calore. | `intro-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.intro` | character_dialogue | Leo | `greia.leo.v1` | en | This is a woolly mammoth, an extinct relative of elephants. It lived in cold environments and had several body adaptations that helped conserve heat. | `intro-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.coat` | character_dialogue | Leo | `greia.leo.v1` | it | Il mammut lanoso aveva una folta pelliccia e uno spesso strato di grasso sotto la pelle. Insieme aiutavano a isolare il corpo dal freddo. | `coat-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/it/coat-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.coat` | character_dialogue | Leo | `greia.leo.v1` | en | The woolly mammoth had a thick coat and a substantial layer of fat under its skin. Together they helped insulate its body from the cold. | `coat-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/en/coat-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.ears` | character_dialogue | Leo | `greia.leo.v1` | it | Le orecchie del mammut lanoso erano relativamente piccole. In un clima freddo, avere meno superficie esposta aiuta a perdere meno calore. | `ears-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/it/ears-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.ears` | character_dialogue | Leo | `greia.leo.v1` | en | Woolly mammoth ears were relatively small. In a cold climate, having less exposed surface area helps reduce heat loss. | `ears-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/en/ears-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.elephants` | character_dialogue | Leo | `greia.leo.v1` | it | Mammut ed elefanti appartengono alla stessa grande famiglia, ma il mammut lanoso non era semplicemente un elefante moderno con più pelo: era una specie distinta e oggi estinta. | `elephants-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/it/elephants-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.elephants` | character_dialogue | Leo | `greia.leo.v1` | en | Mammoths and elephants belong to the same broad family, but a woolly mammoth was not simply a modern elephant with more hair. It was a distinct species that is now extinct. | `elephants-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/en/elephants-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.time` | character_dialogue | Leo | `greia.leo.v1` | it | I mammut lanosi vissero moltissimo tempo dopo i grandi dinosauri non aviani e incontrarono anche gli esseri umani. Alcune popolazioni isolate sopravvissero fino a circa quattromila anni fa. | `time-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/it/time-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.mammoth.time` | character_dialogue | Leo | `greia.leo.v1` | en | Woolly mammoths lived vastly later than the large non-avian dinosaurs and even overlapped with humans. Some isolated populations survived until about four thousand years ago. | `time-leo.ogg` | `encyclopedia/pages/history/mammoth/assets/audio/en/time-leo.ogg` |  |

---

## 38. Requested batch E10-CAVE-PAINTINGS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/history/cave_paintings.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.history.cave_paintings.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Moltissimo tempo fa, persone in tante parti del mondo crearono immagini su pareti di grotte e ripari rocciosi. Alcune sono sopravvissute per decine di migliaia di anni. | `intro-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.intro` | character_dialogue | Leo | `greia.leo.v1` | en | A very long time ago, people in many parts of the world made images on cave walls and rock shelters. Some have survived for tens of thousands of years. | `intro-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.images` | character_dialogue | Leo | `greia.leo.v1` | it | Sulle pareti possiamo trovare animali, mani, figure umane e forme geometriche. Possiamo osservare ciò che è stato dipinto, ma spesso non sappiamo con certezza che significato avesse per chi lo creò. | `images-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/it/images-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.images` | character_dialogue | Leo | `greia.leo.v1` | en | On these walls we can find animals, hands, human figures, and geometric shapes. We can observe what was painted, but we often do not know exactly what it meant to the people who made it. | `images-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/en/images-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.pigments` | character_dialogue | Leo | `greia.leo.v1` | it | Gli artisti antichi potevano ottenere colori da materiali naturali, compresi pigmenti minerali. Luoghi e tempi diversi usavano materiali e tecniche diverse. | `pigments-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/it/pigments-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.pigments` | character_dialogue | Leo | `greia.leo.v1` | en | Ancient artists could make colors from natural materials, including mineral pigments. Different places and times used different materials and techniques. | `pigments-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/en/pigments-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.hands` | character_dialogue | Leo | `greia.leo.v1` | it | In alcuni siti ci sono tantissime sagome di mani. Per crearle, una mano poteva essere appoggiata alla parete mentre il pigmento veniva applicato intorno, lasciando il suo contorno. | `hands-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/it/hands-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.hands` | character_dialogue | Leo | `greia.leo.v1` | en | Some sites contain many hand stencils. One way to make them was to hold a hand against the wall while pigment was applied around it, leaving the hand's outline. | `hands-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/en/hands-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.uncertainty` | character_dialogue | Leo | `greia.leo.v1` | it | Gli archeologi raccolgono indizi su età, pigmenti, immagini e posizione, ma per molte pitture il significato preciso resta sconosciuto. Dire «non lo sappiamo ancora» è una parte importante della scienza. | `uncertainty-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/it/uncertainty-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.cave_paintings.uncertainty` | character_dialogue | Leo | `greia.leo.v1` | en | Archaeologists gather clues about age, pigments, images, and location, but the exact meaning of many paintings remains unknown. Saying “we don't know yet” is an important part of science. | `uncertainty-leo.ogg` | `encyclopedia/pages/history/cave_paintings/assets/audio/en/uncertainty-leo.ogg` |  |

---

## 39. Requested batch E10-PYRAMIDS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/history/pyramids.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.history.pyramids.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Le piramidi dell'antico Egitto sono giganteschi monumenti di pietra costruiti dagli esseri umani migliaia di anni fa. Molte furono create come tombe reali dentro grandi complessi funerari. | `intro-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/it/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.intro` | character_dialogue | Leo | `greia.leo.v1` | en | The pyramids of ancient Egypt are enormous stone monuments built by people thousands of years ago. Many were created as royal tombs within larger funerary complexes. | `intro-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/en/intro-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.blocks` | character_dialogue | Leo | `greia.leo.v1` | it | Una grande piramide richiedeva moltissimi blocchi di pietra preparati, trasportati e messi in posizione con grande precisione. Il nostro gioco di strati è solo uno schema, non il vero cantiere in miniatura. | `blocks-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/it/blocks-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.blocks` | character_dialogue | Leo | `greia.leo.v1` | en | A great pyramid required huge numbers of prepared stone blocks to be transported and positioned carefully. Our layer-stacking game is only a diagram, not a miniature copy of the real building process. | `blocks-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/en/blocks-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.workers` | character_dialogue | Leo | `greia.leo.v1` | it | Le piramidi furono costruite da squadre organizzate di persone: artigiani, cavatori, trasportatori, muratori e altri lavoratori. Le prove archeologiche non raccontano la semplice storia di una massa di schiavi incatenati. | `workers-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/it/workers-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.workers` | character_dialogue | Leo | `greia.leo.v1` | en | Pyramids were built by organized teams of people: craftspeople, quarry workers, haulers, masons, and other laborers. Archaeological evidence does not support the simple story of one mass of chained slaves. | `workers-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/en/workers-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.inside` | character_dialogue | Leo | `greia.leo.v1` | it | Dentro e intorno alle piramidi c'erano passaggi, camere e altri edifici del complesso funerario. Le grandi piramidi non erano montagne cave piene di stanze segrete ovunque. | `inside-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/it/inside-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.inside` | character_dialogue | Leo | `greia.leo.v1` | en | Inside and around pyramids were passages, chambers, and other buildings belonging to the funerary complex. Great pyramids were not hollow mountains filled everywhere with secret rooms. | `inside-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/en/inside-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.engineering` | character_dialogue | Leo | `greia.leo.v1` | it | Gli antichi Egizi usavano cave, slitte, rampe, misure e molta organizzazione per muovere e posizionare la pietra. Gli archeologi ricostruiscono questi metodi dalle prove, ma alcuni dettagli del lavoro restano ancora discussi. | `engineering-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/it/engineering-leo.ogg` |  |
| REQUESTED | `encyclopedia.history.pyramids.engineering` | character_dialogue | Leo | `greia.leo.v1` | en | Ancient Egyptians used quarries, sledges, ramps, measurement, and extensive organization to move and place stone. Archaeologists reconstruct these methods from evidence, while some construction details are still debated. | `engineering-leo.ogg` | `encyclopedia/pages/history/pyramids/assets/audio/en/engineering-leo.ogg` |  |

---

## Full v0.1 queue checkpoint

Generated/retained exact recording rows: **378**.

All 36 factual v0.1 entries now have research-ready bilingual requests. Do not add post-v0.1 topic batches until the owner deliberately expands the encyclopedia scope.
---

## 17. Requested batch E6-FOCUS-01 — Solar System focus names (correction)

Required for `faa46ec4` correction §7 — spoken focus names must be real prerecorded cues, not silent hooks.

Presenter: Leo (warm, patient) per Encyclopedia voice authority.

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.sun.name` | character_dialogue | Leo | `greia.leo.v1` | it | Sole | `sun-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/sun-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.sun.name` | character_dialogue | Leo | `greia.leo.v1` | en | Sun | `sun-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/sun-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.mercury.name` | character_dialogue | Leo | `greia.leo.v1` | it | Mercurio | `mercury-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/mercury-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.mercury.name` | character_dialogue | Leo | `greia.leo.v1` | en | Mercury | `mercury-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/mercury-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.venus.name` | character_dialogue | Leo | `greia.leo.v1` | it | Venere | `venus-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/venus-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.venus.name` | character_dialogue | Leo | `greia.leo.v1` | en | Venus | `venus-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/venus-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.earth.name` | character_dialogue | Leo | `greia.leo.v1` | it | Terra | `earth-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/earth-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.earth.name` | character_dialogue | Leo | `greia.leo.v1` | en | Earth | `earth-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/earth-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.moon.name` | character_dialogue | Leo | `greia.leo.v1` | it | Luna | `moon-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/moon-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.moon.name` | character_dialogue | Leo | `greia.leo.v1` | en | Moon | `moon-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/moon-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.mars.name` | character_dialogue | Leo | `greia.leo.v1` | it | Marte | `mars-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/mars-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.mars.name` | character_dialogue | Leo | `greia.leo.v1` | en | Mars | `mars-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/mars-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.jupiter.name` | character_dialogue | Leo | `greia.leo.v1` | it | Giove | `jupiter-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/jupiter-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.jupiter.name` | character_dialogue | Leo | `greia.leo.v1` | en | Jupiter | `jupiter-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/jupiter-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.saturn.name` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno | `saturn-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/saturn-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.saturn.name` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn | `saturn-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/saturn-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.uranus.name` | character_dialogue | Leo | `greia.leo.v1` | it | Urano | `uranus-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/uranus-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.uranus.name` | character_dialogue | Leo | `greia.leo.v1` | en | Uranus | `uranus-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/uranus-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.neptune.name` | character_dialogue | Leo | `greia.leo.v1` | it | Nettuno | `neptune-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/it/neptune-name-leo.ogg` | focus name |
| REQUESTED | `encyclopedia.space.neptune.name` | character_dialogue | Leo | `greia.leo.v1` | en | Neptune | `neptune-name-leo.ogg` | `encyclopedia/pages/space/assets/audio/en/neptune-name-leo.ogg` | focus name |

