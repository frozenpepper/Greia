# Fossils — factual authoring record

**Page ID:** `history.fossils`  
**Research status:** READY FOR PILOT AUTHORING  
**Reviewed:** 2026-08-27  
**Purpose:** provenance and child-safe wording authority for the first Greia Encyclopedia fossils entry.

This is authoring/review material, not runtime prose. The child page should feel like a tiny fossil dig: remove sediment, uncover evidence, then touch a few visual clues.

## Source set

### U.S. National Park Service — fossils and fossilization

- *What is a Fossil?*  
  `https://www.nps.gov/subjects/fossils/what-is-a-fossil.htm`
- *How Fossils Form*  
  `https://www.nps.gov/subjects/fossils/how-fossils-form.htm`
- *About Fossils*  
  `https://home.nps.gov/subjects/fossils/about-fossils.htm`
- *Body Fossils*  
  `https://www.nps.gov/subjects/fossils/body-fossils.htm`

Supported concepts:

- fossils are evidence of past life preserved in a geologic context;
- body fossils preserve all or part of an organism; trace fossils preserve evidence of its activity, such as footprints or burrows;
- rapid burial increases the chance that remains will survive decomposition, weathering and scavenging;
- hard parts such as bone, teeth, shells and wood are more likely to fossilize than soft tissues;
- fossilization is uncommon and the fossil record is incomplete;
- fossils reveal information about ancient organisms, environments and change through time.

### Smithsonian National Museum of Natural History

- *Fossilization — How Fossils Form*  
  `https://naturalhistory.si.edu/education/teaching-resources/paleontology/fossilization-how-fossils-form`
- *What Do Fossils Teach Us?*  
  `https://naturalhistory.si.edu/education/teaching-resources/paleontology/what-do-fossils-teach-us`

Supporting concepts:

- fossilization happens through multiple preservation processes rather than one universal recipe;
- the fossil record is used to study the history and diversity of life and changing environments.

## Accepted pilot claims

1. **Fossils are evidence.** A fossil is evidence of past life preserved in rock, sediment or another geologic setting.
2. **Body and trace fossils differ.** A bone, tooth, shell or wood fragment can be a body fossil; a footprint or burrow can be a trace fossil.
3. **Burial and hard parts help.** Quick burial and durable hard parts make fossilization more likely.
4. **Fossilization is rare.** Most organisms never become fossils, so the fossil record is incomplete.
5. **Fossils tell stories about the past.** Scientists use them to learn about ancient organisms, their activities and the environments in which they lived.

The page must not imply that every fossil is a dinosaur bone, that fossils are simply `old bones`, or that every buried organism becomes stone.

## Child-facing wording contract

### Intro — Leo

**Italian**  
`Sotto questi strati può nascondersi una traccia di vita antica. Usa il pennello e scopri che cosa è rimasto nel tempo!`

**English**  
`Under these layers there may be a clue from ancient life. Use the brush and discover what has lasted through time!`

### What a fossil is — Leo

**Italian**  
`Un fossile è una prova di vita del passato conservata nelle rocce, nei sedimenti o in un altro ambiente geologico.`

**English**  
`A fossil is evidence of past life preserved in rock, sediment, or another geologic setting.`

### Body and trace fossils — Leo

**Italian**  
`Un osso, un dente o una conchiglia possono diventare fossili del corpo. Un'impronta o una tana possono diventare fossili di traccia.`

**English**  
`A bone, tooth, or shell can become a body fossil. A footprint or burrow can become a trace fossil.`

### Burial and hard parts — Leo

**Italian**  
`Essere coperti rapidamente dai sedimenti aiuta a conservare i resti. Le parti dure, come ossa, denti e conchiglie, si conservano più facilmente.`

**English**  
`Being buried quickly by sediment helps preserve remains. Hard parts such as bones, teeth, and shells are more likely to survive.`

### Rare clues — Leo

**Italian**  
`Diventare un fossile è raro. Per questo i fossili sono indizi preziosi, ma non raccontano ogni cosa vissuta nel passato.`

**English**  
`Becoming a fossil is rare. Fossils are precious clues, but they do not record every living thing from the past.`

### What scientists learn — Leo

**Italian**  
`Studiando fossili e rocce, gli scienziati possono capire meglio quali esseri vivevano tanto tempo fa e com'era il loro ambiente.`

**English**  
`By studying fossils and rocks, scientists can learn what lived long ago and what those ancient environments were like.`

## Interaction-to-claim mapping

- brush grid -> remove one bounded patch of sediment per child action;
- revealed shell/bone form -> body-fossil cue;
- revealed footprint -> trace-fossil cue;
- sediment-layer control -> briefly cover/reveal the specimen to illustrate burial rather than treating burial as a magic transformation;
- clue/magnifier hotspot -> highlight that fossils plus surrounding rock provide information about past environments;
- rarity hotspot -> show many faint organism silhouettes but only a few preserved fossil marks.

## Engineering guardrails

- `FossilDigModel` should own the finite set of cleared sediment cells and reveal thresholds.
- Pointer and semantic controller input must operate on the same finite grid.
- Do not use per-pixel erasing, masks, image processing or unbounded particle effects for brushing.
- Reset/re-cover is a model transition, not reconstruction of runtime assets.

## Scope guardrails

- Do not define a fossil as merely `something very old`.
- Do not imply all fossils are mineral-replaced bones; preservation processes vary.
- Do not claim an exact percentage of all past organisms that fossilized in child narration.
- Do not make `digging fossils out` look like careless treasure hunting; this is a schematic exploration page, not field-collection guidance.