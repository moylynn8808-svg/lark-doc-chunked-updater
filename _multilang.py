#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-language adaptation for lark-doc-chunked-updater.

Handles:
- Arabic RTL: directional marker preservation and RTL run detection
- Japanese: NFC normalization for dakuten/handakuten combining characters
- Korean: NFC normalization for Hangul jamo composition, grapheme counting
"""

import re
import unicodedata
from typing import Iterator, Tuple

# Unicode combining mark categories
_COMBINING_CATEGORIES = frozenset({"Mn", "Mc", "Me"})

# Arabic / Hebrew / RTL presentation form ranges for RTL detection
_RTL_RANGES = [
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0700, 0x074F),   # Syriac
    (0x0750, 0x077F),   # Arabic Extended-A
    (0x0780, 0x07BF),   # Thaana
    (0x07C0, 0x07FF),   # NKo
    (0x0800, 0x085F),   # Samaritan / Arabic Extended-B
    (0x0860, 0x086F),   # Syriac Extended-A
    (0x08A0, 0x08FF),   # Arabic Extended-C
    (0x0FB0, 0x0FD4),   # Hebrew presentation forms
    (0x10D0, 0x10FF),   # Hanifi Rohingya
    (0x1EC00, 0x1ECFF), # Indic Siyaq Numbers
    (0x1ED00, 0x1ED4F), # Ottoman Siyaq Numbers
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
]

# BIDI directional markers
_RTL_OPENERS = frozenset(
    "‪"  # RLE (Right-to-Left Embedding)
    "‫"  # RLO (Right-to-Left Override)
    "⁧"  # RLI (Right-to-Left Isolate)
)
_CLOSERS = "‬"  # PDF (Pop Directional Formatting)


def normalize(text: str) -> str:
    """Apply NFC Unicode normalization.

    Composes decomposed characters:
    - Japanese dakuten: か +  combining ゙ -> が
    - Korean jamo: NFD Hangul -> precomposed syllable
    - Arabic shadda + vowel: composed forms
    """
    return unicodedata.normalize("NFC", text)


def count_graphemes(text: str) -> int:
    """Count visible grapheme clusters instead of code points.

    A grapheme cluster = base character + any following combining marks.
    e.g., 'が' (NFC composed) = 1, 'か' + U+3099 (NFD decomposed) = 1 grapheme.
    """
    if not text:
        return 0
    # Match each base character (non-combining) with its trailing combining marks
    return len(_get_graphemes(text))


def _get_graphemes(text: str) -> list:
    """Return list of grapheme cluster strings."""
    # Pattern: any char that is NOT a combining mark, followed by
    # zero or more combining marks (Unicode Mn/Mc/Me categories)
    clusters = []
    i = 0
    while i < len(text):
        start = i
        i += 1
        # Collect all following combining marks
        while i < len(text) and unicodedata.category(text[i]) in _COMBINING_CATEGORIES:
            i += 1
        clusters.append(text[start:i])
    return clusters


def count_byte_size(text: str) -> int:
    """Return UTF-8 byte length of text.

    Useful for byte-based API limits where len() (code point count)
    underestimates for CJK/Arabic text (3-4 bytes per char in UTF-8).
    """
    return len(text.encode("utf-8"))


def find_rtl_boundaries(text: str) -> Iterator[Tuple[int, int]]:
    """Yield (start, end) positions of RTL text runs.

    Returns indices into the original text string for contiguous runs of
    RTL characters (Arabic, Hebrew, etc.), excluding whitespace and
    bidirectional control characters.
    """
    in_rtl_run = False
    run_start = 0

    for i, ch in enumerate(text):
        code_point = ord(ch)
        is_rtl = any(lo <= code_point <= hi for lo, hi in _RTL_RANGES)
        is_control = ch in _RTL_OPENERS or ch == _CLOSERS

        if (is_rtl or is_control) and not in_rtl_run:
            in_rtl_run = True
            run_start = i
        elif not (is_rtl or is_control) and in_rtl_run:
            # Only yield runs with actual RTL content (not just controls)
            run_has_content = any(
                lo <= ord(c) <= hi
                for c in text[run_start:i]
                for lo, hi in _RTL_RANGES
            )
            if run_has_content:
                yield (run_start, i)
            in_rtl_run = False

    if in_rtl_run:
        run_has_content = any(
            lo <= ord(c) <= hi
            for c in text[run_start:]
            for lo, hi in _RTL_RANGES
        )
        if run_has_content:
            yield (run_start, len(text))


def contains_rtl(text: str) -> bool:
    """Check if text contains any RTL characters."""
    return any(
        lo <= ord(ch) <= hi
        for ch in text
        for lo, hi in _RTL_RANGES
    )


def ensure_rtl_integrity(chunk: str) -> str:
    """Ensure bidirectional markers are balanced within a chunk.

    When a chunk ends with an unclosed RTL embedding/isolate, append
    the appropriate closing character. This prevents RTL formatting
    from leaking into subsequent chunks or being lost in rendering.

    Returns the chunk unchanged if markers are already balanced,
    or the chunk with closing characters appended if needed.
    """
    # Track embedding depth (RLE/RLO use PDF to close)
    embedding_open = 0
    # Track isolate depth (RLI uses PDI to close)
    isolate_open = 0

    for ch in chunk:
        if ch == "‪" or ch == "‫":  # RLE / RLO
            embedding_open += 1
        elif ch == "⁧":  # RLI
            isolate_open += 1
        elif ch == "‬":  # PDF
            embedding_open = max(0, embedding_open - 1)
        elif ch == "⁨":  # LRI
            pass  # LRI, not an issue for RTL
        elif ch == "⁩":  # PDI
            isolate_open = max(0, isolate_open - 1)

    # Append necessary closers
    result = chunk
    # Close isolates first (inner)
    if isolate_open > 0:
        result += "⁩" * isolate_open  # PDI
    # Then close embeddings (outer)
    if embedding_open > 0:
        result += _CLOSERS * embedding_open  # PDF

    return result


def is_nfc(text: str) -> bool:
    """Check if text is already in NFC form (for logging/verification)."""
    return text == unicodedata.normalize("NFC", text)
