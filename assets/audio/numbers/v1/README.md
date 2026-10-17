# Shared spoken numbers bank (v1)

Platform-owned clips for the numbers 0..25 in every released Greia language, shared by counting Activities (P7 F6). Resolve them through `greia_platform.localization.shared_number_audio_path(project_root, n, locale)`; never copy number clips into an Activity package.

    assets/audio/numbers/v1/<locale>/<n>.wav (+ .wav.receipt.json)

* `<locale>`: `en`, `it`, `es`, `fr`; fallback is requested locale chain, base language, English, then silence.
* `<n>`: 0..25; anything else resolves to `None`.
* Spoken form is the bare number with an exclamation ("Three!" / "Tre!" / "¡Tres!" / "Trois !"), `pedagogical` speaker (macOS Samantha / Alice / Mónica / Thomas) through `tools/greia_voice.py`.
* Recorded 2026-10-17 after the owner approved all missing lines; receipts carry the generation record. Never re-encode or overwrite a committed clip.
