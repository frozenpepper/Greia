"""Automatic carrier selection and frozen localized request composition."""
from dataclasses import dataclass
import unicodedata

from .models import SpeechKind, VoiceRequest

COMPOSITION_POLICY = "period-separated-intro-v1"

PREFIXES = {
    "en": "Listen to this phrase in English.",
    "it": "Ascolta questa frase in italiano.",
    "fr": "Cette phrase est en français.",
    "es": "Escucha esta frase en español.",
}


ALTERNATE_PREFIXES = {
    "en": ("Ready for the next words.", "Now we begin."),
    "it": ("Ascolta con attenzione.", "Ora cominciamo."),
    "fr": ("Écoute attentivement.", "Nous commençons."),
    "es": ("Escucha con atención.", "Ahora empezamos."),
}


@dataclass(frozen=True)
class ShortPhrasePolicy:
    """Pure policy: semantic exclusions precede length and explicit forcing."""

    def selected(self, request: VoiceRequest, provider) -> bool:
        """Apply mode/capability/semantic exclusions before counting target words."""
        if request.short_text_mode == "off" or request.kind is SpeechKind.PEDAGOGICAL_SPEECH:
            return False
        if not getattr(provider, "supports_spoken_carrier", False):
            if request.short_text_mode == "on":
                raise ValueError("selected provider does not support the spoken-carrier pipeline")
            return False
        if request.short_text_mode == "on":
            return True
        from voice_carrier import spoken_words
        count = len(spoken_words(request.text))
        alnum = sum(c.isalnum() for c in unicodedata.normalize("NFC", request.text))
        return (1 <= count <= request.short_text_max_words
                and (request.short_text_max_alnum is None or alnum <= request.short_text_max_alnum))

    def composite(self, request: VoiceRequest, default_delivery: str) -> tuple[str, str, str]:
        """Validate one unsplit carrier performance before a provider attempt."""
        try:
            prefix = PREFIXES[request.language]
            language = {"en": "English", "it": "Italian", "fr": "French", "es": "Spanish"}[request.language]
        except KeyError as exc:
            raise ValueError("no localized short-phrase carrier for " + request.language) from exc
        from .number_comparison import canonical_number_tokens
        target_tokens = canonical_number_tokens(request.language, request.text,
                                                ignore_accents=request.ignore_accents)
        for candidate in (prefix, *ALTERNATE_PREFIXES[request.language]):
            tokens = canonical_number_tokens(request.language, candidate,
                                             ignore_accents=request.ignore_accents)
            if not any(tokens[i:i + len(target_tokens)] == target_tokens
                       for i in range(len(tokens) - len(target_tokens) + 1)):
                prefix = candidate
                break
        else:
            raise ValueError("target overlaps every available disposable intro")
        text = prefix.rstrip(".") + ".\n\n" + request.text
        delivery = ((request.delivery_prompt or default_delivery).strip() +
                    " Say the introductory sentence, pause silently for two seconds, then say the final phrase exactly. Do not add words.")
        if len(text) > 240:
            raise ValueError("short-phrase composite exceeds the backend 240-character unsplit limit")
        if len(f"Speak in {language}. {delivery}") > 300:
            raise ValueError("short-phrase delivery exceeds the backend 300-character limit")
        return prefix, text, delivery
