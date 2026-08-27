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

## 5. Requested batch E3-SATURN-01

Research/provenance authority for this batch:

```text
encyclopedia/research/space/saturn.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.space.saturn.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Ecco Saturno, il gigante con gli anelli! Tocca il pianeta e i suoi anelli per scoprire come sono fatti. | `intro-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/intro-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Here is Saturn, the giant with rings! Touch the planet and its rings to discover what they are made of. | `intro-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/intro-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.place` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno è il sesto pianeta dal Sole ed è il secondo pianeta più grande del nostro Sistema Solare. | `place-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/place-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.place` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn is the sixth planet from the Sun and the second-largest planet in our solar system. | `place-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/place-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.gas` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno è un gigante gassoso fatto soprattutto di idrogeno ed elio. Non ha una superficie solida come la Terra. | `gas-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/gas-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.gas` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn is a gas giant made mostly of hydrogen and helium. It does not have a solid surface like Earth. | `gas-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/gas-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.rings` | character_dialogue | Leo | `greia.leo.v1` | it | Gli anelli di Saturno non sono cerchi solidi. Sono formati da miliardi di pezzetti di ghiaccio e roccia che orbitano intorno al pianeta. | `rings-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/rings-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.rings` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn's rings are not solid hoops. They are made of billions of pieces of ice and rock orbiting the planet. | `rings-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/rings-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.tilt` | character_dialogue | Leo | `greia.leo.v1` | it | Saturno è inclinato e i suoi anelli sono inclinati con lui. Mentre gira intorno al Sole, dalla Terra vediamo gli anelli da angolazioni diverse. | `tilt-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/it/tilt-leo.ogg` | |
| REQUESTED | `encyclopedia.space.saturn.tilt` | character_dialogue | Leo | `greia.leo.v1` | en | Saturn is tilted, and its rings are tilted with it. As Saturn travels around the Sun, from Earth we see the rings at different angles. | `tilt-leo.ogg` | `encyclopedia/pages/space/saturn/assets/audio/en/tilt-leo.ogg` | |

---

## 6. Requested batch E3-VOLCANO-01

Research/provenance authority for this batch:

```text
encyclopedia/research/earth/volcano.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.earth.volcano.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Dentro un vulcano può esserci roccia fusa chiamata magma. Tocca la camera magmatica e vediamo come può iniziare un'eruzione! | `intro-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Inside a volcano there can be melted rock called magma. Touch the magma chamber and let's see how an eruption can begin! | `intro-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.magma` | character_dialogue | Tito | `greia.tito.v1` | it | Sotto la superficie si chiama magma. Quando esce sulla superficie, la roccia fusa si chiama lava. | `magma-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/magma-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.magma` | character_dialogue | Tito | `greia.tito.v1` | en | Below the surface it is called magma. When the melted rock comes out onto the surface, it is called lava. | `magma-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/magma-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.vent` | character_dialogue | Tito | `greia.tito.v1` | it | Il magma può risalire e raccogliersi sotto il vulcano, poi spingersi verso l'alto attraverso crepe e condotti. | `vent-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/vent-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.vent` | character_dialogue | Tito | `greia.tito.v1` | en | Magma can rise and collect beneath a volcano, then push upward through cracks and vents. | `vent-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/vent-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.style` | character_dialogue | Tito | `greia.tito.v1` | it | Se i gas riescono a uscire facilmente, la lava può scorrere. Se restano intrappolati in un magma molto denso, la pressione può aumentare e l'eruzione può essere esplosiva. | `style-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/style-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.style` | character_dialogue | Tito | `greia.tito.v1` | en | If gases can escape easily, lava may flow out. If gas stays trapped in very thick magma, pressure can build and the eruption can be explosive. | `style-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/style-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.ash` | character_dialogue | Tito | `greia.tito.v1` | it | In un'eruzione esplosiva il magma può rompersi in tanti frammenti. I pezzetti più piccoli formano la cenere vulcanica. | `ash-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/it/ash-tito.ogg` | |
| REQUESTED | `encyclopedia.earth.volcano.ash` | character_dialogue | Tito | `greia.tito.v1` | en | In an explosive eruption, magma can break into many fragments. The tiniest pieces form volcanic ash. | `ash-tito.ogg` | `encyclopedia/pages/earth/volcano/assets/audio/en/ash-tito.ogg` | |

---

## 7. Requested batch E3-HEART-01

Research/provenance authority for this batch:

