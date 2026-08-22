# Greia First-Party Activity Visual Audit (All 19 Activities)

**Date:** 2026-08-22  
**Scope:** Real Greia Simulator captures at 1024×600 NORMAL across all 19 first-party Activities  
**Scoring Scale:** 1 (Primitive/Debug Prototype) to 5 (Full Greia Product Reference)

---

## 1. Executive Summary & Quality Ranking

| Rank | Activity ID | Localized Title | Collection | Coherence | Grounding | Entities | UI | Delight | Style | Resp. | Overall Score |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `org.greia.labirinto-magico` | **Labirinto Magico** | Gioca / Logica | 2/5 | 1/5 | 1/5 | 2/5 | 2/5 | 2/5 | 3/5 | **1.9/5.0** |
| 2 | `org.greia.treno-numeri` | **Il Treno dei Numeri** | Impara / Matematica | 2/5 | 1/5 | 1/5 | 2/5 | 2/5 | 2/5 | 3/5 | **1.9/5.0** |
| 3 | `org.greia.acquario-magico` | **Acquario Magico** | Scopri / Crea | 2/5 | 2/5 | 2/5 | 3/5 | 3/5 | 2/5 | 3/5 | **2.4/5.0** |
| 4 | `org.greia.writing` | **La Mia Scrittura** | Crea / Scrivi | 3/5 | 2/5 | 2/5 | 3/5 | 2/5 | 2/5 | 3/5 | **2.4/5.0** |
| 5 | `org.greia.memory-meraviglie` | **Memory delle Meraviglie** | Gioca / Mente | 3/5 | 2/5 | 2/5 | 3/5 | 3/5 | 3/5 | 3/5 | **2.6/5.0** |
| 6 | `org.greia.piccola-serra` | **La Piccola Serra** | Scopri / Gioca | 3/5 | 2/5 | 3/5 | 3/5 | 3/5 | 3/5 | 3/5 | **2.9/5.0** |
| 7 | `org.greia.clinica-cuccioli` | **Clinica dei Cuccioli** | Scopri / Gioca | 3/5 | 3/5 | 3/5 | 3/5 | 3/5 | 3/5 | 3/5 | **3.0/5.0** |
| 8 | `org.greia.foresta-parole` | **Foresta delle Parole** | Impara | 4/5 | 3/5 | 3/5 | 3/5 | 4/5 | 4/5 | 4/5 | **3.6/5.0** |
| 9 | `org.greia.volo-draghetto` | **Volo del Draghetto** | Gioca | 3/5 | 3/5 | 4/5 | 3/5 | 4/5 | 4/5 | 4/5 | **3.6/5.0** |
| 10 | `org.greia.sillabe-magiche` | **Sillabe Magiche** | Impara | 4/5 | 3/5 | 3/5 | 4/5 | 4/5 | 4/5 | 4/5 | **3.7/5.0** |
| 11 | `org.greia.workshop-settings` | **Impostazioni Officina** | Sistema | 4/5 | 4/5 | 3/5 | 4/5 | 3/5 | 4/5 | 4/5 | **3.7/5.0** |
| 12 | `org.greia.orchestra-animali` | **Orchestra degli Animali** | Musica / Gioca | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | **4.0/5.0** |
| 13 | `org.greia.pasticceria-magica` | **Pasticceria Magica** | Crea | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | **4.0/5.0** |
| 14 | `org.greia.teatrino-fiabe` | **Teatrino delle Fiabe** | Crea / Racconta | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | **4.0/5.0** |
| 15 | `org.greia.cucciolo-mio` | **Il Mio Cucciolo** | Scopri / Gioca | 4/5 | 5/5 | 4/5 | 4/5 | 4/5 | 4/5 | 4/5 | **4.1/5.0** |
| 16 | `org.greia.nascondino-bosco` | **Nascondino nel Bosco** | Esplora / Gioca | 5/5 | 5/5 | 4/5 | 4/5 | 5/5 | 5/5 | 4/5 | **4.6/5.0** |
| 17 | `org.greia.costruiamo-ponti` | **Costruiamo Ponti** | Gioca / Crea | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5.0/5.0** |
| 18 | `org.greia.painting` | **Colora e Disegna** | Crea | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5.0/5.0** |
| 19 | `org.greia.shape-garden` | **Giardino delle Forme** | Gioca / Crea | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5.0/5.0** |

