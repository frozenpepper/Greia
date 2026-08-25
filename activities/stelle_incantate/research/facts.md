# Stelle Incantate — curiosity fact provenance

Authoring-time research record for the child-facing astronomy facts shipped in
`locales/it.json` and `locales/en.json`. One fact per constellation, one idea
per fact, simplified without becoming false. Facts are packaged as localized
strings; this record is development material only.

## curiosity.triangolo.fact

- Meaning: the sky has 88 official constellations agreed by astronomers worldwide.
- Sources:
  - International Astronomical Union — "The Constellations: The 88 IAU constellations" (88 constellations agreed since 1922/1930). https://www.iau.org/science/publications/iau/... — canonical page: https://www.iau.org/IAU/IAU/Science/What-we-do/The-Constellations.aspx
  - NASA StarChild — "88 Officially Recognized Constellations" (list including Triangulum, "Triangle"). https://starchild.gsfc.nasa.gov/docs/StarChild/questions/88constellations.html
- Simplification: "decise dagli astronomi di tutto il mondo" keeps the
  international-agreement idea without dates or politics.

## curiosity.cassiopeia.fact

- Meaning: Cassiopeia is a queen from ancient stories; her stars form a W visible at night.
- Sources:
  - NASA StarChild 88 constellations list — "Cassiopeia — Queen of Ethiopia". https://starchild.gsfc.nasa.gov/docs/StarChild/questions/88constellations.html
  - IAU constellation pages (Cassiopeia, ancient Greek pattern recorded by Ptolemy).
- Simplification: mythology is presented as "storie antiche" (ancient
  stories), not as fact; the W shape is the child-visible truth.

## curiosity.cigno.fact

- Meaning: Cygnus (the Swan) flies across the summer sky with cross-shaped stars.
- Sources:
  - NASA StarChild 88 constellations list — "Cygnus — Swan". https://starchild.gsfc.nasa.gov/docs/StarChild/questions/88constellations.html
  - IAU list (Cygnus, ancient origin).
- Simplification: the "summer sky" phrasing matches mid-northern-hemisphere
  viewing, which matches the reference audience; the cross shape is the
  well-known stick figure (Northern Cross).

## curiosity.carro.fact

- Meaning: the two outer bowl stars of the Big Dipper point toward the North Star (Polaris).
- Sources:
  - NASA Science — "What is the North Star and How Do You Find It?" (pointer
    stars on the end of the Dipper's cup point the way to Polaris).
    https://science.nasa.gov/solar-system/what-is-the-north-star-and-how-do-you-find-it/
  - Cool Cosmos (Caltech IPAC) — "How can I find the North Star?" (pointer
    stars of the Big Dipper cup). https://coolcosmos.ipac.caltech.edu/ask/253-How-can-I-find-the-North-Star-
- Simplification: "indicano la strada" keeps the pointing idea; the Little
  Dipper/Ursa Minor detail is omitted as too dense for age 4-7.

## curiosity.leone.fact

- Meaning: Leo is an ancient constellation observed for thousands of years.
- Sources:
  - IAU — The Constellations (Leo listed as an ancient (Ptolemy) pattern).
    https://www.iau.org/IAU/IAU/Science/What-we-do/The-Constellations.aspx
  - NASA StarChild list — "Leo" present among the 88. https://starchild.gsfc.nasa.gov/docs/StarChild/questions/88constellations.html
- Simplification: "antichissima / migliaia di anni" reflects the Ptolemaic
  and pre-Greek heritage without naming eras a 4-year-old cannot place.

## curiosity.orione.fact

- Meaning: constellation stars look close together but many are really far apart.
- Sources:
  - NASA Space Place — "What Are Constellations?" ("Some stars in a
    constellation might be close while others are very far away"; dot-to-dot
    framing). https://spaceplace.nasa.gov/constellations/en/
  - IAU — The Constellations ("no physical connection ... widely differing
    distances"). https://www.iau.org/IAU/IAU/Science/What-we-do/The-Constellations.aspx
- Simplification: keeps the projection-effect idea in one sentence.

## Voice coverage status

Leo voice audio produced for all six facts in BOTH shipped locales (it/en)
with the canonical `greia.leo.v1` reference (`leo-reference-v1.flac`, hash
verified against the v0.1 voice registry) through Chatterbox Multilingual V3
(`mlx-community/chatterbox-multilingual-v3`, local Apple Silicon production
environment). Generation tool: `tools/generate_stelle_incantate_audio.py`
(single worker, model loaded once, per-clip Metal cache release, idempotent
skip, loud failures). Packaged as mono 22050 Hz OGG under
`assets/audio/<locale>/` and wired through the locale `audio` tables so
`LocalizedResources.audio_cue()` resolves them; the Activity plays the cue
with a procedural-chirp fail-soft fallback.

Programmatic analysis: durations 3.8-6.3 s (consistent with text length),
mono, mean loudness ~-15 dB, peak signature matching the already-accepted
Baia delle Orche production baseline, no meaningful flat-topping.

**Human listening review by the owner is still the final audio acceptance
gate** (VOICE_GENERATION section 13); process success and analysis are never
audio acceptance by themselves.
