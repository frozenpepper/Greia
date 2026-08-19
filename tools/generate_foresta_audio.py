#!/usr/bin/env python3
"""Audio asset generator for Foresta delle Parole activity.

CRITICAL INSTRUCTIONS FOR AI AGENTS & DEVELOPERS:
================================================
1. NEVER pass uppercase letters (e.g. 'C', 'A', 'B') to macOS say with Italian voices (e.g. Alice).
   The macOS TTS engine speaks uppercase letters as 'C maiuscola', 'A maiuscola', etc.,
   and prompt phrases like 'C come Cane' as 'C maiuscola come cane'!
2. ALWAYS use explicit Italian phonetic names for standalone letter sounds:
   - 'a' -> 'a'
   - 'b' -> 'bi'
   - 'c' -> 'ci'
   - 'd' -> 'di'
   - 'e' -> 'e'
   - 'f' -> 'effe'
   - 'g' -> 'gi'
   - 'i' -> 'i'
   - 'l' -> 'elle'
   - 'm' -> 'emme'
   - 'n' -> 'enne'
   - 'o' -> 'o'
   - 'p' -> 'pi'
   - 'q' -> 'cu'
   - 'r' -> 'erre'
   - 's' -> 'esse'
   - 't' -> 'ti'
   - 'u' -> 'u'
   - 'v' -> 'vu'
   - 'z' -> 'zeta'
3. For instruction prompts, ALWAYS use all-lowercase phonetic phrases:
   - 'ci come cane', 'bi come barca', 'effe come fiore', etc.
4. For English, ALWAYS pass lowercase strings ('a as apple', 'b as boat', etc.) so the
   engine never speaks 'Capital A' or 'Capital C'.
5. Target speech rate:
   - Italian: 180 wpm (calm, clear, natural instructional pace for young children).
   - English: 185 wpm (crisp, friendly pace).
"""

from __future__ import annotations

from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIO_ROOT = REPO_ROOT / 'activities' / 'foresta_parole' / 'assets' / 'audio'
EN_DIR = AUDIO_ROOT / 'en'
IT_DIR = AUDIO_ROOT / 'it'

TMP_AIFF = Path('/tmp/greia_speech_gen.aiff')


def make_wav(text: str, voice: str, rate: int, dest_wav: Path) -> None:
    subprocess.run(['say', '-v', voice, '-r', str(rate), text, '-o', str(TMP_AIFF)], check=True)
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@22050', '-c', '1', str(TMP_AIFF), str(dest_wav)], check=True)


def generate_all() -> None:
    EN_DIR.mkdir(parents=True, exist_ok=True)
    IT_DIR.mkdir(parents=True, exist_ok=True)

    it_data = [
        ('a', 'a', 'a come ape', 'ape', 'ape'),
        ('b', 'bi', 'bi come barca', 'barca', 'barca'),
        ('c', 'ci', 'ci come cane', 'cane', 'cane'),
        ('d', 'di', 'di come delfino', 'delfino', 'delfino'),
        ('e', 'e', 'e come elefante', 'elefante', 'elefante'),
        ('f', 'effe', 'effe come fiore', 'fiore', 'fiore'),
        ('g', 'gi', 'gi come gatto', 'gatto', 'gatto'),
        ('i', 'i', 'i come isola', 'isola', 'isola'),
        ('l', 'elle', 'elle come luna', 'luna', 'luna'),
        ('m', 'emme', 'emme come mela', 'mela', 'mela'),
        ('n', 'enne', 'enne come nave', 'nave', 'nave'),
        ('o', 'o', 'o come orso', 'orso', 'orso'),
        ('p', 'pi', 'pi come pesce', 'pesce', 'pesce'),
        ('q', 'cu', 'cu come quercia', 'quercia', 'quercia'),
        ('r', 'erre', 'erre come rana', 'rana', 'rana'),
        ('s', 'esse', 'esse come sole', 'sole', 'sole'),
        ('t', 'ti', 'ti come tigre', 'tigre', 'tigre'),
        ('u', 'u', 'u come uva', 'uva', 'uva'),
        ('v', 'vu', 'vu come vento', 'vento', 'vento'),
        ('z', 'zeta', 'zeta come zebra', 'zebra', 'zebra'),
    ]

    for key, letter_spoken, prompt_spoken, word_spoken, word_stem in it_data:
        make_wav(prompt_spoken, 'Alice', 180, IT_DIR / f'find_{key}.wav')
        make_wav(letter_spoken, 'Alice', 175, IT_DIR / f'{key}.wav')
        make_wav(word_spoken, 'Alice', 175, IT_DIR / f'{word_stem}.wav')

    make_wav('Bravissima!', 'Alice', 185, IT_DIR / 'bravissima.wav')
    make_wav('Fantastico!', 'Alice', 185, IT_DIR / 'fantastico.wav')
    make_wav('Ottimo!', 'Alice', 185, IT_DIR / 'ottimo.wav')

    en_data = [
        ('a', 'a', 'a as apple', 'apple', 'apple'),
        ('b', 'b', 'b as boat', 'boat', 'boat'),
        ('c', 'c', 'c as cat', 'cat', 'cat'),
        ('d', 'd', 'd as dolphin', 'dolphin', 'dolphin'),
        ('e', 'e', 'e as elephant', 'elephant', 'elephant'),
        ('f', 'f', 'f as flower', 'flower', 'flower'),
        ('g', 'g', 'g as giraffe', 'giraffe', 'giraffe'),
        ('h', 'h', 'h as house', 'house', 'house'),
        ('i', 'i', 'i as island', 'island', 'island'),
        ('l', 'l', 'l as lion', 'lion', 'lion'),
        ('m', 'm', 'm as moon', 'moon', 'moon'),
        ('n', 'n', 'n as nest', 'nest', 'nest'),
        ('o', 'o', 'o as owl', 'owl', 'owl'),
        ('p', 'p', 'p as penguin', 'penguin', 'penguin'),
        ('q', 'q', 'q as queen', 'queen', 'queen'),
        ('r', 'r', 'r as rabbit', 'rabbit', 'rabbit'),
        ('s', 's', 's as sun', 'sun', 'sun'),
        ('t', 't', 't as tiger', 'tiger', 'tiger'),
        ('u', 'u', 'u as umbrella', 'umbrella', 'umbrella'),
        ('v', 'v', 'v as volcano', 'volcano', 'volcano'),
        ('w', 'w', 'w as whale', 'whale', 'whale'),
        ('z', 'z', 'z as zebra', 'zebra', 'zebra'),
    ]

    for key, letter_spoken, prompt_spoken, word_spoken, word_stem in en_data:
        make_wav(prompt_spoken, 'Samantha', 185, EN_DIR / f'find_{key}.wav')
        make_wav(letter_spoken, 'Samantha', 180, EN_DIR / f'{key}.wav')
        make_wav(word_spoken, 'Samantha', 180, EN_DIR / f'{word_stem}.wav')

    make_wav('Great job!', 'Samantha', 185, EN_DIR / 'great_job.wav')
    make_wav('Wonderful!', 'Samantha', 185, EN_DIR / 'wonderful.wav')
    make_wav('You did it!', 'Samantha', 185, EN_DIR / 'you_did_it.wav')

    print('Foresta audio generation complete!')


if __name__ == '__main__':
    generate_all()
