"""Standard IPA stays in the data; move its stress marks above vowel nuclei for display.

The output is a learning notation requested by the user, not standard IPA layout.
Only slash-delimited pronunciation spans are parsed; prose labels are left intact.
"""
import json
import re
from pathlib import Path

VOWELS = frozenset("aeiouɑɒæɛɜəʌɔɪʊɚɝ")
DIPHTHONGS = frozenset(("eɪ", "aɪ", "ɔɪ", "oʊ", "aʊ"))
METRICS = json.loads(Path(__file__).with_name("ipa_glyph_metrics.json").read_text())
MARK_COLORS = {"ˈ": "#B3261E", "ˌ": "#1F3A5F"}
# Match the actual vowel ink height, including the dot when the nucleus is i.
# The secondary mark is slightly lower but still clears the vowel completely.
MARK_GAP = {"ˈ": 0.12, "ˌ": 0.06}


def stress_spans(value):
    """Return (mark index, nucleus start, nucleus end, mark) in the original IPA."""
    spans = []
    for pronunciation in re.finditer(r"/([^/]+)/", value):
        start, end = pronunciation.span(1)
        for i in range(start, end):
            if value[i] not in MARK_COLORS:
                continue
            j = i + 1
            while j < end and value[j] not in VOWELS:
                if value[j].isspace() or value[j] in MARK_COLORS:
                    raise ValueError("Stress without a vowel in its word: " + value)
                j += 1
            if j == end:
                raise ValueError("Stress without a vowel: " + value)
            stop = j + (2 if value[j:j + 2] in DIPHTHONGS else 1)
            spans.append((i, j, stop, value[i]))
    return spans


def display_parts(value):
    """List of (plain text or vowel nucleus, optional overhead stress mark)."""
    spans = stress_spans(value)
    removed = {i for i, _, _, _ in spans}
    anchors = {start: (end, mark) for _, start, end, mark in spans}
    parts = []
    plain = ""
    i = 0
    while i < len(value):
        if i in removed:
            i += 1
        elif i in anchors:
            if plain:
                parts.append((plain, None))
                plain = ""
            end, mark = anchors[i]
            parts.append((value[i:end], mark))
            i = end
        else:
            plain += value[i]
            i += 1
    if plain:
        parts.append((plain, None))
    return parts


def mark_offsets(nucleus, mark):
    """Ink-center X and baseline Y offsets, in em, for the specified fonts."""
    vowel = METRICS["nuclei"][nucleus]
    glyph = METRICS["marks"][mark]
    dx = (vowel["left"] + vowel["right"] - glyph["left"] - glyph["right"]) / 2
    dy = vowel["top"] + MARK_GAP[mark] - glyph["bottom"]
    return dx, dy
