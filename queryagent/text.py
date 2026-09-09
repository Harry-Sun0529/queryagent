"""Shared text utilities: normalisation for citation matching.

Slice 1B rests on one deterministic property — a quote the model returns can
be found, verbatim, in the authorised chunk it claims to come from. That
check is only as good as the normalisation in front of it, and Chinese makes
it easy to get subtly wrong:

- DOCX and PDF extraction insert soft line breaks mid-sentence. Chinese has
  no inter-word space, so a break inside 「按支付日期归属」 must vanish
  entirely rather than become a space, or the quote is never found.
- The same document typed through a CJK IME carries full-width digits and
  CJK punctuation; a model retyping the quote tends to emit ASCII ones.
- Text pasted from web docs carries zero-width characters nothing renders.

Every one of those produces a *false negative*: a genuinely documented rule
gets dropped and the confirmation sheet says "the document did not specify
this". That is a statement about the world, and making it wrongly is worse
than the alternative — so normalisation is deliberately generous here.

Offsets are computed on normalised text and the normalised quote is what
gets stored and displayed. Mapping offsets back to the raw bytes would need
a character-index translation table, which is high-effort, high-error code
for a cosmetic gain; the cost is that a displayed quote may differ from the
source in punctuation width and line breaks.
"""

from __future__ import annotations

import re
import unicodedata

# Zero-width and BOM characters: invisible, and fatal to a substring match.
_INVISIBLE = re.compile(r"[​-‏  ﻿]")
_WHITESPACE = re.compile(r"\s+")

# NFKC folds full-width ASCII (Ｇ→G, ７→7) but leaves CJK punctuation alone,
# because 。 and . are genuinely different characters. For *matching* they
# should not be: the model did not change the meaning by typing a period.
_PUNCTUATION = str.maketrans("，。；：！？（）【】「」、〜", ",.;:!?()[]\"\"'~")

_CJK = re.compile(r"[㐀-鿿豈-﫿]")


def _is_cjk(char: str) -> bool:
    return bool(_CJK.match(char))


def normalize(text: str) -> str:
    """Fold text to the form quote matching compares on.

    Idempotent: offsets are computed against the output, so a second pass
    must not shift them.
    """
    folded = unicodedata.normalize("NFKC", text)
    folded = _INVISIBLE.sub("", folded)
    folded = folded.translate(_PUNCTUATION)
    folded = _WHITESPACE.sub(" ", folded).strip()
    return _drop_spaces_between_cjk(folded)


def _drop_spaces_between_cjk(text: str) -> str:
    """Remove a space only when both neighbours are CJK.

    Dropping every space would join English words ("paid orders" →
    "paidorders"), and the normalised text is what gets displayed back to the
    user. Keeping every space would leave the soft line breaks that make a
    Chinese quote unfindable. The neighbour test is what separates the two.
    """
    out: list[str] = []
    for index, char in enumerate(text):
        if (
            char == " "
            and out
            and index + 1 < len(text)
            and _is_cjk(out[-1])
            and _is_cjk(text[index + 1])
        ):
            continue
        out.append(char)
    return "".join(out)