```text
encyclopedia/research/body/heart.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.body.heart.intro` | character_dialogue | Lilli | `greia.lilli.v1` | it | Il cuore è un muscolo grande più o meno come il tuo pugno. Lavora senza sosta per spingere il sangue in tutto il corpo. | `intro-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/intro-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.intro` | character_dialogue | Lilli | `greia.lilli.v1` | en | Your heart is a muscle about the size of your fist. It keeps working to pump blood around your whole body. | `intro-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/intro-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.chambers` | character_dialogue | Lilli | `greia.lilli.v1` | it | Dentro il cuore ci sono quattro camere. Le due in alto ricevono il sangue e le due in basso lo spingono fuori dal cuore. | `chambers-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/chambers-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.chambers` | character_dialogue | Lilli | `greia.lilli.v1` | en | Inside the heart there are four chambers. The two on top receive blood, and the two below pump it out of the heart. | `chambers-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/chambers-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.circulation` | character_dialogue | Lilli | `greia.lilli.v1` | it | Una parte del cuore manda il sangue ai polmoni per prendere ossigeno. Poi l'altra parte lo spinge verso tutto il corpo. | `circulation-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/circulation-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.circulation` | character_dialogue | Lilli | `greia.lilli.v1` | en | One side of the heart sends blood to the lungs to pick up oxygen. Then the other side pumps it out to the rest of the body. | `circulation-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/circulation-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.beat` | character_dialogue | Lilli | `greia.lilli.v1` | it | Ogni battito è una contrazione che spinge il sangue. Le valvole si chiudono e aiutano a fare il famoso suono: lub-dub! | `beat-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/beat-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.beat` | character_dialogue | Lilli | `greia.lilli.v1` | en | Each heartbeat is a squeeze that pumps blood. Valves close and help make the familiar sound: lub-dub! | `beat-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/beat-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.exercise` | character_dialogue | Lilli | `greia.lilli.v1` | it | Quando corri o giochi con energia, il cuore batte più in fretta per portare più ossigeno ai muscoli. | `exercise-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/it/exercise-lilli.ogg` | |
| REQUESTED | `encyclopedia.body.heart.exercise` | character_dialogue | Lilli | `greia.lilli.v1` | en | When you run or play energetically, your heart beats faster to bring more oxygen to your muscles. | `exercise-lilli.ogg` | `encyclopedia/pages/body/heart/assets/audio/en/exercise-lilli.ogg` | |

---

## 8. Requested batch E3-GEARS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/machines/gears.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.machines.gears.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Ingranaggi pronti! I denti si incastrano e fanno passare il movimento da una ruota all'altra. Prova a farli girare! | `intro-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/intro-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.intro` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Gears ready! Their teeth mesh together and pass motion from one wheel to the next. Try turning them! | `intro-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/intro-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.teeth` | dani_system_speech | Dani | `greia.dani.system-v1` | it | I denti di due ingranaggi si incontrano. Quando uno gira, spinge i denti dell'altro e lo fa girare. | `teeth-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/teeth-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.teeth` | dani_system_speech | Dani | `greia.dani.system-v1` | en | The teeth of two gears meet. When one turns, it pushes the teeth of the other and makes it turn. | `teeth-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/teeth-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.direction` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Due ingranaggi che si toccano girano in direzioni opposte. Se il primo gira a destra, il vicino gira a sinistra. | `direction-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/direction-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.direction` | dani_system_speech | Dani | `greia.dani.system-v1` | en | Two gears that mesh turn in opposite directions. If the first turns one way, its neighbor turns the other way. | `direction-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/direction-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.ratio` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Se un ingranaggio grande fa girare uno piccolo, quello piccolo gira più veloce. Se uno piccolo fa girare uno grande, quello grande gira più lentamente. | `ratio-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/ratio-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.ratio` | dani_system_speech | Dani | `greia.dani.system-v1` | en | When a large gear drives a small gear, the small one turns faster. When a small gear drives a large gear, the large one turns more slowly. | `ratio-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/ratio-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.rack` | dani_system_speech | Dani | `greia.dani.system-v1` | it | Un ingranaggio rotondo può anche spingere una barra con denti e trasformare un movimento che gira in un movimento diritto. | `rack-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/it/rack-dani.ogg` | |
| REQUESTED | `encyclopedia.machines.gears.rack` | dani_system_speech | Dani | `greia.dani.system-v1` | en | A round gear can also push a toothed rack and turn spinning motion into straight-line motion. | `rack-dani.ogg` | `encyclopedia/pages/machines/gears/assets/audio/en/rack-dani.ogg` | |

---

## 9. Requested batch E3-FOSSILS-01

Research/provenance authority for this batch:

