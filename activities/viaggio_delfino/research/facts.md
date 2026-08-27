# Il Viaggio del Delfino — curiosity fact provenance

Authoring-time research record for the child-facing dolphin facts spoken by
Tito in `locales/it.json` and `locales/en.json`. One compact idea per fact,
simplified without becoming false. Facts ship as localized captions plus
reviewed canonical Tito voice audio (`greia.tito.v1`); this record is
development material only and is not packaged as runtime content.

## curiosity.delfino.breaching

- Meaning: dolphins leap out of the water (up to roughly 4 m / 20 feet), and
  leaping/spinning also works as long-distance signalling.
- Sources:
  - NOAA Fisheries — "Striped Dolphin: Science" ("breaching, jumping, and
    leaping over 20 feet above the surface of the water").
    https://www.fisheries.noaa.gov/species/striped-dolphin/science
  - NOAA Fisheries — "Spinner Dolphin: Science" (leaping/spinning believed to
    serve primarily as acoustic signaling/communication).
    https://www.fisheries.noaa.gov/species/spinner-dolphin/science
- Simplification: "per giocare e per farsi vedere dagli amici" keeps play +
  communication; exact species/measurement detail is omitted for age 4-8.

## curiosity.delfino.echolocation

- Meaning: dolphins emit clicks and locate prey by listening to echoes, even
  when they cannot see.
- Sources:
  - NOAA Fisheries — "Common Bottlenose Dolphin" ("They use passive listening
    and/or high frequency echolocation to locate prey").
    https://www.fisheries.noaa.gov/species/common-bottlenose-dolphin
- Simplification: "piccoli click / l'eco" conveys the emit-and-listen loop;
  frequency ranges are omitted.

## curiosity.delfino.blowhole

- Meaning: dolphins are mammals, not fish, and breathe air through the
  blowhole on top of the head, surfacing regularly.
- Sources:
  - BBC Earth — "Dolph Facts | Mammals" (dolphins are marine mammals that
    breathe air through the blowhole and must resurface).
    https://www.bbcearth.com/factfiles/animals/mammals/dolphin
  - NOAA Fisheries — "Dolphins & Porpoises" (cetaceans are marine mammals).
    https://www.fisheries.noaa.gov/dolphins-porpoises
- Simplification: one idea per sentence chain (mammal → breathes through the
  head hole); conscious-breathing physiology is omitted.

## curiosity.delfino.pods

- Meaning: dolphins live in social groups/families called pods and cooperate
  (for example herding fish together).
- Sources:
  - NOAA Fisheries — "Common Bottlenose Dolphin" ("they work together to herd
    fish into groups").
    https://www.fisheries.noaa.gov/species/common-bottlenose-dolphin
  - NOAA Fisheries — "Dolphins & Porpoises" ("tend to be social and live in
    groups"). https://www.fisheries.noaa.gov/dolphins-porpoises
- Simplification: "famiglie chiamate branchi" keeps family + cooperation;
  fission-fusion dynamics are omitted.

## curiosity.delfino.teeth

- Meaning: dolphins have many teeth but use them only to grasp prey and
  swallow it whole; they never chew.
- Sources:
  - BBC Earth — "Dolph Facts | Mammals" ("Dolphins swallow their prey whole
    and only use their tiny teeth to grasp their meals"; bottlenose up to ~100
    teeth). https://www.bbcearth.com/factfiles/animals/mammals/dolphin
- Simplification: "tanti dentini ... non mastica mai" avoids tooth-count
  statistics while preserving the swallow-whole truth.

## curiosity.delfino.whistle

- Meaning: every dolphin develops its own individually distinctive signature
  whistle that works like a name, letting others recognise it.
- Sources:
  - Janik & Sayigh — PNAS 2006, "Signature whistle shape conveys identity
    information to bottlenose dolphins".
    https://www.pnas.org/doi/abs/10.1073/pnas.0509918103
  - Frontiers in Marine Science 2022 — "The Sarasota Dolphin Whistle Database"
    (signature whistles function "in some ways like human names").
    https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2022.923046/full
- Simplification: "quasi un nome" preserves the identity-function claim
  without implying human language equivalence.

## Voice production

Tito is the semantic speaker for the welcome and six facts in both shipped
locales. Current production is submitted only through the canonical Greia Voice
Production Engine via `tools/generate_viaggio_delfino_audio.py`, which is a thin
batch producer for `tools/greia_voice.py`. The Activity does not select or load a
TTS model, inspect canonical reference files, set token budgets, trim audio, run
Whisper, convert containers, or manage accelerator memory.

Existing packaged OGG files remain historical reviewed runtime assets and are not
regenerated merely because the authoring path changed. Any future generated take
lands in a review workspace with `human_review = PENDING`; owner listening review
is required before it may replace packaged Activity audio.
