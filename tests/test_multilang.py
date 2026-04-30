# -*- coding: utf-8 -*-
"""
Tests for _multilang module.

Run:
    python -m pytest tests/test_multilang.py -v
"""

import sys
from pathlib import Path

import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _multilang import (
    count_byte_size,
    count_graphemes,
    ensure_rtl_integrity,
    find_rtl_boundaries,
    is_nfc,
    normalize,
    contains_rtl,
)


# ─── normalize ────────────────────────────────────────────────────────


class TestNormalize:
    def test_nfc_composes_japanese_dakuten(self):
        # U+304B (か) + U+3099 (combining dakuten) -> U+304C (が)
        decomposed = "が"
        result = normalize(decomposed)
        assert result == "が"

    def test_nfc_composes_arabic_shadda(self):
        decomposed = "لّ"  # lam + shadda
        result = normalize(decomposed)
        assert unicodedata.normalize("NFC", result) == result

    def test_nfc_composes_hangul(self):
        # NFD jamo -> composed syllable
        nfd_jamo = "가"  # ㄱ + ㅏ -> 가
        result = normalize(nfd_jamo)
        assert is_nfc(result)

    def test_ascii_unchanged(self):
        assert normalize("Hello World") == "Hello World"

    def test_chinese_unchanged(self):
        assert normalize("你好世界") == "你好世界"


# ─── count_graphemes ─────────────────────────────────────────────────


class TestCountGraphemes:
    def test_empty_string(self):
        assert count_graphemes("") == 0

    def test_ascii(self):
        assert count_graphemes("hello") == 5

    def test_chinese(self):
        assert count_graphemes("你好") == 2

    def test_japanese_composed(self):
        # が (U+304C) = 1 grapheme
        assert count_graphemes("が") == 1

    def test_japanese_decomposed(self):
        # か + combining dakuten = 1 grapheme
        decomposed = "が"
        assert count_graphemes(decomposed) == 1

    def test_korean_syllable(self):
        assert count_graphemes("가") == 1

    def test_emoji_with_skin_tone(self):
        # Waving hand + skin tone modifier: skin tone is category Sk (Symbol, Modifier),
        # not Mn/Mc/Me, so counts as 2 codepoints. This is acceptable since emoji
        # skin tones rarely appear in business documents.
        text = "\U0001f44b\U0001f3fd"
        assert count_graphemes(text) == 2

    def test_mixed_content(self):
        assert count_graphemes("你好が") == 3

    def test_arabic_text(self):
        text = "العربية"
        assert count_graphemes(text) == 7


# ─── count_byte_size ─────────────────────────────────────────────────


class TestCountByteSize:
    def test_ascii(self):
        assert count_byte_size("hello") == 5

    def test_chinese(self):
        # Chinese chars = 3 bytes in UTF-8
        assert count_byte_size("你好") == 6

    def test_japanese(self):
        assert count_byte_size("が") == 3

    def test_emoji(self):
        assert count_byte_size("\U0001f44b") == 4

    def test_mixed(self):
        # 2*1 + 2*3 = 8
        assert count_byte_size("hi你好") == 8


# ─── find_rtl_boundaries ─────────────────────────────────────────────


class TestFindRtlBoundaries:
    def test_pure_arabic(self):
        text = "مرحبا"  # مرحبا
        boundaries = list(find_rtl_boundaries(text))
        assert len(boundaries) == 1
        assert boundaries[0] == (0, len(text))

    def test_arabic_with_latin(self):
        text = "Hello مرحبا World"
        boundaries = list(find_rtl_boundaries(text))
        assert len(boundaries) == 1
        assert boundaries[0] == (6, 11)

    def test_pure_latin(self):
        boundaries = list(find_rtl_boundaries("Hello World"))
        assert len(boundaries) == 0

    def test_multiple_arabic_segments(self):
        text = "مرحبا and السلام"
        boundaries = list(find_rtl_boundaries(text))
        assert len(boundaries) == 2

    def test_hebrew(self):
        text = "שלום"  # שלום
        boundaries = list(find_rtl_boundaries(text))
        assert len(boundaries) == 1


# ─── contains_rtl ────────────────────────────────────────────────────


class TestContainsRtl:
    def test_arabic(self):
        assert contains_rtl("مرحبا") is True

    def test_hebrew(self):
        assert contains_rtl("שלום") is True

    def test_latin_only(self):
        assert contains_rtl("Hello") is False

    def test_chinese_only(self):
        assert contains_rtl("你好") is False

    def test_mixed_with_rtl(self):
        assert contains_rtl("Hello مرحبا") is True


# ─── ensure_rtl_integrity ────────────────────────────────────────────


class TestEnsureRtlIntegrity:
    def test_balanced_no_change(self):
        # RLE + text + PDF
        text = "Hello ‪مرحبا‬ World"
        assert ensure_rtl_integrity(text) == text

    def test_unclosed_rle(self):
        text = "‪مر"  # RLE + Arabic, no closing PDF
        result = ensure_rtl_integrity(text)
        assert result.endswith("‬")  # ends with PDF

    def test_unclosed_rli(self):
        text = "⁧مر"  # RLI + Arabic, no closing PDI
        result = ensure_rtl_integrity(text)
        assert "⁩" in result  # contains PDI

    def test_pure_latin_no_change(self):
        text = "Hello World"
        assert ensure_rtl_integrity(text) == text

    def test_empty_string(self):
        assert ensure_rtl_integrity("") == ""

    def test_multiple_unclosed(self):
        text = "‪‪م"  # Two RLE, no closing
        result = ensure_rtl_integrity(text)
        assert result.count("‬") == 2  # Two PDF appended


# ─── is_nfc ──────────────────────────────────────────────────────────


class TestIsNfc:
    def test_ascii_is_nfc(self):
        assert is_nfc("hello") is True

    def test_composed_is_nfc(self):
        assert is_nfc("が") is True  # が

    def test_decomposed_is_not_nfc(self):
        assert is_nfc("が") is False  # か + dakuten

    def test_chinese_is_nfc(self):
        assert is_nfc("你好") is True
