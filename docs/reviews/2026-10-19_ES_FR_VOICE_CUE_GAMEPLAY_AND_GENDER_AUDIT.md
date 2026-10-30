# ES/FR voice-cue gameplay and gender audit — 2026-10-19

**Status:** PROPOSAL for owner approval. Nothing here has been applied.
**Evidence scope:** SOURCE review only. No audio was synthesised or listened to;
`plan.json` and `state.sqlite3` of the live corpus run were only read.

## 1. Why this exists

The corpus regeneration (owner exception 2026-10-19,
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`) re-records every READY cue with
the text frozen in its plan. While resolving the blocked EN/IT cues, we saw that
several Spanish and French lines released on 2026-10-17 describe different
gameplay from what the Activity code does, or address the child with gendered
words. Those ES/FR cues are READY in the live run, so they will be re-recorded
with the drifted text.

This report lists every ES/FR cue that should change, with a proposed text,
so the owner can approve wording before a **new, deliberate plan** is made once
the current run has finished (§2 of the regeneration manual: "finish/restore
that run and create a deliberate new plan; do not silently rewrite its history").

## 2. Sources and method

| Source | What it gave |
|---|---|
| `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/plan.json` (`row.request.text`, `row.state`) | The exact ES/FR (and READY EN/IT) text the live run will speak. 5,308 rows: 4,543 READY, 167 BLOCKED_METADATA, 598 PRESERVED. |
| `git show 078812efb^:tools/generate_<name>_audio.py` (13 deleted scripts) and the kept `tools/generate_{stelle_incantate,viaggio_delfino}_audio.py` | The authored EN/IT meaning for cues whose EN/IT rows are BLOCKED (text `None`) in the plan. |
| Activity source (`activities/*/*.py`), in particular each `*_audio.py` docstring and every `say(...)`/`line(...)`/`enqueue(...)` caller | When a cue plays and what the child is doing at that moment. |
| `src/greia_platform/localization.py` `speech_paths()` | Both `assets/audio/<lang>/` and `locales/<lang>/audio/` are searched, so an ES/FR clip in either folder **replaces** the EN/IT line for that cue. |
| Commit `a5b15e6a`, `skills/greia-activity-authoring/PRE_READER_UX.md` §4.1, `docs/product/FIRST_BOOT_PROFILE_SETUP.md` (ADR 0032 neutral baseline) | Rule: praise and child-addressed speech must not gender the child. |

Checks applied to every ES/FR row of every Activity, the shared character
library, first-boot and launcher labels:

1. **Gameplay match.** Does the line describe what the code is doing when it plays it?
2. **Meaning match.** Does it say what the EN/IT authored line says?
3. **Gender.** Does it give the child a grammatical gender?
4. **Caller exists.** Does any code play it? Unused cues are listed separately (§8).

Severity: **HIGH**: wrong instruction or wrong reaction for the gameplay.
**MEDIUM**: same situation, but the line loses the instruction or character content
that EN/IT have. **GENDER**: breaks the neutral-address rule. **LOW**: style or
optional neutralisation.

Proposed texts follow the existing ES (Spain) and FR register of the corpus.
A native-speaker read is still recommended before approval.

## 3. Summary

| Activity / area | HIGH | MEDIUM | GENDER | Notes |
|---|---:|---:|---:|---|
| luci_di_momo | 4 | 5 | 1 (+1 unused cue) | prompt_choose describes a different game |
| specchi_magici | 3 | 2 | 1 | retry_2 tells the child to rotate a shape; the game has no rotation. Also 28 ES/FR rows planned with the wrong speaker (Leo instead of Lilli, §4.2.1) |
| casa_del_dieci | 13 | 0 | 0 | every prompt is a different task from the one on screen |
| bottega_delle_misure | 1 | 5 | 0 | |
| faccine_momo | 1 | 8 | 0 | comfort line is the opposite reaction |
| il_giardino_dei_numeri | 1 | 0 | 0 | intro talks about picking flowers |
| bosco_numeri | 1 | 0 | 1 | intro |
| quattro_stagioni | 0 | 9 | 0 | season/weather lines reduced to labels |
| mondo_contrari | 0 | 0 | 1 | labels match the code; only welcome |
| colline_allegre, quattro_amici, sottomarino_giramondo, workshop_settings | 0 | 0 | 3 (+2 LOW) | |
| enciclopedia_greia | systemic | 199 rows | 0 | ES/FR speak the on-screen caption, not the narration (§6) |
| Shared character library, first-boot, launcher labels, other Activities | 0 | 0 | 0 | No mismatch found; see §7 for owner decisions |

Activities checked with **no ES/FR finding**: acquario_magico, alfabeto_leo (played cues),
baia_delle_orche, clinica_cuccioli, corsa_bacche, costruiamo_ponti, cucciolo_mio,
festa_delle_rime (played cues), foresta_parole, la_discesa_della_biglia,
labirinto_magico, memory_meraviglie, morbidi_mostriciattoli, nanna_delle_nuvolette,
nascondino_bosco, officina_dei_suoni (played cues), orchestra_animali, painting,
pasticceria_magica, piccola_serra, posta_di_leo, shape_garden, sillabe_magiche,
stelle_incantate, storie_della_mia_voce, teatrino_fiabe, torre_forme, treno_numeri,
viaggio_delfino, volo_draghetto, writing. (`tempo_di_greia` has no ES/FR rows.)
The alfabeto_leo and foresta_parole "X as Word" cues were checked against
`EXAMPLES_ES/FR` and `PHONICS_DATA`: every spoken word matches the picture word.

## 4. Gameplay and meaning mismatches

Paths are `activities/<activity>/assets/audio/{es,fr}/<cue>.wav` unless noted.

### 4.1 luci_di_momo (speaker: Momo)

Code: `firefly_app.py` shows fireflies, hides them, then asks how many; the child
taps a number. `firefly_audio.py` docstring: `count_1..5` = "three fireflies!",
`count_6..10` = bare number.

| Cue | ES now | FR now | Intended (code + EN/IT) | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `prompt_choose` | ¡Ahora toca las luces en orden! | Maintenant, touche les lumières dans l'ordre ! | Asked after the fireflies hide: "How many fireflies did you see?" / "Quante lucciole hai visto?" | HIGH | ¿Cuántas luciérnagas has visto? | Combien de lucioles as-tu vues ? |
| `welcome` | ¡Bienvenido al jardín de las luces! | Bienvenue dans le jardin des lumières ! | Plays before the first glimpse: "Look closely at how many fireflies glow in the night, then tap the right number!" | HIGH + GENDER (ES) | ¡Hola! Mira bien cuántas luciérnagas brillan en la noche y luego toca el número correcto. | Coucou ! Regarde bien combien de lucioles brillent dans la nuit, puis touche le bon nombre ! |
| `retry_1` | ¡Inténtalo otra vez! | Essaie encore ! | "Almost! Look again at how many fireflies glow!" | HIGH (the counting hint is lost) | ¡Casi! Mira otra vez cuántas luciérnagas brillan. | Presque ! Regarde encore combien de lucioles brillent ! |
| `retry_2` | ¡Mira otra vez! | Regarde encore ! | "Try again, look closely at the little lights!" | MEDIUM | Inténtalo otra vez: ¡mira bien las lucecitas! | Essaie encore, regarde bien les petites lumières ! |
| `count_1` | Uno | Un | "One firefly!" | HIGH (docstring contract) | ¡Una luciérnaga! | Une luciole ! |
| `count_2` | Dos | Deux | "Two fireflies!" | MEDIUM | ¡Dos luciérnagas! | Deux lucioles ! |
| `count_3` | Tres | Trois | "Three fireflies!" | MEDIUM | ¡Tres luciérnagas! | Trois lucioles ! |
| `count_4` | Cuatro | Quatre | "Four fireflies!" | MEDIUM | ¡Cuatro luciérnagas! | Quatre lucioles ! |
| `count_5` | Cinco | Cinq | "Five fireflies!" | MEDIUM | ¡Cinco luciérnagas! | Cinq lucioles ! |
| `garden_complete` | ¡El jardín brilla con mil luces! | Le jardin brille de mille feux ! | "Wonderful! All the fireflies are shining bright and happy!" | LOW (acceptable as is) | ¡Qué maravilla! ¡Todas las luciérnagas brillan felices! | Merveilleux ! Toutes les lucioles brillent de joie ! |
| `count_together` | Contémoslas juntos. | Comptons-les ensemble. | "Let's count them together." (Momo + child) | LOW (generic masculine plural, see §7.3) | Vamos a contarlas. | keep |
| `prompt_ready` | ¿Listo? ¡Mira las luces! | Prêt ? Regarde les lumières ! | No caller in current code (§8). | GENDER | drop from the new plan; if kept: ¿Todo listo? ¡Mira las luces! | drop; if kept: C'est parti ? Regarde les lumières ! |

### 4.2 specchi_magici (speaker: Lilli)

Code: `mirror_app.py`. The child places tiles so the picture is mirrored across a
line. `retry_1` plays for `PlaceOutcome.WRONG_CELL` (nothing belongs there),
`retry_2` for `WRONG_PIECE` (another tile belongs there). The "unreflected copy"
case already plays `turn_it`. There is no free rotation control.

| Cue | ES now | FR now | Intended | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `retry_2` | ¡Gira la forma! | Tourne la forme ! | Wrong tile on a valid spot. EN/IT: "Try again, you are so close!" (IT original "sei quasi riuscito" is gendered, see §5.2) | HIGH | Inténtalo otra vez, ¡ya casi lo tienes! | Essaie encore, tu y es presque ! |
| `prompt_place` | ¡Coloca la forma en el espejo! | Place la forme dans le miroir ! | Each new mosaic: "Mirror the shapes across the magic line!" (tiles go on the other side, not "in the mirror") | HIGH | ¡Refleja las formas al otro lado de la línea mágica! | Reflète les formes de l'autre côté de la ligne magique ! |
| `welcome` | ¡Bienvenido a los espejos mágicos! | Bienvenue dans les miroirs magiques ! | "Look in the magic mirror and place the matching shapes on the other side!" | HIGH + GENDER (ES) | ¡Hola! Mira el espejo mágico y coloca las formas iguales al otro lado. | Coucou ! Regarde le miroir magique et place les mêmes formes de l'autre côté ! |
| `retry_1` | ¡Inténtalo otra vez! | Essaie encore ! | Nothing belongs on that spot: "Almost! Look closely at the distance from the mirror!" | MEDIUM | ¡Casi! Fíjate bien en la distancia al espejo. | Presque ! Regarde bien la distance jusqu'au miroir ! |
| `mosaic_complete` | ¡Qué hermoso mosaico mágico! | Quel beau puzzle magique ! | "Beautiful mirror! Here is the next mosaic!" (FR says "puzzle") | MEDIUM | ¡Qué espejo tan bonito! ¡Aquí llega el siguiente mosaico! | Quel beau miroir ! Voici la mosaïque suivante ! |

#### 4.2.1 Speaker correction (owner decision, relayed 2026-10-19)

The owner decided that Specchi Magici uses **Lilli for every cue**. In the live
plan, 28 ES/FR Specchi rows are READY with `speaker=leo` and Leo's delivery
prompt. The other 12 ES/FR Specchi rows are already `lilli`, verified against
`plan.json`. The list is in
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-corpus-prepared/specchi_es_fr_to_lilli.txt`:
`correct_1..5`, `mosaic_complete`, `prompt_place`, `retry_1`, `retry_2`,
`shape_circle`, `shape_semicircle`, `shape_square`, `shape_triangle` and `welcome`, in both `es` and `fr`.

In the post-run correction plan, all 28 need `speaker=lilli` and Lilli's
default `delivery_prompt` (`tools/greia_voice_core/character_delivery.json`,
identical to the live plan's snapshot): *"Wonder-filled and affectionate, with
a sparkling storybook-unicorn smile. Gentle theatrical lilt, buoyant warmth and
clear, unhurried words."*

- 10 of them also take the text fixes above: `welcome`, `prompt_place`,
  `retry_1`, `retry_2` and `mosaic_complete`, in ES and FR.
- The other 18 keep their current text and change speaker and prompt only.
  These are `correct_1..5` and the four `shape_*` cues, in ES and FR.

The EN/IT Specchi cues are already set to Lilli in that folder's `overrides.json`.
Leave them as they are.

### 4.3 casa_del_dieci (speaker: Dani)

Code: `ten_house_app.py`. Compose: the child switches on N lights. Add / take-away /
missing part: the child answers a "how many" question with a number. The current
ES/FR lines are imperatives ("Add!", "Take away!", "Make number 7!") that do not
match these tasks.

| Cue | ES now | FR now | Intended (EN/IT) | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `prompt_compose_1` | ¡Forma el número 1! | Forme le nombre 1 ! | "Turn on 1 light in the house!" | HIGH | ¡Enciende una luz en la casa! | Allume une lumière dans la maison ! |
| `prompt_compose_2` … `_9` | ¡Forma el número N! | Forme le nombre N ! | "Turn on N lights in the house!" | HIGH (8 cues) | ¡Enciende N luces en la casa! | Allume N lumières dans la maison ! |
| `prompt_compose_10` | ¡Forma el número 10! | Forme le nombre 10 ! | "Turn on all 10 lights in the house!" | HIGH | ¡Enciende las 10 luces de la casa! | Allume les 10 lumières de la maison ! |
| `prompt_add` | ¡Añade! | Ajoute ! | After guests arrive: "How many lights are on in all?" | HIGH | ¿Cuántas luces hay encendidas en total? | Combien de lumières sont allumées en tout ? |
| `prompt_take_away` | ¡Quita! | Enlève ! | After fireflies fly home: "How many lights are left on?" (the child removes nothing) | HIGH | ¿Cuántas luces quedan encendidas? | Combien de lumières restent allumées ? |
| `prompt_missing_part` | ¡Encuentra la parte que falta! | Trouve la partie qui manque ! | "How many lights are missing?" | HIGH | ¿Cuántas luces faltan por encender? | Combien de lumières reste-t-il à allumer ? |

(In the table, N is written as a digit, as in the EN/IT originals: "¡Enciende 2 luces en la casa!".)

### 4.4 bottega_delle_misure (speaker: Dani)

Code: `measure_app.prompt_cue()`. Compare tasks: the child taps one of two parcels.
Measure tasks: `prompt_measure` plays before any block is laid ("measure the
parcel"), then `line_up_blocks`, then `how_many_long`.

| Cue | ES now | FR now | Intended | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `prompt_measure` | ¡Mide el objeto! | Mesure l'objet ! | Code: "measure the parcel" before laying blocks. (The EN/IT originals, "Count how many blocks long the parcel is and tap the number!", describe the older flow; the owner should align them too, §5.2.) | HIGH | ¡Mide el paquete con los bloques! | Mesure le colis avec les cubes ! |
| `prompt_compare_longer` | ¿Cuál es más largo? | Lequel est le plus long ? | "Tap the longer parcel!" | MEDIUM (action lost) | ¡Toca el paquete más largo! | Touche le colis le plus long ! |
| `prompt_compare_shorter` | ¿Cuál es más corto? | Lequel est le plus court ? | "Tap the shorter parcel!" | MEDIUM | ¡Toca el paquete más corto! | Touche le colis le plus court ! |
| `prompt_compare_taller` | ¿Cuál es más alto? | Lequel est le plus haut ? | "Tap the taller parcel!" | MEDIUM | ¡Toca el paquete más alto! | Touche le colis le plus haut ! |
| `prompt_compare_shorter_h` | ¿Cuál es más bajo? | Lequel est le plus bas ? | "Tap the shorter (height) parcel!" | MEDIUM | ¡Toca el paquete más bajo! | Touche le colis le moins haut ! |
| `retry_2` | ¡Compara con atención! | Compare bien ! | "Almost, try again!" (also plays in measuring tasks, where "compare" is wrong) | MEDIUM | ¡Casi! Prueba otra vez. | Presque ! Essaie encore ! |

`prompt_order_height`, `prompt_order_length` and `prompt_shelf` have no caller (§8).

### 4.5 faccine_momo (speaker: Momo)

ES/FR clips sit in `assets/audio/{es,fr}/`; EN/IT in `locales/{en,it}/audio/`.
Both folders feed `speech_paths()`, so the ES/FR clip is what plays. Code
(`momo_app.py`): `comfort` plays **after the child has comforted Momo**;
`<emotion>` plays when Momo acts out a feeling; `game_prompt` replays the
recognise question; `welcome` on the listen button.

| Cue | ES now | FR now | Intended (EN/IT) | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `comfort` | ¡No estés triste! | Ne sois pas triste ! | Momo thanks the child: "Thank you for the cuddle! I feel much better now!" | HIGH | ¡Gracias por el abrazo! ¡Ya me siento mucho mejor! | Merci pour le câlin ! Je me sens beaucoup mieux ! |
| `game_prompt` | ¡Toca la carita! | Touche la grimace ! | "How is Momo feeling now? Look at my face!" | MEDIUM | ¿Cómo se siente Momo ahora? ¡Mira mi carita! | Comment se sent Momo maintenant ? Regarde ma frimousse ! |
| `welcome` | ¡Hola! ¡Mira mis caritas! | Bonjour ! Regarde mes grimaces ! | "Hi! I am Momo! Let's play with faces!" | MEDIUM | ¡Hola! ¡Soy Momo! ¿Jugamos con las caritas? | Coucou ! Moi, c'est Momo ! On joue avec les frimousses ? |
| `happy` | Feliz | Heureux | Momo, in character: "Yaaay! I am so happy! What joy!" | MEDIUM | ¡Yupiii! ¡Estoy muy feliz! ¡Qué alegría! | Youpiii ! Je suis trop content ! Quelle joie ! |
| `sad` | Triste | Triste | "Oh no... I am a little sad... will you give me a hug?" | MEDIUM (the invitation to help is lost) | Oh, no… estoy un poco triste… ¿me das un abrazo? | Oh non… je suis un peu triste… tu me fais un câlin ? |
| `angry` | Enfadado | Fâché | "Hmph! I'm a bit grumpy... let's take a deep breath together: whooosh!" (the calming breath is the teaching point) | MEDIUM | ¡Uf! Estoy un poco enfadado… vamos a respirar hondo: fuuuuh. | Grrr ! Je suis un peu fâché… on respire fort ensemble : fffouuuh ! |
| `surprised` | Sorprendido | Surpris | "Oooooh! What is that?! Such an amazing surprise!" | MEDIUM | ¡Ooooh! ¿Qué es eso? ¡Qué sorpresa tan increíble! | Ooooh ! Qu'est-ce que c'est ?! Quelle surprise incroyable ! |
| `silly` | Gracioso | Rigolo | "Ahaha! Let's make silly faces! Bleeeeh!" | MEDIUM | ¡Jajaja! ¡Vamos a hacer muecas! ¡Bleeeh! | Hahaha ! On fait des grimaces ! Bleeeh ! |
| `sleepy` | Con sueño | Endormi | "Yawn... so sleepy... let's take a nap..." | MEDIUM | Aaah… qué sueño… vamos a echar una siestecita… | Aaah… j'ai sommeil… on fait une petite sieste… |

Owner choice: the one-word labels ("Feliz") could be kept on purpose as
emotion names, but then `comfort`, `sad` and `angry` lose their reaction and
teaching content, and Momo stops speaking in character in ES/FR only. The
recommendation is the faithful lines above. Momo's adjectives are masculine
because Momo is masculine in the IT originals ("felicissimo"); this describes the
character, not the child.

### 4.6 il_giardino_dei_numeri

| Cue | ES now | FR now | Intended | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `intro` | ¡Vamos a recoger flores en el jardín! | Cueillons des fleurs dans le jardin ! | First round: the child touches each garden object (only some are flowers) and counts. EN/IT: "Hi! Touch and count with me!" | HIGH | ¡Hola! ¡Toca y cuenta conmigo! | Coucou ! Touche et compte avec moi ! |

### 4.7 bosco_numeri (speaker: Tito)

| Cue | ES now | FR now | Intended | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `intro` | ¡Bienvenido al bosque de los números! | Bienvenue dans la forêt des nombres ! | Tito's opening (`_enter_step(opening="intro")`): "Hi, I'm Tito! Let's count to ten together in the forest!" | HIGH (task lost) + GENDER (ES) | ¡Hola, soy Tito! ¡Vamos a contar hasta diez en el bosque! | Salut, moi c'est Tito ! Comptons ensemble jusqu'à dix dans la forêt ! |

`mode_count` ("¡Cuenta los animalitos!" / "Compte les animaux !") and `mode_guess` have no caller (§8).

### 4.8 quattro_stagioni (speaker: Tito)

As for faccine_momo, the ES/FR clips (`assets/audio/{es,fr}/`) replace the EN/IT
lines (`locales/{en,it}/audio/`). `tree_audio.py` documents "the four season lines,
the four weather lines". ES/FR currently say only the bare word, which the
on-screen banner already shows.

| Cue | ES now | FR now | Intended (EN/IT) | Sev. | Proposed ES | Proposed FR |
|---|---|---|---|---|---|---|
| `welcome` | ¡El gran árbol de las estaciones! | Le grand arbre des saisons ! | "Hi! Look at my big tree! Let's play together!" | MEDIUM | ¡Hola! ¡Mira mi gran árbol! ¿Jugamos? | Salut ! Regarde mon grand arbre ! On joue ensemble ? |
| `spring` | Primavera | Printemps | "In spring, lots of colorful flowers bloom!" | MEDIUM | ¡En primavera florecen muchas flores de colores! | Au printemps, plein de petites fleurs colorées éclosent ! |
| `summer` | Verano | Été | "It's summer! The tree has green leaves and sweet apples!" | MEDIUM | ¡Es verano! ¡El árbol tiene hojas verdes y manzanas dulces! | C'est l'été ! L'arbre a des feuilles vertes et des pommes sucrées ! |
| `autumn` | Otoño | Automne | "In autumn the leaves turn red and fall down: swoosh swoosh!" | MEDIUM | En otoño las hojas se ponen rojas y caen: ¡fris, fras! | En automne, les feuilles deviennent rouges et tombent : frou, frou ! |
| `winter` | Invierno | Hiver | "In winter there is snow! Let's make a snowman together!" | MEDIUM | ¡En invierno hay nieve! ¡Hagamos un muñeco de nieve! | En hiver, il y a de la neige ! Faisons un bonhomme de neige ensemble ! |
| `sun` | Sol | Soleil | "Such a warm sun! Shining high in the sky!" | MEDIUM | ¡Qué sol tan calentito! ¡Brilla alto en el cielo! | Quel bon soleil tout chaud ! Il brille haut dans le ciel ! |
| `rain` | Lluvia | Pluie | "It's raining! Plip plop! Let's put on our boots!" | MEDIUM | ¡Llueve! ¡Plic, ploc! ¡Pongámonos las botas! | Il pleut ! Plic ploc ! Mettons nos bottes ! |
| `wind` | Viento | Vent | "Whoosh, what wind! Blowing strong and making leaves dance!" | MEDIUM | ¡Uuuh, qué viento! ¡Sopla fuerte y hace bailar las hojas! | Whouuu, quel vent ! Il souffle fort et fait danser les feuilles ! |
| `snow` | Nieve | Neige | "It's snowing! Soft and white snowflakes!" | MEDIUM | ¡Nieva! ¡Copos de nieve suaves y blancos! | Il neige ! Des flocons tout doux et tout blancs ! |

`day` and `night` have no caller (§8).

### 4.9 mondo_contrari (speaker: Flash)

The ten concept cues (`up` … `slow`) are one-word labels in ES/FR and
exclamations in EN/IT. `contrari_audio.py` calls them "the ten concept words", so
the labels match the code: **no change proposed**. Only `welcome` (gender, §5.1).

## 5. Gendered wording

### 5.1 ES/FR rows (READY in the live run)

| Path | Now | Problem | Proposed |
|---|---|---|---|
| `luci_di_momo/…/es/welcome.wav` | ¡Bienvenido al jardín de las luces! | masculine "Bienvenido" to the child | see §4.1 |
| `specchi_magici/…/es/welcome.wav` | ¡Bienvenido a los espejos mágicos! | same | see §4.2 |
| `bosco_numeri/…/es/intro.wav` | ¡Bienvenido al bosque de los números! | same | see §4.7 |
| `mondo_contrari/…/es/welcome.wav` | ¡Bienvenido al mundo de los contrarios! | same | ¡Hola! ¡Vamos a jugar con los contrarios! ¡Es muy divertido! |
| `mondo_contrari/…/fr/welcome.wav` | Bienvenue dans le monde des contraires ! | neutral (noun), but loses the EN/IT invitation; optional | Salut ! On joue avec les contraires ? C'est trop rigolo ! |
| `colline_allegre/…/fr/made_it_picnic.wav` | Tu es arrivé au pique-nique ! | past participle agrees with the child | Te voilà au pique-nique ! |
| `quattro_amici/…/fr/i_stopped_you.wav` | Je t'ai bloqué ! | participle agrees with the child ("te") | Je t'ai barré la route ! |
| `sottomarino_giramondo/audio/es/sub_order_compliment.wav` | ¡Buena maniobra, capitán! ¡Rumbo fijado! | addresses the child as "capitán" (FR "capitaine" is epicene and fine) | ¡Buena maniobra! ¡Rumbo fijado! |
| `luci_di_momo/…/{es,fr}/prompt_ready.wav` | ¿Listo? / Prêt ? | gendered; no caller | see §4.1 |

LOW (title or object, not a direct address; owner choice):

| Path | Now | Note | Optional |
|---|---|---|---|
| `sottomarino_giramondo/audio/es/sub_title.wav` and `sottomarino_giramondo/locales/es/audio/activity-title.wav` | Explorador submarino | masculine role noun as the title (FR already uses "Exploration en sous-marin") | Exploración submarina |
| `workshop_settings/…/{es,fr}/pick_your_friend.wav` | ¡Elige a tu amigo! / Choisis ton ami ! | plays on the "me" tab; the companion may be female (Lilli) | ¡Elige quién te acompaña! / Choisis qui t'accompagne ! |
| `luci_di_momo/…/es/count_together.wav`, `pasticceria_magica/…/es/count_together.wav` | Contémoslas juntos. / Contemos juntos. | generic masculine plural including the child | Vamos a contarlas. / Vamos a contar. |
| `treno_numeri/…/es/all_aboard.wav` | ¡Todos a bordo! | fixed idiom, generic masculine plural | keep, or ¡Al tren! |

### 5.2 Same-rule problems in EN/IT (outside the ES/FR scope; reported because they are in the same run)

READY in the live plan:

| Path | Now | Proposed |
|---|---|---|
| `bosco_numeri/assets/audio/it/well_done.wav` | Esatto! Bravissimo! | Esatto! Ottimo lavoro! |
| `il_giardino_dei_numeri/assets/audio/it/praise_1.wav` | Bravissimo! | Evviva! |
| `alfabeto_leo/assets/audio/it/well_done.wav` (no caller) | Esatto! Bravissimo! | drop, or Esatto! Ottimo lavoro! |
| `colline_allegre/assets/audio/it/made_it_picnic.wav` | Sei arrivato al picnic! | Eccoti al picnic! |
| `quattro_amici/assets/audio/it/i_stopped_you.wav` | Ti ho fermato! | Ti ho sbarrato la strada! |
| `sottomarino_giramondo/audio/it/sub_order_compliment.wav` | Ottima manovra, capitano! Rotta perfetta! | Ottima manovra! Rotta perfetta! |
| `enciclopedia_greia/assets/audio/it/home/welcome.ogg` | Benvenuto! Qui ci sono tante cose da scoprire. … | Ciao! Qui ci sono tante cose da scoprire. … |
| `assets/audio/characters/shared/v0.2/_intros/it/tito.ogg` | Ciao, esploratore! Io sono Tito! … | Ciao! Io sono Tito! … (ES/FR already drop "explorer") |
| `workshop_settings/assets/audio/it/pick_your_friend.wav` (LOW) | Scegli il tuo amico! | Scegli chi ti accompagna! |

BLOCKED EN/IT rows whose authored originals (078812efb^) are gendered, for the
session that resolves those texts:

| Cue | Authored IT | Proposed IT |
|---|---|---|
| `specchi_magici/…/it/retry_2.wav` | Riprova, sei quasi riuscito! | Riprova, ci sei quasi! |
| `luci_di_momo/…/it/prompt_ready.wav` (no caller) | Tocca il grande pulsante quando sei pronto … | drop |

Also for that session: the authored EN/IT `bottega_delle_misure.prompt_measure`
("Count how many blocks long the parcel is and tap the number!") no longer
matches the code, which plays it before any block is laid ("measure the parcel").

## 6. Systemic: enciclopedia_greia narration (199 cues × ES + FR)

EN/IT `assets/audio/<lang>/**/*.ogg` are the spoken **narration** (1–3 sentences
of facts or instructions, `caption_key: null`). The ES/FR rows are the **on-screen
caption strings** from `locales/{es,fr}.json` (for example `bee.food` = "Néctar y
polen"). `es.json`/`fr.json` declare no audio paths; the resolver maps the English
filename template to `assets/audio/<lang>/…`, so these caption-texts are what
plays.

Effect: an ES/FR child hears a short title instead of the narrated fact. Each
world intro (`animals/intro`, `body/intro`, `earth/intro`, `history/intro`,
`machines/intro`, `space/intro`) says only the world name ("Animales") and loses
the instruction "touch the one you want to look at"; `home/welcome` says "¿Qué
quieres descubrir?" without the "choose a world and touch" guidance.

This is an owner decision, not a wording fix:

- **A (recommended):** translate the EN/IT narration into ES/FR (199 × 2 lines,
  with a native factual review) and plan them as new READY rows;
- **B:** keep caption-voicing, but rewrite at least the 7 navigation intros
  (`home/welcome` and the six world intros) as instructions;
- **C:** keep as is and accept that ES/FR are shorter.

The full row list (EN meaning next to the current ES/FR) is in Appendix A. Topic
intros are listed first.

## 7. Owner decisions needed

1. **Grammatical gender of "Greia".** ES is consistently feminine ("Mi Greia",
   "Tu Greia está lista", "¡Esta es tu Greia!"). FR mixes "Mon Greia"
   (launcher `my_greia`, workshop_settings title) with "Ta Greia est prête",
   "Cette Greia est toute neuve", "Voici ta Greia !". IT mixes "Mio Greia" /
   "Questo è il tuo Greia" with "La Mia Greia" / "La tua Greia è pronta".
   Pick one gender per language. The rest of the corpus suggests feminine in
   all three: FR `my_greia` → "Ma Greia", workshop FR title → "Ma Greia";
   IT `my_greia` → "La mia Greia", `this_is_your_greia` → "Questa è la tua Greia!".
2. **French "Bravo !".** It is an invariable interjection in French (neutral),
   but PRE_READER_UX §4.1 lists "Bravo!" by name. It appears as `correct_1` /
   `praise_1` in luci_di_momo, bottega_delle_misure, casa_del_dieci,
   faccine_momo, mondo_contrari, quattro_stagioni, specchi_magici and as
   `sillabe_magiche/…/fr/bravo.wav`. Either confirm that FR "Bravo !" is allowed
   (and say so in §4.1), or replace it with "Super !" / "Génial !".
3. **ES generic masculine plurals that include the child** ("juntos", "todos"):
   keep as standard Spanish, or neutralise (§5.1 LOW).
4. **faccine_momo** (§4.5) and **quattro_stagioni** (§4.8): faithful character
   lines (recommended) or deliberate one-word labels.
5. **enciclopedia_greia** (§6): option A, B or C.

## 8. ES/FR READY cues with no caller in current code

Recording these costs run time and adds nothing a child can hear. Recommend
leaving them out of the correction plan (and, separately, deciding whether to
delete the files):

| Activity | Cues |
|---|---|
| luci_di_momo | `prompt_ready` |
| bottega_delle_misure | `prompt_order_height`, `prompt_order_length`, `prompt_shelf` |
| bosco_numeri | `mode_count`, `mode_guess` |
| alfabeto_leo | `intro`, `guess_prompt`, `mode_guess_intro`, `well_done` (the module also has no `try_again` cue caller; only the `TRY_AGAIN` state) |
| festa_delle_rime | `prompt_sound` |
| officina_dei_suoni | `prompt_build`, `prompt_find`, `prompt_initial` (ES/FR only) |
| quattro_stagioni | `day`, `night` |

Checked by searching each Activity's `*.py` for the cue id, including f-string
prefixes and locale JSON audio maps. Cues reached through f-strings or JSON
(`prompt_compose_<n>`, sillabe `find_<syllable>`, sottomarino `sub_*`,
stelle/viaggio curiosities, baia `find/feed/jump_<orca>`) were confirmed to be
reachable and are not listed.

## 9. How to apply after the live run

1. Owner approves or edits the proposed texts (§4–§7).
2. Wait until `tools/regenerate_voice_corpus.py` finishes or is restored; do not
   touch the frozen `plan.json` / `state.sqlite3`.
3. Make a deliberate new plan that covers only the approved cue paths, with the
   approved text and the normal character `delivery_prompt`
   (`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` §2). Leave the §8 cues out
   unless the owner wants them. Include the 28 Specchi Magici ES/FR rows from
   §4.2.1 with `speaker=lilli` and Lilli's delivery prompt, even those whose
   text does not change.
4. New takes get listening-pending receipts and need fresh human acceptance,
   like the rest of the regenerated corpus.
5. Update the matching locale JSON captions where the visible text should
   follow the new spoken line (enciclopedia option A/B, quattro_stagioni if
   captions exist).

## Appendix A — enciclopedia_greia ES/FR rows (current text vs EN narration)

EN is truncated at 160 characters. Path: `activities/enciclopedia_greia/assets/audio/<lang>/<cue>.ogg`.

| Cue (`…/<lang>/<cue>.ogg`) | EN narration (owner-accepted meaning) | ES now | FR now |
|---|---|---|---|
| `animals/bee_intro` | Look at the bee among the flowers! It searches for nectar and pollen and, by flying from flower to flower, can help plants reproduce. | ¡Sigue el polen de flor en flor! | Suis le pollen de fleur en fleur ! |
| `animals/elephant_intro` | Here is the elephant! Its trunk is strong and delicate, its large ears help it cool down, and touch is also part of elephant communication. | ¡Toca los símbolos y descubre la trompa! | Touche les symboles pour découvrir sa trompe ! |
| `animals/frog_intro` | Frogs are amphibians and can change enormously as they grow. Follow one very common transformation: from egg to tadpole and then to a little frog! | ¡Sigue la transformación del renacuajo en rana! | Suis la transformation d'un têtard en grenouille ! |
| `animals/intro` | Let's meet the animals! Touch the one you want to look at more closely. | Animales | Animaux |
| `animals/lion_intro` | Here is the lion! Look at its mane, strong front legs, and mighty roar. Touch the symbols and discover how it lives. | ¡Toca los símbolos y descubre al león! | Touche les symboles pour découvrir le lion ! |
| `animals/octopus_intro` | Look at this octopus! It has eight soft arms covered in suckers. Touch it and discover its tricks! | ¡Toca los símbolos y descubre los trucos del pulpo! | Touche les symboles pour découvrir les astuces de la pieuvre ! |
| `animals/penguin_intro` | A penguin is a bird that does not fly through the air: its wings have become powerful flippers for swimming. Touch the symbols and let's dive in! | ¡Sumérgete y descubre cómo vive un pingüino! | Plonge pour découvrir la vie d'un manchot ! |
| `body/bones_intro` | Under your skin is your skeleton. Bones support your body, work with muscles to help you move, and some protect important organs. | ¡Descubre el esqueleto que hay bajo tu piel! | Découvre le squelette sous ta peau ! |
| `body/heart_intro` | Your heart is a muscle about the size of your fist. It keeps working to pump blood around your whole body. | ¡Toca los símbolos y observa cómo trabaja el corazón! | Touche les symboles et observe le cœur au travail ! |
| `body/intro` | Your body does so many things! Touch a part and let's discover how it works. | Mi cuerpo | Mon corps |
| `body/lungs_intro` | Your lungs are two soft organs in your chest. When you breathe, air moves in and out, and inside the lungs your blood picks up oxygen and leaves carbon dioxide… | ¡Respira y observa qué ocurre en tu pecho! | Respire et observe ce qui se passe dans ta poitrine ! |
| `body/senses_intro` | Your body collects information in many ways. Eyes, ears, nose, mouth, and sensory nerves send signals to your brain, which uses them to build what you see, hea… | Tu cuerpo capta señales y el cerebro las interpreta | Ton corps reçoit des signaux que ton cerveau interprète |
| `body/teeth_intro` | Your teeth do not all have the same shape. Front teeth cut, canines help grip and tear, and broad molars crush and grind food. | ¡Cada tipo de diente tiene un trabajo! | Chaque dent a son rôle ! |
| `earth/intro` | Earth is full of things to explore! Touch the sky, the water, a plant, or a rock and let's see what happens. | Tierra y naturaleza | Terre et nature |
| `earth/ocean_intro` | The ocean covers more than seventy percent of Earth. Pacific, Atlantic, Indian, Arctic, and Southern are names for large regions, but all that water forms one … | ¡Desciende desde la superficie hasta las profundidades del océano! | Descends de la surface jusqu'aux profondeurs de l'océan ! |
| `earth/rain_intro` | Water on Earth is always on the move. The Sun can make water evaporate, clouds can form above, and water can come back down as rain. | ¡Sigue el viaje de una gota de agua! | Suis le voyage d'une goutte d'eau ! |
| `earth/rainbow_intro` | A rainbow appears when sunlight meets many water droplets in the air and we look from the right position. Let's place the Sun, rain, and observer in the right … | ¡Coloca el Sol, la lluvia y al observador en los lugares correctos! | Place le Soleil, la pluie et l'observateur au bon endroit ! |
| `earth/tree_intro` | A tree continues below the ground. Its roots anchor it and absorb water and minerals, while its leaves use sunlight to make food for the tree. | ¡Descubre qué sucede por encima y por debajo del suelo! | Découvre ce qui se passe au-dessus et au-dessous de la terre ! |
| `earth/volcano_intro` | Inside a volcano there can be melted rock called magma. Touch the magma chamber and let's see how an eruption can begin! | ¡Toca los símbolos y haz que el volcán cobre vida! | Touche les symboles et donne vie au volcan ! |
| `history/cave_paintings_intro` | A very long time ago, people in many parts of the world made images on cave walls and rock shelters. Some have survived for tens of thousands of years. | ¡Ilumina la pared y explora marcas hechas hace muchísimo tiempo! | Éclaire la paroi et explore des traces laissées il y a très longtemps ! |
| `history/dinosaurs_intro` | Dinosaurs were not all alike. Some were small and some enormous, some walked on two legs or four, and they included plant-eaters and meat-eaters. Let's travel … | ¡Descubre lo diferentes que podían ser los dinosaurios! | Découvre à quel point les dinosaures pouvaient être différents ! |
| `history/fossils_intro` | Under these layers there may be a clue from ancient life. Use the brush and discover what has lasted through time! | ¡Descubre pistas escondidas bajo el suelo! | Découvre les indices cachés sous la terre ! |
| `history/intro` | Let's take a journey into the past! Touch a scene and we'll see what it was like long ago. | Hace mucho tiempo | Autrefois |
| `history/mammoth_intro` | This is a woolly mammoth, an extinct relative of elephants. It lived in cold environments and had several body adaptations that helped conserve heat. | ¡Descubre un antiguo pariente de los elefantes adaptado al frío! | Découvre un ancien parent des éléphants adapté au froid ! |
| `history/pyramids_intro` | The pyramids of ancient Egypt are enormous stone monuments built by people thousands of years ago. Many were created as royal tombs within larger funerary comp… | ¡Descubre cómo grandes grupos de personas construyeron enormes monumentos de piedra! | Découvre comment des équipes ont construit d'immenses monuments en pierre ! |
| `home/welcome` | Welcome! There are so many things to discover here. Choose a world and touch whatever makes you curious! | ¿Qué quieres descubrir? | Que veux-tu découvrir ? |
| `machines/airplane_intro` | Ready for takeoff! An airplane flies because several forces work together. Its wings interact with moving air to produce lift, while an engine or propeller pro… | ¿Cómo vuela un avión? ¡Descubre las alas, el motor, los controles y las nubes del cielo! | Comment vole un avion ? Découvre les ailes, le moteur, les commandes de vol et les nuages dans le ciel ! |
| `machines/bicycle_intro` | Go! When you turn the pedals, you turn the crank and front chainring. The chain carries that motion to the gear on the rear wheel. | ¡Gira los pedales y sigue el movimiento hasta la rueda! | Tourne les pédales et suis le mouvement jusqu'à la roue ! |
| `machines/bridge_intro` | Bridge ready! A bridge does more than stay still. It must carry its own weight and whatever travels across it, then transfer those forces to its supports and t… | ¿Cómo aguanta un puente tanto peso? ¡Descubre cómo transmite las cargas de coches y camiones hasta el suelo! | Comment un pont supporte-t-il un poids si lourd ? Découvre comment les charges des voitures et camions passent jusqu'au sol ! |
| `machines/gears_intro` | Gears ready! Their teeth mesh together and pass motion from one wheel to the next. Try turning them! | ¡Toca los símbolos y haz funcionar el mecanismo! | Touche les symboles et fais bouger le mécanisme ! |
| `machines/intro` | Workshop ready! Touch a machine or an experiment and let's discover what makes it work. | Ciencia y máquinas | Sciences et machines |
| `machines/magnet_intro` | Magnet detected! Every magnet has two poles. Different poles attract, while matching poles repel even without touching. | ¡Descubre los polos magnéticos, cómo se atraen o se repelen y cómo orientan las brújulas en la Tierra! | Découvre les pôles magnétiques, comment ils s'attirent ou se repoussent et comment ils guident les boussoles sur Terre ! |
| `space/earth_intro` | This is our home seen from space: Earth, the third planet from the Sun. It is a rocky world with oceans, air, and life. | ¡Mira nuestro hogar desde el espacio! | Regarde notre maison depuis l'espace ! |
| `space/intro` | Look up there! Let's explore space. Touch the Sun, a planet, or the Moon to move closer. | Espacio | Espace |
| `space/jupiter_intro` | Here is Jupiter, the largest planet in the solar system! It is a gas giant full of clouds, bands, and storms. | ¡Descubre el planeta más grande! | Découvre la plus grosse planète ! |
| `space/mars_intro` | This is Mars, the red planet. Its soil contains iron minerals that oxidized, a little like rust, helping give the surface its special color. | ¡Descubre por qué Marte es el planeta rojo! | Découvre pourquoi Mars est la planète rouge ! |
| `space/mercury_intro` | This small world is Mercury, the planet closest to the Sun. It is the smallest major planet, and it races around the Sun very quickly. | ¡Descubre el pequeño planeta más cercano al Sol! | Découvre la petite planète la plus proche du Soleil ! |
| `space/moon_intro` | Here is the Moon, Earth's natural satellite. It travels around Earth and shows us almost the same face, but the Moon really does spin on its axis too. | ¡Descubre la compañera de la Tierra! | Découvre la compagne de la Terre ! |
| `space/neptune_intro` | Here is Neptune, the eighth and most distant major planet. It is a cold blue ice giant with incredibly powerful winds. | ¡Descubre el planeta principal más lejano! | Découvre la planète principale la plus éloignée ! |
| `space/saturn_intro` | Here is Saturn, the giant with rings! Touch the planet and its rings to discover what they are made of. | ¡Toca los símbolos y descubre el gigante de los anillos! | Touche les symboles et découvre la géante aux anneaux ! |
| `space/sun_intro` | This is our star: the Sun! It is a gigantic ball of extremely hot plasma, and its gravity helps hold the solar system together. | ¡Toca los símbolos y descubre nuestra estrella! | Touche les symboles pour découvrir notre étoile ! |
| `space/uranus_intro` | This is Uranus, an ice giant that appears to spin almost on its side. It is one of the strangest-looking worlds in the solar system. | ¡Descubre el gigante que gira casi tumbado de lado! | Découvre la géante qui tourne presque sur le côté ! |
| `space/venus_intro` | This is Venus. From far away it looks wrapped in calm clouds, but beneath those clouds is an extremely hot rocky world. | ¡Descubre lo que esconden las nubes! | Découvre ce qui se cache sous les nuages ! |
| `animals/bee_food` | Flowers offer two important foods: nectar is rich in sugars, while pollen contains important nutrients for bees. | Néctar y polen | Nectar et pollen |
| `animals/bee_homes` | Not all bees live in a hive. Most wild bees live alone, while honey bees live together in large colonies. | No todas las abejas viven en colmenas | Toutes les abeilles ne vivent pas dans une ruche |
| `animals/bee_pollen` | When a bee visits a flower, some pollen can stick to its body. At the next flower, some of that pollen can be transferred. | El polen viaja con las abejas | Le pollen voyage avec les abeilles |
| `animals/bee_pollination` | This movement of pollen is called pollination. For many plants it is an important step in making new seeds and fruits. | El polen ayuda a las plantas a reproducirse | Le pollen aide les plantes à se reproduire |
| `animals/elephant_ears` | Large elephant ears contain many blood vessels. Flapping them can help move heat away and cool the elephant. | Las orejas ayudan a refrescarse | Les oreilles aident à se rafraîchir |
| `animals/elephant_social` | Elephants are very social animals. They often touch with their trunks to greet, explore, and communicate. | Se tocan para comunicarse | Se toucher pour communiquer |
| `animals/elephant_trunk` | The trunk combines the nose and upper lip. It is packed with muscles and is used to smell, touch, pick up food, and move objects. | Una trompa fuerte y precisa | Une trompe forte et précise |
| `animals/elephant_water` | An elephant draws water into its trunk and then squirts it into its mouth to drink. It can also use the trunk for bathing. | Agua con la trompa | De l'eau avec la trompe |
| `animals/frog_cycle` | In one very common life cycle, an egg hatches into a tadpole that lives in water. As it grows, it becomes a froglet and then an adult frog. | Huevo, renacuajo, ranita, rana | Œuf, têtard, jeune grenouille, grenouille |
| `animals/frog_metamorphosis` | This big transformation is called metamorphosis. In the classic cycle, the tadpole grows legs and lungs while its tail becomes smaller and smaller. | La metamorfosis transforma el cuerpo | La métamorphose transforme le corps |
| `animals/frog_skin` | Frog skin is moist and permeable and also helps with breathing. That is why water and moisture are very important for many amphibians. | Piel húmeda y permeable | Une peau humide et perméable |
| `animals/frog_variety` | But not every frog grows in exactly the same way! Many use water and tadpoles, while others lay eggs in very different moist nurseries. | No todas las ranas crecen igual | Les grenouilles ne grandissent pas toutes de la même façon |
| `animals/lion_forelegs` | A lion has very strong front legs. Together with its compact body, they help it move and grip powerfully. | Fuertes patas delanteras | De puissantes pattes avant |
| `animals/lion_mane` | Many adult male lions have a large mane around the head and neck. Its color and size can vary from one lion to another. | Melenas diferentes | Des crinières différentes |
| `animals/lion_pride` | Lions are the most social cats. They often live in groups called prides, where several lions stay connected and raise their young. | Los leones suelen vivir en manadas | Les lions vivent souvent en groupes |
| `animals/lion_roar` | A roar helps lions communicate and signal their territory. It is so powerful that it can be heard from very far away. | Un rugido que se oye desde lejos | Un rugissement qui porte loin |
| `animals/octopus_arms` | An octopus has eight arms, not tentacles. Suckers along its arms help it touch and hold things. | Ocho brazos con ventosas | Huit bras munis de ventouses |
| `animals/octopus_camouflage` | Many octopuses can change the color and pattern of their skin very quickly. That helps them blend into their surroundings. | Cambia de color para camuflarse | Elle change de couleur pour se camoufler |
| `animals/octopus_hearts` | Surprise: an octopus has three hearts! Two send blood to the gills, and one sends it around the rest of the body. | ¡Tres corazones! | Trois cœurs ! |
| `animals/octopus_ink` | When danger comes, many octopuses can release a cloud of ink and escape while the predator is confused. | Una nube de tinta para escapar | Un nuage d'encre pour s'échapper |
| `animals/penguin_breeding` | Many penguin species gather in colonies to breed, but they do not all make the same kind of nest. Emperor and king penguins even keep the egg on top of their f… | Colonias y cuidados de los huevos muy distintos | Des colonies et des soins aux œufs très variés |
| `animals/penguin_feathers` | A penguin has many short overlapping feathers that help keep water out. Feathers and a layer of body fat also help hold in heat. | Plumas superpuestas que aíslan del frío | Des plumes superposées qui protègent du froid |
| `animals/penguin_swim` | Underwater, a penguin's flippers push it forward while its feet and tail help it steer. | Las aletas impulsan; las patas y la cola dirigen | Les ailes propulsent ; les pattes et la queue dirigent |
| `animals/penguin_world` | Not every penguin lives on ice! Penguins live in the Southern Hemisphere, but some species live in temperate or even very warm places. | No todos los pingüinos viven sobre hielo | Tous les manchots ne vivent pas sur la glace |
| `body/bones_joints` | Joints are places where two or more bones meet. Some, like your elbow, mostly bend one way, while others, like your shoulder, can move in many directions. | Distintas articulaciones permiten movimientos diferentes | Différentes articulations permettent différents mouvements |
| `body/bones_living` | Bones are not dead, unchanging pieces. They are living tissue. They grow during childhood, and your body keeps renewing small parts of bone throughout life. | Los huesos son tejido vivo que crece y cambia | Les os sont des tissus vivants qui grandissent et changent |
| `body/bones_marrow` | Inside some bones is bone marrow. In this soft tissue, your body makes new blood cells. | La médula ósea produce nuevas células de la sangre | La moelle osseuse fabrique de nouvelles cellules sanguines |
| `body/bones_protect` | Some bones also act like shields. Your skull protects your brain, and your ribs surround and help protect your heart and lungs. | El cráneo y las costillas ayudan a proteger órganos importantes | Le crâne et les côtes protègent des organes importants |
| `body/heart_beat` | Each heartbeat is a squeeze that pumps blood. Valves close and help make the familiar sound: lub-dub! | ¡Tum-tum! | Boum-boum ! |
| `body/heart_chambers` | Inside the heart there are four chambers. The two on top receive blood, and the two below pump it out of the heart. | Cuatro cavidades | Quatre cavités |
| `body/heart_circulation` | One side of the heart sends blood to the lungs to pick up oxygen. Then the other side pumps it out to the rest of the body. | Del corazón a los pulmones y al resto del cuerpo | Du cœur vers les poumons et le reste du corps |
| `body/heart_exercise` | When you run or play energetically, your heart beats faster to bring more oxygen to your muscles. | Late más deprisa cuando corres | Il bat plus vite quand tu cours |
| `body/lungs_airways` | Air travels from your nose or mouth into the airways. Inside your lungs, the tubes branch into smaller and smaller passages until they reach tiny air sacs. | Las vías respiratorias se ramifican en conductos más pequeños | Les voies respiratoires se divisent en petits conduits |
| `body/lungs_breath` | To breathe in, the diaphragm below your lungs contracts and moves downward, making more room in your chest. When it relaxes, the space becomes smaller and air … | El diafragma y el pecho se mueven para que entre y salga aire | Le diaphragme et la cage thoracique bougent pour faire entrer et sortir l'air |
| `body/lungs_exchange` | In tiny air sacs called alveoli, oxygen moves from the air into your blood. At the same time, carbon dioxide moves from the blood into the air and is then brea… | El oxígeno entra en la sangre y el dióxido de carbono sale | L'oxygène entre dans le sang, tandis que le dioxyde de carbone en sort |
| `body/lungs_exercise` | When you run or play energetically, your muscles use more oxygen and make more carbon dioxide. That is why you usually breathe faster and more deeply. | Al correr, respiras más rápido y más profundamente | Quand tu cours, tu respires plus vite et plus profondément |
| `body/senses_flavor` | Sweet, sour, salty, bitter, and umami can be sensed across many parts of the tongue; the famous tongue taste map is wrong. When you eat, taste and smell also w… | El gusto y el olfato trabajan juntos; no existe un mapa de sabores en la lengua | Le goût et l'odorat travaillent ensemble : la langue n'a pas de carte des saveurs |
| `body/senses_hearing` | Sound waves make your eardrum and tiny ear bones vibrate. In the inner ear, those vibrations are turned into signals that the auditory nerve carries to your br… | Las vibraciones se convierten en señales que llegan al cerebro | Les vibrations deviennent des signaux envoyés vers le cerveau |
| `body/senses_sight` | Light enters your eye and reaches the light-sensitive retina. The retina turns light into electrical signals that travel along the optic nerve to your brain. | La retina transforma la luz en señales para el cerebro | La rétine transforme la lumière en signaux pour le cerveau |
| `body/senses_touch` | Sensory nerves carry information such as touch, pressure, and temperature to your brain. Different people can experience the world in somewhat different ways, … | Los nervios transportan información del tacto, la presión y la temperatura | Les nerfs transmettent les sensations de toucher, de pression et de température |
| `body/teeth_care` | Gently brushing all sides of your teeth helps remove plaque. Fluoride toothpaste helps make enamel more resistant to tooth decay. | El cepillado suave y el flúor ayudan a proteger los dientes | Un brossage doux et le fluor aident à protéger les dents |
| `body/teeth_jobs` | Incisors have an edge suited for cutting. Canines are more pointed. Molars have broad surfaces that help crush and chew food. | Los incisivos cortan, los caninos sujetan y los molares trituran | Les incisives coupent, les canines saisissent et les molaires broient |
| `body/teeth_layers` | The visible part of a tooth is covered by enamel, a very hard layer that protects it. Deeper inside are dentin and pulp, where nerves and blood vessels are fou… | Esmalte por fuera y otros tejidos en el interior | De l'émail à l'extérieur et d'autres tissus à l'intérieur |
| `body/teeth_sets` | Children first have primary, or baby, teeth. A complete set usually has twenty. As you grow, those teeth are gradually replaced by permanent teeth. | Primero salen los dientes de leche y después los definitivos | Les dents de lait arrivent avant les dents définitives |
| `earth/ocean_deep` | The deep ocean is dark, cold, and under enormous pressure, but it is not empty. Many organisms are adapted to live in these deep environments. | Las profundidades son oscuras, pero están llenas de vida | Les profondeurs sont sombres, mais pleines de vie |
| `earth/ocean_light` | Sunlight reaches mainly through the upper ocean. Below about two hundred meters it becomes much weaker, and below roughly one thousand meters sunlight from the… | La luz del Sol disminuye rápidamente con la profundidad | La lumière du Soleil diminue rapidement avec la profondeur |
| `earth/ocean_salt` | Seawater contains many dissolved salts. On average, about thirty-five parts out of every thousand are dissolved salts, although salinity changes from place to … | El agua marina contiene sales disueltas | L'eau de mer contient des sels dissous |
| `earth/ocean_water` | Almost all of Earth's water is in the ocean: about ninety-seven percent. The rest is found mostly in ice, groundwater, lakes, rivers, and the atmosphere. | Un solo océano conectado contiene casi toda el agua de la Tierra | Un seul océan relié contient presque toute l'eau de la Terre |
| `earth/rain_condensation` | When water vapor cools, it can condense into tiny droplets. Clouds are made of huge numbers of tiny water droplets and, when it is cold enough, ice crystals to… | El vapor se enfría y forma gotitas | La vapeur refroidit et forme de petites gouttes |
| `earth/rain_evaporation` | Energy from the Sun can turn some liquid water into invisible water vapor that moves into the atmosphere. This process is called evaporation. | El Sol hace que parte del agua se evapore | Le Soleil fait évaporer une partie de l'eau |
| `earth/rain_ground` | After rain, some water runs downhill toward streams, rivers, and the ocean. Some can soak into the ground and continue its journey underground. | Parte del agua corre por la superficie y otra parte se filtra al suelo | Une partie de l'eau ruisselle, l'autre pénètre dans le sol |
| `earth/rain_precipitation` | Inside clouds, droplets can join and grow. When they become large and heavy enough, water falls toward the ground. Rain is one form of precipitation. | Las gotas crecen y cae la lluvia | Les gouttes grossissent et la pluie tombe |
| `earth/rainbow_circle` | A complete rainbow is actually a circle. From the ground, though, the land and horizon usually hide part of it, so we mostly see an arc. | Un arcoíris completo forma un círculo | Un arc-en-ciel complet forme un cercle |
| `earth/rainbow_colors` | White sunlight contains many colors. Inside the droplet, different colors bend by slightly different amounts, so they reach our eyes separated. | Los colores se separan porque se desvían de forma diferente | Les couleurs se séparent parce qu'elles se courbent différemment |
| `earth/rainbow_droplet` | When light enters a water droplet, it changes direction. Some of it then reflects inside, and the light bends again as it leaves. | La luz se desvía, se refleja y vuelve a desviarse | La lumière se courbe, se réfléchit, puis se courbe encore |
| `earth/rainbow_position` | To see a typical rainbow, the Sun needs to be behind us and water droplets in front. The rainbow we see also depends on where the observer is standing. | El Sol detrás, las gotas delante | Le Soleil derrière, les gouttes devant |
| `earth/tree_photosynthesis` | In the leaves, light energy helps use water and carbon dioxide to make sugars. This process is called photosynthesis, and it also produces oxygen. | La luz, el agua y el dióxido de carbono ayudan a producir azúcares | La lumière, l'eau et le dioxyde de carbone aident à fabriquer des sucres |
| `earth/tree_roots` | Roots have many fine branches that absorb water and minerals from the soil. Larger roots also help hold the tree firmly in place. | Las raíces absorben agua y sujetan el árbol | Les racines absorbent l'eau et ancrent l'arbre |
| `earth/tree_seasons` | Trees do not all change the same way. Many broad-leaved trees lose their leaves in a cold season, while many conifers stay green; in other climates leaves may … | No todos los árboles cambian del mismo modo | Tous les arbres ne changent pas de la même façon |
| `earth/tree_transpiration` | Some water leaves the leaves and enters the air as water vapor. This process is called transpiration, and it is also part of the water cycle. | Las hojas también liberan vapor de agua | Les feuilles rejettent aussi de la vapeur d'eau |
| `earth/tree_water` | Water absorbed by the roots travels upward through the trunk and branches to the leaves. A tree must keep moving water to its living parts. | El agua viaja desde las raíces hasta las hojas | L'eau monte des racines jusqu'aux feuilles |
| `earth/volcano_ash` | In an explosive eruption, magma can break into many fragments. The tiniest pieces form volcanic ash. | Ceniza y fragmentos | Des cendres et des fragments |
| `earth/volcano_magma` | Below the surface it is called magma. When the melted rock comes out onto the surface, it is called lava. | Magma bajo tierra, lava en la superficie | Du magma en profondeur, de la lave à l'extérieur |
| `earth/volcano_style` | If gases can escape easily, lava may flow out. If gas stays trapped in very thick magma, pressure can build and the eruption can be explosive. | Diferentes tipos de erupciones | Différents types d'éruptions |
| `earth/volcano_vent` | Magma can rise and collect beneath a volcano, then push upward through cracks and vents. | El magma asciende por conductos | Le magma monte dans des conduits |
| `history/cave_paintings_hands` | Some sites contain many hand stencils. One way to make them was to hold a hand against the wall while pigment was applied around it, leaving the hand's outline. | Siluetas de manos hechas aplicando pigmento alrededor de los dedos | Des silhouettes de mains obtenues en appliquant des pigments autour des doigts |
| `history/cave_paintings_images` | On these walls we can find animals, hands, human figures, and geometric shapes. We can observe what was painted, but we often do not know exactly what it meant… | Animales, manos, personas y figuras geométricas | Animaux, mains, personnages et formes géométriques |
| `history/cave_paintings_pigments` | Ancient artists could make colors from natural materials, including mineral pigments. Different places and times used different materials and techniques. | Colores obtenidos de materiales naturales y minerales | Des couleurs fabriquées avec des matériaux naturels et minéraux |
| `history/cave_paintings_uncertainty` | Archaeologists gather clues about age, pigments, images, and location, but the exact meaning of many paintings remains unknown. Saying “we don't know yet” is a… | Aún desconocemos el significado exacto de muchas imágenes | Nous ignorons encore la signification exacte de nombreuses images |
| `history/dinosaurs_birds` | But part of the dinosaur story is still alive today: birds are living dinosaurs. When you look at a sparrow or a chicken, you are seeing a surviving branch of … | Las aves son dinosaurios que siguen vivos | Les oiseaux sont des dinosaures encore vivants |
| `history/dinosaurs_diversity` | Look how different they could be. A tyrannosaur walked on two legs and ate meat, Triceratops was a four-legged plant-eater, and sauropods had extremely long ne… | Formas, tamaños y dietas muy distintos | Des formes, tailles et régimes alimentaires très variés |
| `history/dinosaurs_evidence` | Paleontologists reconstruct dinosaurs from fossils such as bones, teeth, footprints, and other clues. Some details, including many skin colors, remain uncertai… | Los fósiles y otras pistas ayudan a reconstruir su aspecto | Les fossiles et d'autres indices aident à reconstituer leur apparence |
| `history/dinosaurs_time` | Non-avian dinosaurs disappeared about sixty-six million years ago. Humans arrived vastly later, so people and tyrannosaurs never lived together. | Los dinosaurios no avianos vivieron mucho antes que los humanos | Les dinosaures non aviens vivaient bien avant les humains |
| `history/fossils_burial` | Being buried quickly by sediment helps preserve remains. Hard parts such as bones, teeth, and shells are more likely to survive. | Quedar enterrado puede ayudar a conservar los restos | L'enfouissement peut aider à préserver les restes |
| `history/fossils_clues` | By studying fossils and rocks, scientists can learn what lived long ago and what those ancient environments were like. | Los fósiles revelan cómo eran los ambientes antiguos | Les fossiles révèlent des milieux anciens |
| `history/fossils_definition` | A fossil is evidence of past life preserved in rock, sediment, or another geologic setting. | Huellas o restos de seres vivos del pasado | Des traces ou des restes de la vie passée |
| `history/fossils_rare` | Becoming a fossil is rare. Fossils are precious clues, but they do not record every living thing from the past. | Convertirse en fósil es poco frecuente | Devenir un fossile est rare |
| `history/fossils_types` | A bone, tooth, or shell can become a body fossil. A footprint or burrow can become a trace fossil. | Fósiles de cuerpos y fósiles de rastros | Fossiles de corps et fossiles de traces |
| `history/mammoth_coat` | The woolly mammoth had a thick coat and a substantial layer of fat under its skin. Together they helped insulate its body from the cold. | Su pelaje espeso y su grasa corporal ayudaban a conservar el calor | Sa fourrure épaisse et sa graisse l'aidaient à garder la chaleur |
| `history/mammoth_ears` | Woolly mammoth ears were relatively small. In a cold climate, having less exposed surface area helps reduce heat loss. | Sus orejas relativamente pequeñas reducían la pérdida de calor | Ses petites oreilles limitaient les pertes de chaleur |
| `history/mammoth_elephants` | Mammoths and elephants belong to the same broad family, but a woolly mammoth was not simply a modern elephant with more hair. It was a distinct species that is… | Mamuts y elefantes son parientes, pero no la misma especie | Mammouths et éléphants sont apparentés, mais ce ne sont pas les mêmes espèces |
| `history/mammoth_time` | Woolly mammoths lived vastly later than the large non-avian dinosaurs and even overlapped with humans. Some isolated populations survived until about four thou… | Los mamuts vivieron mucho después de los dinosaurios y coincidieron con los humanos | Les mammouths ont vécu longtemps après les dinosaures et en même temps que les humains |
| `history/pyramids_blocks` | A great pyramid required huge numbers of prepared stone blocks to be transported and positioned carefully. Our layer-stacking game is only a diagram, not a min… | Muchísimos bloques de piedra preparados y colocados con cuidado | Des quantités énormes de blocs préparés et placés avec soin |
| `history/pyramids_engineering` | Ancient Egyptians used quarries, sledges, ramps, measurement, and extensive organization to move and place stone. Archaeologists reconstruct these methods from… | Canteras, trineos, rampas, mediciones y organización | Carrières, traîneaux, rampes, mesures et organisation |
| `history/pyramids_inside` | Inside and around pyramids were passages, chambers, and other buildings belonging to the funerary complex. Great pyramids were not hollow mountains filled ever… | Pasadizos y cámaras dentro de los complejos funerarios | Des passages et des chambres à l'intérieur des complexes funéraires |
| `history/pyramids_workers` | Pyramids were built by organized teams of people: craftspeople, quarry workers, haulers, masons, and other laborers. Archaeological evidence does not support t… | Equipos organizados de artesanos y trabajadores | Des équipes organisées d'artisans et de travailleurs |
| `machines/airplane_forces` | Four main forces act in flight: lift upward, weight downward, thrust forward, and drag backward. When their balance changes, the airplane's motion changes too. | Altura y nubes: abajo flotan los cúmulos esponjosos; muy arriba, en el frío, aparecen finos cirros. | Altitude et nuages : en bas flottent des cumulus duveteux ; plus haut, dans le froid, apparaissent de fins cirrus. |
| `machines/airplane_lift` | When air flows around a wing, the wing changes the motion of the air and creates a pressure pattern that produces an upward force: lift. | Alas y sustentación: el ala desvía aire hacia abajo y ayuda a levantar el avión. | Ailes et portance : l'aile dévie l'air vers le bas, ce qui aide à soulever l'avion. |
| `machines/airplane_myth` | One important thing: air passing above and below a wing does not have to meet again at the same time behind it. The famous longer-path story does not correctly… | Controles de vuelo: los alerones, el timón y los elevadores ayudan a girar, ascender o descender. | Commandes de vol : ailerons, gouvernail et profondeur aident à tourner, monter ou descendre. |
| `machines/airplane_thrust` | An engine or propeller pushes the airplane forward through the air. The wings do the main lifting work; even an engine-free glider can fly while it moves throu… | Motor y hélice: empujan el avión hacia delante para que el aire fluya alrededor de las alas. | Moteur et hélice : ils poussent l'avion vers l'avant pour faire circuler l'air autour des ailes. |
| `machines/bicycle_drive` | Follow the motion: pedals, chainring, chain, rear sprocket, and finally the wheel. Each part passes motion to the next. | Pedales, plato, cadena y piñón transmiten el movimiento | Pédales, plateau, chaîne et pignon transmettent le mouvement |
| `machines/bicycle_energy` | Gears do not create free energy. They can make it more useful to trade force for motion or motion for force, but there is always a tradeoff. | Los engranajes transforman el movimiento, pero no crean energía | Les engrenages transforment le mouvement, ils ne créent pas d'énergie |
| `machines/bicycle_ratio` | Changing gear sizes changes the ratio. An easier gear needs less force but turns the wheel less for each pedal turn; a harder gear does the opposite. | Los desarrollos cambian las vueltas de rueda y el esfuerzo al pedalear | Les rapports de vitesse font varier les tours de roue et l'effort de pédalage |
| `machines/bicycle_travel` | With the same complete pedal turn, different gear ratios can make the rear wheel turn by different amounts. Gears change the relationship between motion and fo… | La rueda al girar impulsa la bicicleta por el camino | Une roue qui tourne fait avancer le vélo sur la route |
| `machines/bridge_forces` | Some parts of a structure are in compression, meaning they are pushed together. Others are in tension, meaning they are pulled. In a real bridge, the design de… | Los pilares: unas columnas fuertes transmiten las cargas hasta unos cimientos resistentes. | Les piliers : de solides colonnes transmettent les charges à des fondations résistantes. |
| `machines/bridge_load` | When you place a load on a bridge, the force enters through the deck. Connected parts of the bridge transfer it toward the supports at the sides. | La carga: cuando pasan coches y camiones, su peso empuja hacia abajo el tablero del puente. | La charge : quand des voitures et des camions passent, leur poids appuie sur le tablier du pont. |
| `machines/bridge_path` | Follow the arrows: the load passes through connected parts until it reaches the supports. A bridge works as a system of paths for forces. | Los cables: los tirantes de acero sostienen el tablero mediante tensión y ayudan a mantenerlo estable. | Les câbles : des tirants d'acier soutiennent le tablier en tension et l'aident à rester stable. |
| `machines/bridge_shapes` | A beam, an arch, and a truss do not carry a load in the same way. The shape changes the path forces take through the structure. | El arco: su forma curva distribuye el peso hacia los apoyos laterales. | La voûte : sa forme courbe répartit le poids vers les appuis sur les côtés. |
| `machines/gears_direction` | Two gears that mesh turn in opposite directions. If the first turns one way, its neighbor turns the other way. | Los engranajes vecinos giran en sentidos contrarios | Les engrenages voisins tournent en sens opposé |
| `machines/gears_rack` | A round gear can also push a toothed rack and turn spinning motion into straight-line motion. | Del movimiento giratorio al movimiento recto | Du mouvement circulaire au mouvement rectiligne |
| `machines/gears_ratio` | When a large gear drives a small gear, the small one turns faster. When a small gear drives a large gear, the large one turns more slowly. | Grandes y pequeños: velocidades diferentes | Grand et petit : des vitesses différentes |
| `machines/gears_teeth` | The teeth of two gears meet. When one turns, it pushes the teeth of the other and makes it turn. | Los dientes transmiten el movimiento | Les dents transmettent le mouvement |
| `machines/magnet_distance` | Two magnets can pull or push each other even with a small gap between them. Magnetic force acts through the field around the magnet. | Fuerza a distancia: cuanto más cerca están los imanes, más fuerte puede ser su empuje o su atracción invisible. | Une force à distance : plus les aimants se rapprochent, plus leur attraction ou leur répulsion invisible peut devenir forte. |
| `machines/magnet_field` | A magnetic field cannot be seen directly. The lines we draw around a magnet are a useful way to show where and how its force can act. | La Tierra tiene un campo magnético invisible que ayuda a las brújulas a señalar el norte. | La Terre possède un champ magnétique invisible qui aide les boussoles à indiquer le nord. |
| `machines/magnet_materials` | Careful: a magnet does not attract every metal. Iron, nickel, cobalt, and many materials containing them respond strongly; aluminum and copper, for example, do… | Materiales: los imanes atraen el hierro y el acero, pero no la madera, el plástico ni el aluminio. | Matériaux : les aimants attirent le fer et l'acier, mais pas le bois, le plastique ni l'aluminium. |
| `machines/magnet_poles` | Bring a north pole near a south pole and the magnets attract. North facing north, or south facing south, makes them repel instead. | Polos norte y sur: los opuestos (N y S) se atraen y los iguales (N-N o S-S) se repelen. | Pôles nord et sud : les pôles opposés (N et S) s'attirent, les mêmes pôles (N-N ou S-S) se repoussent. |
| `space/earth_life` | Earth is wrapped in an atmosphere of gases. It is also the only world we currently know that has life. | Una atmósfera y vida conocida | Une atmosphère et de la vie connue |
| `space/earth_name` | Earth | Tierra | Terre |
| `space/earth_rotation` | Earth is always turning. The side facing the Sun is lit and has daytime; the side turned away has nighttime. | La rotación produce el día y la noche | La rotation produit le jour et la nuit |
| `space/earth_seasons` | Earth's axis is tilted. As Earth travels around the Sun, that tilt changes how much sunlight each hemisphere receives and creates the seasons. | La inclinación del eje crea las estaciones | L'inclinaison de son axe crée les saisons |
| `space/earth_water` | Most of Earth's surface is covered by water. Almost all of the planet's water is held in the oceans. | Un planeta cubierto de agua en gran parte | Une planète en grande partie couverte d'eau |
| `space/jupiter_day` | Jupiter spins very fast. A day lasts only about ten hours, the shortest day of any planet in the solar system. | El día más corto: unas diez horas | Le jour le plus court : environ dix heures |
| `space/jupiter_gas` | The bands we see are clouds, not continents. Jupiter is a gas giant and does not have a solid surface like Earth. | Nubes sin una superficie sólida como la terrestre | Des nuages, sans surface solide comme celle de la Terre |
| `space/jupiter_name` | Jupiter | Júpiter | Jupiter |
| `space/jupiter_scale` | Jupiter is enormous: it is about eleven Earths wide. If it were a hollow shell, roughly one thousand Earths could fit inside. | Unas once Tierras de ancho | Environ onze fois la largeur de la Terre |
| `space/jupiter_storm` | The Great Red Spot is a gigantic storm in Jupiter's atmosphere. It has lasted a very long time and is still larger than Earth. | La Gran Mancha Roja es una tormenta gigante | La Grande Tache rouge est une tempête géante |
| `space/mars_day` | A day on Mars lasts about twenty-four and a half hours, almost like an Earth day. Martian solar days are called sols. | Su día dura unas 24,6 horas | Une journée dure environ 24,6 heures |
| `space/mars_name` | Mars | Marte | Mars |
| `space/mars_olympus` | Mars is home to Olympus Mons, the largest volcano in the solar system. From its base to its summit it rises more than forty kilometers. | Monte Olimpo: el volcán más grande del sistema solar | Olympus Mons : le plus grand volcan du système solaire |
| `space/mars_red` | Mars is not red because it is burning. Iron-rich minerals in the ground oxidized, so much of the dust and rock looks reddish. | El hierro oxidado vuelve rojizo el suelo | Le fer oxydé rend le sol rougeâtre |
| `space/mars_water` | Mars is cold and very dry today, but ancient valleys, deltas, and lakebeds show that lots of liquid water flowed across its surface billions of years ago. | Antiguos valles revelan un pasado con más agua | D'anciennes vallées révèlent un passé plus humide |
| `space/mercury_craters` | Mercury's surface is covered with craters. And there is a surprise: water ice can survive in polar craters that stay permanently in shadow. | Cráteres, rayos de impacto y hielo en sombras polares | Des cratères, des rayons d'impact et de la glace dans les ombres polaires |
| `space/mercury_name` | Mercury | Mercurio | Mercure |
| `space/mercury_orbit` | Mercury goes around the Sun in only eighty-eight Earth days. Its year is much shorter than ours. | Su año dura 88 días terrestres | Une année y dure 88 jours terrestres |
| `space/mercury_place` | Mercury is the planet closest to the Sun, and it is also the smallest of the eight major planets. | El más cercano al Sol y el más pequeño | La plus proche du Soleil et la plus petite |
| `space/mercury_temperature` | Mercury does not have a thick atmosphere to hold heat. In sunlight it can become extremely hot, while at night it can become extremely cold. | Muy caliente al sol, frío por la noche | Très chaude au Soleil, froide la nuit |
| `space/moon_gravity` | Surface gravity on the Moon is about one-sixth as strong as Earth's. That is why astronauts can look much lighter as they move around. | Su gravedad es aproximadamente una sexta parte de la terrestre | Une gravité environ six fois plus faible que sur Terre |
| `space/moon_name` | Moon | La Luna | La Lune |
| `space/moon_phases` | The Moon does not change shape. The Sun always lights half of it, and as the Moon travels around Earth we see different portions of that lit half. Those are th… | Las fases muestran distintas partes de la mitad iluminada | Les phases montrent différentes parties de la moitié éclairée |
| `space/moon_rotation` | The Moon rotates once while it completes one orbit around Earth. That is why it shows us almost the same side. The far side is not always dark; it receives sun… | Gira mientras orbita y nos muestra casi siempre la misma cara | Elle tourne sur elle-même en orbitant et nous montre presque toujours la même face |
| `space/moon_surface` | The Moon is a rocky world covered with dust and impact craters. Its large dark areas are ancient plains that were filled by lava long ago. | Rocas, polvo, cráteres y antiguas llanuras de lava | Roches, poussière, cratères et anciennes plaines de lave |
| `space/neptune_blue` | Neptune is an ice giant without a solid surface like Earth's. Methane in its atmosphere contributes to the blue color, and faint rings also circle the planet. | Un gigante helado azul con anillos tenues | Une géante glacée bleue avec des anneaux discrets |
| `space/neptune_distance` | Neptune is about thirty times farther from the Sun than Earth is. Sunlight takes roughly four hours to travel all the way there. | La luz del Sol tarda unas cuatro horas en llegar | La lumière du Soleil met environ quatre heures pour y parvenir |
| `space/neptune_name` | Neptune | Neptuno | Neptune |
| `space/neptune_winds` | Neptune is the windiest world in the solar system. Some winds race faster than two thousand kilometers per hour. | Los vientos más fuertes del sistema solar | Les vents les plus puissants du système solaire |
| `space/neptune_year` | Neptune spins once in about sixteen hours, but it takes about one hundred sixty-five Earth years to complete one orbit around the Sun. | Un año dura unos 165 años terrestres | Une année dure environ 165 ans terrestres |
| `space/saturn_gas` | Saturn is a gas giant made mostly of hydrogen and helium. It does not have a solid surface like Earth. | Un gigante gaseoso | Une géante gazeuse |
| `space/saturn_name` | Saturn | Saturno | Saturne |
| `space/saturn_place` | Saturn is the sixth planet from the Sun and the second-largest planet in our solar system. | Sexto desde el Sol y segundo en tamaño | Sixième depuis le Soleil et deuxième plus grosse |
| `space/saturn_rings` | Saturn's rings are not solid hoops. They are made of billions of pieces of ice and rock orbiting the planet. | Miles de millones de fragmentos de hielo y roca | Des milliards de morceaux de glace et de roche |
| `space/saturn_tilt` | Saturn is tilted, and its rings are tilted with it. As Saturn travels around the Sun, from Earth we see the rings at different angles. | Los anillos cambian de inclinación aparente | Les anneaux semblent changer d'inclinaison |
| `space/sun_fusion` | In the Sun's core, hydrogen joins together to form helium. This process is called fusion, and it releases the energy that reaches us as light and heat. | La fusión libera energía en el núcleo | La fusion libère de l'énergie au cœur de l'étoile |
| `space/sun_name` | Sun | El Sol | Le Soleil |
| `space/sun_plasma` | The Sun is the only star in our solar system. It has no solid surface like Earth; it is made mostly of plasma, hydrogen, and helium. | Una estrella de plasma, no de roca sólida | Une étoile de plasma, pas un rocher solide |
| `space/sun_rotation` | The Sun is not solid, so it does not all rotate at the same speed. Near its equator it turns faster than near its poles. | Sus distintas zonas giran a velocidades diferentes | Ses différentes zones tournent à des vitesses variées |
| `space/sun_scale` | The Sun is enormous: it is about one hundred times wider than Earth. Look how many tiny Earth widths fit across its diameter! | Aproximadamente cien veces más ancho que la Tierra | Environ cent fois plus large que la Terre |
| `space/uranus_color` | Uranus's atmosphere contains methane. This gas absorbs some red light and helps give the planet its blue-green color. | El metano contribuye a su color azul verdoso | Le méthane contribue à sa couleur bleu-vert |
| `space/uranus_name` | Uranus | Urano | Uranus |
| `space/uranus_rings` | Uranus has rings too. They are much fainter and darker than Saturn's bright rings, but they still circle the planet. | Urano también tiene tenues anillos oscuros | Uranus possède aussi de fins anneaux sombres |
| `space/uranus_seasons` | A year on Uranus lasts about eighty-four Earth years. With the planet tilted so far sideways, its seasons are extremely long and one pole can face the Sun for … | Su órbita dura 84 años y tiene estaciones muy largas | Une orbite de 84 ans et des saisons très longues |
| `space/uranus_tilt` | Uranus's axis is tilted by almost ninety-eight degrees. As it spins, the planet therefore looks almost as if it is rolling along its orbit. | Su eje está inclinado casi 98 grados | Un axe incliné de presque 98 degrés |
| `space/venus_clouds` | Thick clouds hide Venus's surface. Underneath are rocks, mountains, valleys, and many volcanic features. | Nubes densas sobre un mundo rocoso | D'épais nuages au-dessus d'un monde rocheux |
| `space/venus_compare` | Venus is the second planet from the Sun and is nearly the same size as Earth, so the two planets are often compared. | Casi del mismo tamaño que la Tierra | Presque aussi grande que la Terre |
| `space/venus_heat` | Venus is the hottest planet in the solar system. Its very dense, carbon-dioxide-rich atmosphere traps an enormous amount of heat. | El planeta más caliente | La planète la plus chaude |
| `space/venus_name` | Venus | Venus | Vénus |
| `space/venus_rotation` | Venus turns very slowly and rotates backward compared with most planets. There, the Sun would appear to rise in the west and set in the east. | Gira lentamente en sentido contrario | Elle tourne lentement en sens inverse |