```text
encyclopedia/research/history/fossils.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.history.fossils.intro` | character_dialogue | Leo | `greia.leo.v1` | it | Sotto questi strati può nascondersi una traccia di vita antica. Usa il pennello e scopri che cosa è rimasto nel tempo! | `intro-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/intro-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.intro` | character_dialogue | Leo | `greia.leo.v1` | en | Under these layers there may be a clue from ancient life. Use the brush and discover what has lasted through time! | `intro-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/intro-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.definition` | character_dialogue | Leo | `greia.leo.v1` | it | Un fossile è una prova di vita del passato conservata nelle rocce, nei sedimenti o in un altro ambiente geologico. | `definition-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/definition-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.definition` | character_dialogue | Leo | `greia.leo.v1` | en | A fossil is evidence of past life preserved in rock, sediment, or another geologic setting. | `definition-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/definition-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.types` | character_dialogue | Leo | `greia.leo.v1` | it | Un osso, un dente o una conchiglia possono diventare fossili del corpo. Un'impronta o una tana possono diventare fossili di traccia. | `types-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/types-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.types` | character_dialogue | Leo | `greia.leo.v1` | en | A bone, tooth, or shell can become a body fossil. A footprint or burrow can become a trace fossil. | `types-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/types-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.burial` | character_dialogue | Leo | `greia.leo.v1` | it | Essere coperti rapidamente dai sedimenti aiuta a conservare i resti. Le parti dure, come ossa, denti e conchiglie, si conservano più facilmente. | `burial-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/burial-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.burial` | character_dialogue | Leo | `greia.leo.v1` | en | Being buried quickly by sediment helps preserve remains. Hard parts such as bones, teeth, and shells are more likely to survive. | `burial-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/burial-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.rare` | character_dialogue | Leo | `greia.leo.v1` | it | Diventare un fossile è raro. Per questo i fossili sono indizi preziosi, ma non raccontano ogni cosa vissuta nel passato. | `rare-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/rare-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.rare` | character_dialogue | Leo | `greia.leo.v1` | en | Becoming a fossil is rare. Fossils are precious clues, but they do not record every living thing from the past. | `rare-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/rare-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.clues` | character_dialogue | Leo | `greia.leo.v1` | it | Studiando fossili e rocce, gli scienziati possono capire meglio quali esseri vivevano tanto tempo fa e com'era il loro ambiente. | `clues-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/it/clues-leo.ogg` | |
| REQUESTED | `encyclopedia.history.fossils.clues` | character_dialogue | Leo | `greia.leo.v1` | en | By studying fossils and rocks, scientists can learn what lived long ago and what those ancient environments were like. | `clues-leo.ogg` | `encyclopedia/pages/history/fossils/assets/audio/en/clues-leo.ogg` | |

---

## 10. Requested batch E4-LION-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/lion.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.lion.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Ecco il leone! Guarda la criniera, le zampe forti e il grande ruggito. Tocca i simboli e scopri come vive. | `intro-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Here is the lion! Look at its mane, strong front legs, and mighty roar. Touch the symbols and discover how it lives. | `intro-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.mane` | character_dialogue | Tito | `greia.tito.v1` | it | Molti leoni maschi adulti hanno una grande criniera intorno alla testa e al collo. Colore e grandezza possono cambiare da un leone all'altro. | `mane-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/mane-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.mane` | character_dialogue | Tito | `greia.tito.v1` | en | Many adult male lions have a large mane around the head and neck. Its color and size can vary from one lion to another. | `mane-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/mane-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.pride` | character_dialogue | Tito | `greia.tito.v1` | it | I leoni sono i felini più sociali. Spesso vivono in gruppi chiamati branchi, dove diversi leoni restano in contatto e crescono i piccoli. | `pride-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/pride-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.pride` | character_dialogue | Tito | `greia.tito.v1` | en | Lions are the most social cats. They often live in groups called prides, where several lions stay connected and raise their young. | `pride-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/pride-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.roar` | character_dialogue | Tito | `greia.tito.v1` | it | Il ruggito aiuta i leoni a comunicare e a segnalare il loro territorio. È così potente che può sentirsi da molto lontano. | `roar-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/roar-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.roar` | character_dialogue | Tito | `greia.tito.v1` | en | A roar helps lions communicate and signal their territory. It is so powerful that it can be heard from very far away. | `roar-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/roar-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.forelegs` | character_dialogue | Tito | `greia.tito.v1` | it | Il leone ha zampe anteriori molto forti. Insieme al corpo compatto, lo aiutano a muoversi e ad afferrare con forza. | `forelegs-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/it/forelegs-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.lion.forelegs` | character_dialogue | Tito | `greia.tito.v1` | en | A lion has very strong front legs. Together with its compact body, they help it move and grip powerfully. | `forelegs-tito.ogg` | `encyclopedia/pages/animals/lion/assets/audio/en/forelegs-tito.ogg` | |

---

