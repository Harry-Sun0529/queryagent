"""Slice 1B: the normalisation every quote match depends on.

Its own file because this function is load-bearing and cheap to get subtly
wrong: it decides whether a citation the model returns can be found in the
document it claims to come from. A false negative here silently downgrades a
real documented rule to "the document did not say", which is a statement
about the world we must not make wrongly.
"""

from __future__ import annotations

from queryagent.text import normalize


def test_full_width_ascii_folds_to_half_width() -> None:
    """NFKC: a document typed in a CJK IME often carries full-width digits."""
    assert normalize("ＧＭＶ７天") == normalize("GMV7天")


def test_cjk_punctuation_folds_to_ascii() -> None:
    """A model retyping a quote frequently swaps ，。 for , . — not a mismatch."""
    assert normalize("按支付日期，不含退款。") == normalize("按支付日期,不含退款.")


def test_zero_width_characters_are_removed() -> None:
    """Copy-paste from web docs carries ZWSP/ZWNJ that nothing else can see."""
    assert normalize("新增​用户﻿") == normalize("新增用户")


def test_a_soft_line_break_inside_a_chinese_sentence_disappears() -> None:
    """DOCX and PDF extraction insert breaks mid-sentence; Chinese has no space.

    Without this the quote can never be found in the chunk, which is the most
    likely cause of a real rule being dropped.
    """
    assert normalize("按 users.created_at\n归属日期计数") == normalize(
        "按 users.created_at 归属日期计数"
    )


def test_english_words_keep_one_separating_space() -> None:
    """Folding whitespace away entirely would join words and break display."""
    assert normalize("paid   orders\nonly") == "paid orders only"


def test_a_space_between_two_cjk_characters_is_dropped() -> None:
    assert normalize("新增 用户") == "新增用户"


def test_a_space_between_latin_and_cjk_is_kept() -> None:
    """`GMV 口径` reads wrong as `GMV口径` when shown back to the user."""
    assert normalize("GMV 口径") == "GMV 口径"


def test_normalisation_is_idempotent() -> None:
    """Offsets are computed on normalised text, so a second pass must not shift."""
    once = normalize("　按支付日期，\n不含退款。　")
    assert normalize(once) == once


def test_empty_and_whitespace_only_text() -> None:
    assert normalize("") == ""
    assert normalize("   \n\t ") == ""