---

## 2. Detailed Per-Activity Audit Matrix

### `org.greia.labirinto-magico` — Labirinto Magico
- **Collection:** Gioca / Logica
- **Overall Score:** **1.9/5.0**
- **Evidence Screenshot:** `[org.greia.labirinto-magico.png](captures/org.greia.labirinto-magico.png)`
- **Current Architecture:** Pure 2D grid line maze on flat dark backdrop, primitive colored circles for player and stars, arrow/touch controls
- **Strongest Qualities:** Diverse biome color themes (galaxy, forest, crystal, volcano), multi-tier maze generator
- **Visual Weaknesses:** Looks like an ungrounded algorithmic debug screen; walls are plain rectangular lines, player is a simple circle with no character actor or tactile presence, goal is an empty square
- **Shared Library Usage:** character.dani or character.tito, crystal collectibles, portal goals, biome wall textures
- **Canonical Mascot:** character.tito / character.dani (Exploration / Logic)
- **Authoring Opportunity:** `CREATE_ORIGINAL + COMPOSE_ADAPT (Layered maze tiles, mascot adventurer, luminous magical portal goal)`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.treno-numeri` — Il Treno dei Numeri
- **Collection:** Impara / Matematica
- **Overall Score:** **1.9/5.0**
- **Evidence Screenshot:** `[org.greia.treno-numeri.png](captures/org.greia.treno-numeri.png)`
- **Current Architecture:** Basic colored rectangle train on flat background, crude procedural wheel spokes, straight brown lines for tracks, overlapping circle fruits
- **Strongest Qualities:** Great zero-text visual math equation design, steam whistle audio, interactive fruit loading
- **Visual Weaknesses:** Objectively the most visually crude and flat activity in the entire catalogue; locomotive looks like primitive debug geometry, landscape is empty 2-color ellipses, fruit baskets are plain rectangles
- **Shared Library Usage:** distant hills, clouds, sunbeams, trees, train engine/caboose art, fruit crate baskets
- **Canonical Mascot:** character.dani (Math / Numbers Conductor)
- **Authoring Opportunity:** `CREATE_ORIGINAL + COMPOSE_ADAPT (Rich scenic railway valley, illustrated steam locomotive & wagon, wooden fruit crates, Dani conductor)`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.acquario-magico` — Acquario Magico
- **Collection:** Scopri / Crea
- **Overall Score:** **2.4/5.0**
- **Evidence Screenshot:** `[org.greia.acquario-magico.png](captures/org.greia.acquario-magico.png)`
- **Current Architecture:** Flat cyan/midnight blue fill, crude procedural polygon fish/turtles/octopuses, simple wavy lines for kelp, circular food pellets
- **Strongest Qualities:** Fun day/night bioluminescence switch, gentle bubble physics
- **Visual Weaknesses:** Zero depth layering, no underwater light caustics, rock arches, sunken castle or coral reefs; sea creatures are crude primitive geometric ellipses
- **Shared Library Usage:** aquatic fauna, underwater flora, seabed rock formations
- **Canonical Mascot:** None (marine life)
- **Authoring Opportunity:** `CREATE_ORIGINAL + REUSE generic underwater assets`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.writing` — La Mia Scrittura
- **Collection:** Crea / Scrivi
- **Overall Score:** **2.4/5.0**
- **Evidence Screenshot:** `[org.greia.writing.png](captures/org.greia.writing.png)`
- **Current Architecture:** White document sheet, text cursor, floating toolbar, basic typography
- **Strongest Qualities:** Reliable text editing and autosave
- **Visual Weaknesses:** Bare sterile document canvas, lacks child-friendly desk/easel framing or playful writing accessories
- **Shared Library Usage:** desk textures, stationery props
- **Canonical Mascot:** None (text editor)
- **Authoring Opportunity:** `KEEP_EXISTING_INTENTIONAL`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.memory-meraviglie` — Memory delle Meraviglie
- **Collection:** Gioca / Mente
- **Overall Score:** **2.6/5.0**
- **Evidence Screenshot:** `[org.greia.memory-meraviglie.png](captures/org.greia.memory-meraviglie.png)`
- **Current Architecture:** Grid of cards on plain pastel backdrop, card flip animation, animal/sweet/vehicle icon drawings
- **Strongest Qualities:** Solid flip animation, clean high-contrast icons
- **Visual Weaknesses:** Entire card grid floats on empty flat color; lacks a tactile wooden game table, play mat, or atmospheric room environment
- **Shared Library Usage:** generic card frames, item icons
- **Canonical Mascot:** None (board game)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.piccola-serra` — La Piccola Serra
- **Collection:** Scopri / Gioca
- **Overall Score:** **2.9/5.0**
- **Evidence Screenshot:** `[org.greia.piccola-serra.png](captures/org.greia.piccola-serra.png)`
- **Current Architecture:** Greenhouse interior, 3 plant pots, procedural sunflower/tulip/strawberry growth stages, tool palette (seeds, water, sun, harvest)
- **Strongest Qualities:** Delightful growth cycle mechanics, thought bubble care hints
- **Visual Weaknesses:** Pots and plants are basic polygon drawings; greenhouse backdrop lacks glass panels, potting bench, watering cans, or sunbeams
- **Shared Library Usage:** flora props, garden accessories
- **Canonical Mascot:** None (botanical garden)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.clinica-cuccioli` — Clinica dei Cuccioli
- **Collection:** Scopri / Gioca
- **Overall Score:** **3.0/5.0**
- **Evidence Screenshot:** `[org.greia.clinica-cuccioli.png](captures/org.greia.clinica-cuccioli.png)`
- **Current Architecture:** Striped wallpaper background, examination table bed, procedural animal patient, tool palette (stethoscope, bath, bandaid, food, cuddle)
- **Strongest Qualities:** Clear medical tool order cues, sweet nurturing theme
- **Visual Weaknesses:** Sparse clinic environment without veterinary cabinets, medicine bottles, posters or room depth; procedural patient drawing is basic
- **Shared Library Usage:** furniture props
- **Canonical Mascot:** None (puppy/kitten patients)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.foresta-parole` — Foresta delle Parole
- **Collection:** Impara
- **Overall Score:** **3.6/5.0**
- **Evidence Screenshot:** `[org.greia.foresta-parole.png](captures/org.greia.foresta-parole.png)`
- **Current Architecture:** Enchanted forest background, Leo the owl mascot on branch, floating glowing letter orbs, phonics audio feedback
- **Strongest Qualities:** Great Leo the owl character integration, glowing orb physics, responsive phonetic speech
- **Visual Weaknesses:** Forest trees in background are flat vector silhouettes; card presentation is basic
- **Shared Library Usage:** character.leo, forest foliage
- **Canonical Mascot:** character.leo (Leo the Owl)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.volo-draghetto` — Volo del Draghetto
- **Collection:** Gioca
- **Overall Score:** **3.6/5.0**
- **Evidence Screenshot:** `[org.greia.volo-draghetto.png](captures/org.greia.volo-draghetto.png)`
- **Current Architecture:** Side-scrolling sky runner, procedural dragon with customizable accessories, rainbow boost arches, golden stars
- **Strongest Qualities:** Fluid motion, energetic particle bursts, fun dragon accessories
- **Visual Weaknesses:** Background clouds and rainbow arches are repetitive procedural shapes without scenic landscape below
- **Shared Library Usage:** cloud nodes, star particles
- **Canonical Mascot:** None (friendly dragon)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.sillabe-magiche` — Sillabe Magiche
- **Collection:** Impara
- **Overall Score:** **3.7/5.0**
- **Evidence Screenshot:** `[org.greia.sillabe-magiche.png](captures/org.greia.sillabe-magiche.png)`
- **Current Architecture:** Tactile syllable cards, word illustration badges, drag/tap syllable combining slots, phonetic audio feedback
- **Strongest Qualities:** Clear educational affordances, high-contrast readable typography, playful syllable color coding
- **Visual Weaknesses:** Meadow background behind the cards is plain; word cards float without a grounded table/easel
- **Shared Library Usage:** cloud nodes, illustration icons
- **Canonical Mascot:** None
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.workshop-settings` — Impostazioni Officina
- **Collection:** Sistema
- **Overall Score:** **3.7/5.0**
- **Evidence Screenshot:** `[org.greia.workshop-settings.png](captures/org.greia.workshop-settings.png)`
- **Current Architecture:** Tactile settings panel, profile cards, sliders, hardware status indicators, parent lock dial
- **Strongest Qualities:** Clean system utility, clear visual feedback for settings, high accessibility
- **Visual Weaknesses:** Intentionally utilitarian rather than playful game world
- **Shared Library Usage:** system icons, theme preview widgets
- **Canonical Mascot:** None (system utility)
- **Authoring Opportunity:** `KEEP_EXISTING_INTENTIONAL`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.orchestra-animali` — Orchestra degli Animali
- **Collection:** Musica / Gioca
- **Overall Score:** **4.0/5.0**
- **Evidence Screenshot:** `[org.greia.orchestra-animali.png](captures/org.greia.orchestra-animali.png)`
- **Current Architecture:** Concert bandstand stage, 6 animal musicians with instruments, musical note waves, rhythm tempo lights
- **Strongest Qualities:** Vibrant musical stage, clear instrument affordances, delightful instrument audio feedback
- **Visual Weaknesses:** Musicians are seated on flat procedural circles rather than grounded chairs/risers
- **Shared Library Usage:** musical props, stage backdrop
- **Canonical Mascot:** None (animal musicians)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.pasticceria-magica` — Pasticceria Magica
- **Collection:** Crea
- **Overall Score:** **4.0/5.0**
- **Evidence Screenshot:** `[org.greia.pasticceria-magica.png](captures/org.greia.pasticceria-magica.png)`
- **Current Architecture:** Bakery shop counter, tiered cakes, cream icing layers, fruit decorations, customer order cards
- **Strongest Qualities:** Tactile appetizing cake layers, clear customer order matching, cheerful dessert palette
- **Visual Weaknesses:** Bakery background wallpaper and customer animals are relatively simple
- **Shared Library Usage:** tableware props, fruit ingredients
- **Canonical Mascot:** None (bakery shop theme)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.teatrino-fiabe` — Teatrino delle Fiabe
- **Collection:** Crea / Racconta
- **Overall Score:** **4.0/5.0**
- **Evidence Screenshot:** `[org.greia.teatrino-fiabe.png](captures/org.greia.teatrino-fiabe.png)`
- **Current Architecture:** Red velvet theater stage, wooden proscenium, puppet stick characters (princess, dragon, knight, fairy), stage lighting
- **Strongest Qualities:** Classic tactile puppet theater framing, gold tassels, expressive character puppets
- **Visual Weaknesses:** Background scenery drops are somewhat flat gradient backdrops
- **Shared Library Usage:** curtain textures, character puppets
- **Canonical Mascot:** None (fairy tale puppets)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.cucciolo-mio` — Il Mio Cucciolo
- **Collection:** Scopri / Gioca
- **Overall Score:** **4.1/5.0**
- **Evidence Screenshot:** `[org.greia.cucciolo-mio.png](captures/org.greia.cucciolo-mio.png)`
- **Current Architecture:** Isometric bedroom backdrop, pet bed, interactive ball physics, thought bubbles, multi-state pet animation
- **Strongest Qualities:** Cozy inviting interior, dynamic puppy state machine (sleep, eat, play, bath), tactile toy physics
- **Visual Weaknesses:** Toy box and wall decorations are somewhat flat procedural rectangles
- **Shared Library Usage:** interior backdrop, furniture props
- **Canonical Mascot:** None (pet puppy)
- **Authoring Opportunity:** `COMPOSE_ADAPT`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.nascondino-bosco` — Nascondino nel Bosco
- **Collection:** Esplora / Gioca
- **Overall Score:** **4.6/5.0**
- **Evidence Screenshot:** `[org.greia.nascondino-bosco.png](captures/org.greia.nascondino-bosco.png)`
- **Current Architecture:** Dense layered forest scenery, animated peeking animals (owl, fox, squirrel, bear), foliage shadows, star collection HUD
- **Strongest Qualities:** Superb environmental depth, atmospheric woodland lighting, expressive animal peeking cues
- **Visual Weaknesses:** Slightly static foreground trees in lower resolutions
- **Shared Library Usage:** forest backdrop, vegetation nodes
- **Canonical Mascot:** None (woodland animals)
- **Authoring Opportunity:** `KEEP_EXISTING_INTENTIONAL`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.costruiamo-ponti` — Costruiamo Ponti
- **Collection:** Gioca / Crea
- **Overall Score:** **5.0/5.0**
- **Evidence Screenshot:** `[org.greia.costruiamo-ponti.png](captures/org.greia.costruiamo-ponti.png)`
- **Current Architecture:** PygameReferenceCanvas + PygameSceneRenderer + SceneActorDefinition (Flash the rabbit with dynamic facial states, suspension cables, world cliffs, particle bursts)
- **Strongest Qualities:** Exceptional canonical mascot integration, expressive hopping and landing physics, world backdrops (river, canyon, space), celebration fanfare
- **Visual Weaknesses:** None (owner-accepted productization reference)
- **Shared Library Usage:** character.flash, shadow.contact.small.01, hills.distant.01, cloud.large.01, atmosphere.sunlight_rays.01
- **Canonical Mascot:** character.flash (Flash the Rabbit)
- **Authoring Opportunity:** `KEEP_EXISTING_INTENTIONAL`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.painting` — Colora e Disegna
- **Collection:** Crea
- **Overall Score:** **5.0/5.0**
- **Evidence Screenshot:** `[org.greia.painting.png](captures/org.greia.painting.png)`
- **Current Architecture:** PygameReferenceCanvas + Shared UI Mixins + Color palettes + coloring pages + texture stamps + tactile undo/redo/save cards + zoom/pan canvas
- **Strongest Qualities:** Rich vibrant coloring templates, tactile stamp textures, clean child-first layout, smooth brush lines
- **Visual Weaknesses:** None (owner-accepted productization reference)
- **Shared Library Usage:** ui.portal.frame, category icons, stamp patterns
- **Canonical Mascot:** None (creative utility)
- **Authoring Opportunity:** `KEEP_EXISTING_INTENTIONAL`
- **Generic Library Gap:** `NO_GAP`

### `org.greia.shape-garden` — Giardino delle Forme
- **Collection:** Gioca / Crea
- **Overall Score:** **5.0/5.0**
- **Evidence Screenshot:** `[org.greia.shape-garden.png](captures/org.greia.shape-garden.png)`
- **Current Architecture:** PygameReferenceCanvas + PygameSceneRenderer + layered semantic scene nodes (clouds, distant hills, garden beds, tactile toolbox, particle fountains)
- **Strongest Qualities:** Rich depth layers, polished geometry with soft specular highlights, excellent tactile toolbar, lush flora particles
- **Visual Weaknesses:** None (owner-accepted productization reference)
- **Shared Library Usage:** cloud.large.01, cloud.small.01, hills.distant.01, bush.flowering.01
- **Canonical Mascot:** None (sandbox focus)
- **Authoring Opportunity:** `KEEP_EXISTING_INTENTIONAL`
- **Generic Library Gap:** `NO_GAP`

