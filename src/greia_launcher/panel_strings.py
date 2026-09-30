"""Every user-visible string in the on-device Parent panel, in one place.

The panel had no string table at all. Labels were inline literals, and the audio
tab had already drifted into half-hardcoded Italian next to English —
"Microphone Input Gain (Guadagno Microfono)", "Preset rapidi consigliati:",
"Livello:", "Normale/Medio/Alto/Forte/Massimo" — on a system that declares
twelve supported languages including Arabic, Chinese, Bengali and Hindi. That is
not a cosmetic problem: the audio tab's level label is centred inside a fixed
300 px badge with no measurement, and a longer translation lands on the adjacent
buttons. The screenshot review reproduced exactly that.

This module is the single translation surface. It is deliberately *not* a
gettext pipeline: there is no catalogue compiler, no per-locale .mo files and no
runtime locale negotiation in the Shell yet, and inventing a half-built i18n
layer would be worse than an honest single file. What it does provide is the
property that matters for correctness today:

  * every string is a named constant, so a translator sees the whole surface at
    once and a missing string is a NameError rather than a silent blank;
  * the layout never assumes any of them fit, because greia_launcher.panel_layout
    measures, wraps, grows containers downwards, and clips with an ellipsis only
    where growing is impossible;
  * tests/test_panel_layout.py replays every constant through that layout, so a
    string that cannot be laid out fails the suite rather than a parent.

Two things this deliberately does not solve, recorded so they are not mistaken
for solved. Right-to-left languages (Arabic is in SUPPORTED_SYSTEM_LANGUAGES)
need mirroring of the whole layout, not just text wrapping, and nothing here does
that. Non-Latin scripts (Chinese, Bengali, Hindi) need a font that has the
glyphs; the bundled Nunito Sans coverage decides that, not this module.
"""

from __future__ import annotations

# --- Panel chrome -----------------------------------------------------------
TITLE = "Parent Settings"
CLOSE = "Close"

# --- Tabs -------------------------------------------------------------------
# Longest first: the strip allocates equal columns and shrinks or clips a label
# rather than letting it overlap its neighbour.
TAB_LANGUAGE = "Language"
TAB_AUDIO = "Audio & Mic"
TAB_WIFI = "Wi-Fi"
TAB_SSH = "SSH"
TAB_INFO = "Remote & Pairing"
TAB_POINTER = "Pointer"
TAB_ACCOUNTS = "Kids"
TAB_SECURITY = "Password"

TABS: tuple[tuple[str, str], ...] = (
    (TAB_LANGUAGE, "language"),
    (TAB_AUDIO, "audio"),
    (TAB_ACCOUNTS, "accounts"),
    (TAB_SECURITY, "security"),
    (TAB_WIFI, "wifi"),
    (TAB_SSH, "ssh"),
    (TAB_INFO, "info"),
    (TAB_POINTER, "pointer"),
)

# --- Unlock -----------------------------------------------------------------
AUTH_PROMPT = "Enter Parent Password"
AUTH_UNLOCK = "Unlock"
AUTH_CANCEL = "Cancel"
AUTH_REJECTED = "Incorrect password"
AUTH_CANNOT_CHECK = "Cannot check the password right now"
AUTH_RATE_LIMITED = "Too many attempts. Please wait a moment."

# --- Microphone gain --------------------------------------------------------
AUDIO_TITLE = "Microphone Gain"
AUDIO_INTRO = (
    "Sets the recording volume used for voice activities and puppet theatre. "
    "Pick a preset, or adjust in steps."
)
AUDIO_LEVEL_LABEL = "Level"
AUDIO_DECREASE = "−25%"
AUDIO_INCREASE = "+25%"
AUDIO_INPUT_LABEL = "Microphone input"
AUDIO_INPUT_SILENT = "No sound detected"
AUDIO_INPUT_CLIPPING = "Clipping"
AUDIO_INPUT_UNAVAILABLE = (
    "No microphone could be read. Check that a microphone is connected."
)
AUDIO_PRESETS_TITLE = "Suggested presets"
AUDIO_PRESET_NAMES: dict[float, str] = {
    1.0: "Normal",
    1.5: "Medium",
    2.0: "High",
    3.0: "Strong",
    4.0: "Maximum",
}
AUDIO_BOOST_SUFFIX = "boost"

# --- Child accounts ---------------------------------------------------------
ACCOUNTS_TITLE = "Child accounts"
ACCOUNTS_INTRO = (
    "Each child gets their own saved work, settings and history. Removing an "
    "account deletes its saved data and cannot be undone."
)
ACCOUNTS_ADD = "Add child"
ACCOUNTS_REMOVE = "Remove"
ACCOUNTS_EMPTY = "No child accounts yet."
ACCOUNTS_NAME_LABEL = "Name"
ACCOUNTS_NAME_PLACEHOLDER = "Child's name"
ACCOUNTS_AGE_LABEL = "Approximate age (optional)"
ACCOUNTS_AGE_PLACEHOLDER = "Age"
ACCOUNTS_AVATAR_LABEL = "Avatar"
ACCOUNTS_CREATE = "Create account"
ACCOUNTS_CANCEL = "Cancel"
ACCOUNTS_CONFIRM_REMOVE_TITLE = "Remove this child account?"
ACCOUNTS_CONFIRM_REMOVE_BODY = (
    "All saved work for this child will be deleted. This cannot be undone."
)
ACCOUNTS_CONFIRM_REMOVE_YES = "Remove permanently"
ACCOUNTS_LIMIT_REACHED = (
    "This system allows at most {count} child accounts."
)
ACCOUNTS_ACTIVE_HINT = "The signed-in child cannot be removed."

# --- Parent password --------------------------------------------------------
SECURITY_TITLE = "Parent password"
SECURITY_INTRO = (
    "The Parent password unlocks these settings and manages child accounts. "
    "Keep it somewhere your child will not find it."
)
SECURITY_CURRENT_LABEL = "Current password"
SECURITY_NEW_LABEL = "New password"
SECURITY_CONFIRM_LABEL = "Repeat new password"
SECURITY_CHANGE = "Change password"
SECURITY_MISMATCH = "The two new passwords do not match."
SECURITY_CURRENT_WRONG = "The current password is not correct."
SECURITY_CHANGED = "Parent password changed."
SECURITY_TOO_SHORT = "Use at least {count} characters."
SECURITY_TOO_LONG = "Use at most {count} characters."

# --- Shared feedback --------------------------------------------------------
STATUS_SAVED = "Saved."
STATUS_BUSY = "Working…"
STATUS_OFFLINE = "The Parent service is not responding. Try again shortly."

#: Longest string the panel can be asked to lay out, used by the layout tests as
#: a translation stress case. A German compound is the realistic worst case for
#: the bundled Latin fonts; it is deliberately far longer than any constant here.
STRESS_SAMPLE = (
    "Mikrofonverstärkung für Aufnahmepuppenspiele und Stimmaktivitäten mit "
    "zusätzlicher Verdeutlichung"
)