## 11. Requested batch E4-ELEPHANT-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/elephant.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.elephant.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Ecco l'elefante! La proboscide è forte e delicata, le grandi orecchie aiutano a rinfrescarsi e il contatto serve anche per comunicare. | `intro-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Here is the elephant! Its trunk is strong and delicate, its large ears help it cool down, and touch is also part of elephant communication. | `intro-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.trunk` | character_dialogue | Tito | `greia.tito.v1` | it | La proboscide unisce naso e labbro superiore. È piena di muscoli e serve per annusare, toccare, prendere il cibo e spostare oggetti. | `trunk-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/trunk-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.trunk` | character_dialogue | Tito | `greia.tito.v1` | en | The trunk combines the nose and upper lip. It is packed with muscles and is used to smell, touch, pick up food, and move objects. | `trunk-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/trunk-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.water` | character_dialogue | Tito | `greia.tito.v1` | it | L'elefante aspira l'acqua nella proboscide e poi la spruzza dentro la bocca per bere. Può usarla anche per fare il bagno. | `water-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/water-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.water` | character_dialogue | Tito | `greia.tito.v1` | en | An elephant draws water into its trunk and then squirts it into its mouth to drink. It can also use the trunk for bathing. | `water-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/water-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.ears` | character_dialogue | Tito | `greia.tito.v1` | it | Le grandi orecchie hanno molti vasi sanguigni. Quando l'elefante le muove, possono aiutarlo a disperdere calore e rinfrescarsi. | `ears-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/ears-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.ears` | character_dialogue | Tito | `greia.tito.v1` | en | Large elephant ears contain many blood vessels. Flapping them can help move heat away and cool the elephant. | `ears-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/ears-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.social` | character_dialogue | Tito | `greia.tito.v1` | it | Gli elefanti sono animali molto sociali. Si toccano spesso con la proboscide per salutarsi, esplorare e comunicare. | `social-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/it/social-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.elephant.social` | character_dialogue | Tito | `greia.tito.v1` | en | Elephants are very social animals. They often touch with their trunks to greet, explore, and communicate. | `social-tito.ogg` | `encyclopedia/pages/animals/elephant/assets/audio/en/social-tito.ogg` | |

---

## 12. Requested batch E4-BEE-01

Research/provenance authority for this batch:

```text
encyclopedia/research/animals/bee.md
```

| STATUS | CUE_ID | KIND | SPEAKER | VOICE_ID | LOCALE | EXACT_TEXT | FINAL_FILENAME | FINAL_PATH | RECORDER_NOTES |
|---|---|---|---|---|---|---|---|---|---|
| REQUESTED | `encyclopedia.animals.bee.intro` | character_dialogue | Tito | `greia.tito.v1` | it | Guarda l'ape tra i fiori! Cerca nettare e polline e, volando da un fiore all'altro, può aiutare le piante a riprodursi. | `intro-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.intro` | character_dialogue | Tito | `greia.tito.v1` | en | Look at the bee among the flowers! It searches for nectar and pollen and, by flying from flower to flower, can help plants reproduce. | `intro-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/intro-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.food` | character_dialogue | Tito | `greia.tito.v1` | it | I fiori offrono due cibi importanti: il nettare è ricco di zuccheri, mentre il polline contiene sostanze nutritive importanti per le api. | `food-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/food-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.food` | character_dialogue | Tito | `greia.tito.v1` | en | Flowers offer two important foods: nectar is rich in sugars, while pollen contains important nutrients for bees. | `food-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/food-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.pollen` | character_dialogue | Tito | `greia.tito.v1` | it | Quando un'ape visita un fiore, un po' di polline può restare sul suo corpo. Sul fiore successivo, parte di quel polline può essere trasferita. | `pollen-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/pollen-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.pollen` | character_dialogue | Tito | `greia.tito.v1` | en | When a bee visits a flower, some pollen can stick to its body. At the next flower, some of that pollen can be transferred. | `pollen-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/pollen-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.pollination` | character_dialogue | Tito | `greia.tito.v1` | it | Questo trasporto di polline si chiama impollinazione. Per molte piante è un passaggio importante per formare nuovi semi e frutti. | `pollination-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/pollination-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.pollination` | character_dialogue | Tito | `greia.tito.v1` | en | This movement of pollen is called pollination. For many plants it is an important step in making new seeds and fruits. | `pollination-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/pollination-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.homes` | character_dialogue | Tito | `greia.tito.v1` | it | Non tutte le api vivono in un alveare. La maggior parte delle api selvatiche vive da sola; le api da miele, invece, vivono in grandi colonie. | `homes-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/it/homes-tito.ogg` | |
| REQUESTED | `encyclopedia.animals.bee.homes` | character_dialogue | Tito | `greia.tito.v1` | en | Not all bees live in a hive. Most wild bees live alone, while honey bees live together in large colonies. | `homes-tito.ogg` | `encyclopedia/pages/animals/bee/assets/audio/en/homes-tito.ogg` | |

---

## 13. Pending future batches

Do **not** record these yet.

Future batches are appended only after page research and wording are ready. No additional factual batch is `REQUESTED` until its research provenance exists.
