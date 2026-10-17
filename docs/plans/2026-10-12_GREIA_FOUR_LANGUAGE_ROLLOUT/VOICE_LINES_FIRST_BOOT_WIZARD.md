# Voice lines — first-boot profile setup (Leo), EN / IT / ES / FR

**Date:** 2026-10-17 · **Status:** REQUEST LIST — **nothing in this file has been generated, recorded or accepted.**
**Owner:** four-language rollout ([PLAN.md](./PLAN.md), [PROGRESS.md](./PROGRESS.md)); cue/voice policy in [LOCAL_AGENT_VOICE_PRODUCTION.md](./LOCAL_AGENT_VOICE_PRODUCTION.md); executable recording order in [LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md](./LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md).
**Product requirement:** [`docs/product/FIRST_BOOT_PROFILE_SETUP.md`](../../product/FIRST_BOOT_PROFILE_SETUP.md).
**Consumer (source owner of cue ids and paths):** `src/greia_launcher/first_profile_copy.py` (`FIRST_PROFILE_CUES`, `FIRST_PROFILE_AUDIO_ROOT`).

## What this is

The Shell's first-boot profile setup (shown once, when the only profile is the
untouched placeholder the platform created on a brand-new device) is guided by
**Leo**, the cast's platform guide (`greia.leo.v1`, the same voice as the
launcher Collection labels and the profile-picker greeter). Each step plays one
short line. The wizard already runs without these files: it resolves
`locale → base language → English → silence` and never errors on a missing
clip, so recording can land independently of code.

Rules applied to every line (from the voice production policy and ADR 0032):

- simple, warm, child-sized, in Leo's thoughtful-storyteller voice;
- no device words (no mouse / keyboard / click / tap); no answer-revealing wording;
- **grammatically neutral toward the child** in IT/ES/FR (no *benvenuto/a*,
  *pronto/a*, *listo/a*, *prêt/e* addressed to the child). Adjectives that agree
  with *Greia* (feminine noun: *pronta*, *lista*, *prête*) are fine;
- the on-screen caption is a short heading, not the transcript; the spoken line
  is the exact text below.

These texts are authored here (new copy). Per `LOCAL_AGENT_VOICE_PRODUCTION.md`
§0.2 they need **owner text approval** before the local Voice Engine produces
candidates, and every candidate stays `REVIEW_PENDING` until a person listens.
ES/FR additionally need native-speaker review of wording.

## Files and ids

| Field | Value |
|---|---|
| speaker | `leo` |
| kind | `character_dialogue` |
| cue id | `first_boot.<name>` (table below) |
| promoted file | `assets/audio/system/first-boot/<locale>/<name>.wav` (+ `.wav.receipt.json`, written by the voice tooling) |
| review output | `$RUN/review/first-boot/<locale>/<name>.wav` (never canonical assets) |
| trigger | played once when the step is entered; the on-screen ear/speaker button replays it |

## Lines

| cue id | step / trigger | EN | IT | ES | FR |
|---|---|---|---|---|---|
| `first_boot.welcome` | Welcome screen appears | Oh, hello! I'm Leo. This Greia is brand new, so let's make a place just for you! | Oh, ciao! Io sono Leo. Questa Greia è tutta nuova: prepariamo un posto solo per te! | ¡Oh, hola! Soy Leo. Esta Greia es nuevecita: ¡preparemos un sitio solo para ti! | Oh, bonjour ! Moi, c'est Leo. Cette Greia est toute neuve : préparons un coin rien que pour toi ! |
| `first_boot.ask_name` | Name step appears | What's your name? Find the letters and spell it for me. A grown-up can help! | Come ti chiami? Trova le lettere e scrivi il tuo nome. Un grande ti può aiutare! | ¿Cómo te llamas? Busca las letras y escribe tu nombre. ¡Un adulto te puede ayudar! | Comment tu t'appelles ? Trouve les lettres et écris ton prénom. Un grand peut t'aider ! |
| `first_boot.name_empty` | "Next" chosen with no name yet | Let's write your name first! | Prima scriviamo il tuo nome! | ¡Primero escribamos tu nombre! | D'abord, écrivons ton prénom ! |
| `first_boot.ask_avatar` | Picture step appears | Now pick a picture that's just for you. | Adesso scegli un'immagine tutta tua. | Ahora elige un dibujo solo para ti. | Maintenant, choisis une image rien que pour toi. |
| `first_boot.ask_age` | Age step appears (optional step) | How old are you? Pick your number. You can skip this, too. | Quanti anni hai? Scegli il tuo numero. Puoi anche saltare. | ¿Cuántos años tienes? Elige tu número. También puedes saltarlo. | Quel âge as-tu ? Choisis ton nombre. Tu peux aussi passer. |
| `first_boot.check` | Summary (name + picture) appears | Here you are! Is that you? | Eccoti! Sei proprio tu? | ¡Aquí estás! ¿Eres tú? | Te voilà ! C'est bien toi ? |
| `first_boot.celebrate` | Profile saved; celebration before Home | Hooray! Your Greia is ready. Let's go and explore! | Evviva! La tua Greia è pronta. Andiamo a esplorare! | ¡Hurra! Tu Greia está lista. ¡Vamos a explorar! | Hourra ! Ta Greia est prête. Allons explorer ! |
| `first_boot.try_again` | Saving the profile failed (rare) | Oops! Something got stuck. Let's try that again. | Ops! Qualcosa si è inceppato. Riproviamo! | ¡Uy! Algo se atascó. ¡Probemos otra vez! | Oups ! Quelque chose a coincé. On réessaie ! |

8 cues × 4 locales = **32 clips**. Pronunciation note: "Greia" is said the
same way in every language (as in the existing Leo launcher labels); "Leo" is
the character name, not translated.

## Ledger rows and Voice Engine requests (after owner text approval)

Ledger rows use the standard header from the recording order:

```text
source,locale,speaker,kind,cue_id,exact_text,caption_key,output_path,existing_asset_sha256,state,provider,receipt_path,asr_result,human_review,notes
shell:first_boot,en,leo,character_dialogue,first_boot.welcome,"Oh, hello! I'm Leo. This Greia is brand new, so let's make a place just for you!",welcome.title,assets/audio/system/first-boot/en/welcome.wav,,MISSING,,,,,
```

Example batch request (one locale × one speaker per batch; replace `$RUN` with
the absolute run folder; text copied **exactly** from the table above):

```json
{"speaker":"leo","kind":"character_dialogue","locale":"en","text":"Oh, hello! I'm Leo. This Greia is brand new, so let's make a place just for you!","cue_id":"first_boot.welcome","output":"$RUN/review/first-boot/en/welcome.wav"}
{"speaker":"leo","kind":"character_dialogue","locale":"en","text":"What's your name? Find the letters and spell it for me. A grown-up can help!","cue_id":"first_boot.ask_name","output":"$RUN/review/first-boot/en/ask_name.wav"}
```

Promotion copies accepted WAVs (and receipts) to
`assets/audio/system/first-boot/<locale>/<name>.wav`. No code change is needed
when they land; `tests/test_first_profile_wizard.py` checks that every cue id in
this file is wired and that missing files fall back silently.
