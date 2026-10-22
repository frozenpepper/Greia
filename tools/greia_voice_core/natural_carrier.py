"""Natural, localized lead-ins for the owner-approved short-phrase recipe."""
from .short_policy import ShortPhrasePolicy, ALTERNATE_PREFIXES
from .number_comparison import canonical_number_tokens

NATURAL_COMPOSITION_POLICY = "natural-context-period-v1"
DELIVERY = {
    "en": "Warm, calm, clear speech. Careful, natural pronunciation.",
    "it": "Voce calda e calma. Pronuncia chiara e naturale.",
    "fr": "Lecture chaleureuse et calme. Diction claire et naturelle.",
    "es": "Lectura cálida y tranquila. Pronunciación clara y natural.",
}
PREFIXES = {
    "number": {"en": "Let's practise counting together.", "it": "Facciamo pratica con i numeri.", "fr": "Nous allons compter ensemble.", "es": "Vamos a practicar los números."},
    "letter": {"en": "Let's practise the letters together.", "it": "Guardiamo insieme le lettere.", "fr": "Regardons les lettres ensemble.", "es": "Vamos a practicar las letras."},
    "search": {"en": "Let's look carefully together.", "it": "Cerchiamo con calma insieme.", "fr": "Nous allons chercher ensemble.", "es": "Vamos a buscar con calma."},
    "friend": {"en": "Let's look for our friend.", "it": "Cerchiamo insieme il nostro amico.", "fr": "Nous cherchons notre amie.", "es": "Vamos a buscar a nuestra amiga."},
    "general": {"en": "Let's speak calmly together.", "it": "Parliamo con calma insieme.", "fr": "Nous allons parler ensemble.", "es": "Vamos a hablar con calma."},
}


class NaturalCarrierPolicy(ShortPhrasePolicy):
    """Reuse semantic short selection; compose normal sentences without pause commands."""

    composition_policy = NATURAL_COMPOSITION_POLICY

    def topic(self, request) -> str:
        cue = (request.cue_id or "").lower()
        words = request.text.strip().split()
        tokens = canonical_number_tokens(request.language, request.text, ignore_accents=request.ignore_accents)
        if (tokens and all(t.startswith("<num:") for t in tokens)) or any(k in cue for k in ("count_", "numero", "number", "numeri")):
            return "number"
        if any(k in cue for k in ("letter_", "alfabeto", "find_letter", "foresta_parole")):
            return "letter"
        if words[0].strip("¡¿").lower() in {"count", "compte", "conta", "cuenta"}:
            return "number"
        if words[0].strip("¡¿").lower() in {"find", "trova", "cerca", "trouve", "cherche", "busca", "encuentra"}:
            # A capitalized single object after the verb is a source-authored
            # proper name (e.g. Trouve Luna); ordinary objects use search context.
            return "friend" if len(words) == 2 and words[1][0].isupper() else "search"
        return "general"

    def composite(self, request, default_delivery):
        locale = request.language
        if locale not in DELIVERY:
            raise ValueError("no natural carrier for " + locale)
        target = canonical_number_tokens(locale, request.text, ignore_accents=request.ignore_accents)
        for prefix in (PREFIXES[self.topic(request)][locale], PREFIXES["general"][locale], *ALTERNATE_PREFIXES[locale]):
            tokens = canonical_number_tokens(locale, prefix, ignore_accents=request.ignore_accents)
            if not any(tokens[i:i+len(target)] == target for i in range(len(tokens)-len(target)+1)):
                break
        else:
            raise ValueError("target overlaps all natural lead-ins")
        composite = prefix.rstrip(".") + ".\n\n" + request.text
        delivery = request.delivery_prompt or DELIVERY[locale]
        language = {"en":"English", "it":"Italian", "fr":"French", "es":"Spanish"}[locale]
        if len(composite) > 240 or len(f"Speak in {language}. {delivery}") > 300:
            raise ValueError("natural carrier exceeds unsplit provider bounds")
        return prefix, composite, delivery
