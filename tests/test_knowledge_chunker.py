"""Slice 1B: grouping blocks into citable chunks.

Parsing is test_knowledge_loaders.py; this file proves only what a chunk is
and where it says it came from.

A chunk is the unit a rule cites, so its boundaries decide whether a
citation is checkable. Two properties matter more than size: a chunk must
not straddle a rule boundary (the reader would not know which half the
citation meant), and it must carry enough surrounding text that the rule
still means the same thing out of context.
"""

from __future__ import annotations

from pathlib import Path

from queryagent.knowledge.chunker import chunk_document
from queryagent.knowledge.loaders import load_document

DOC = """\
# 新增用户口径

运营口径按 users.created_at 注册日期计数。

不含 channel='internal_test' 的测试账号。

## 首单口径

财务侧按 users.first_order_at 首单日期计数。

从未下单的用户不计入。

# 成交额口径

按 status='paid' 的订单金额求和。
"""


def _chunks(tmp_path: Path, text: str = DOC, name: str = "ops.md") -> tuple:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return chunk_document(load_document(path))


def test_a_section_becomes_one_chunk(tmp_path: Path) -> None:
    chunks = _chunks(tmp_path)
    assert [c.section_path for c in chunks] == [
        ("新增用户口径",),
        ("新增用户口径", "首单口径"),
        ("成交额口径",),
    ]


def test_a_chunk_keeps_every_line_of_its_section(tmp_path: Path) -> None:
    """Splitting 「按注册日期计数」 from 「不含测试账号」 would drop a filter."""
    first = _chunks(tmp_path)[0]
    assert "注册日期计数" in first.text
    assert "internal_test" in first.text


def test_a_chunk_carries_its_heading_so_it_survives_out_of_context(
    tmp_path: Path,
) -> None:
    """Retrieved alone, 「按 first_order_at 计数」 must still say what of."""
    second = _chunks(tmp_path)[1]
    assert "首单口径" in second.text


def test_a_chunk_reports_the_line_range_a_person_can_open(tmp_path: Path) -> None:
    chunks = _chunks(tmp_path)
    assert chunks[0].unit == "line"
    assert chunks[0].start < chunks[0].end
    assert chunks[0].end < chunks[1].start


def test_chunk_ids_are_stable_across_reloads(tmp_path: Path) -> None:
    """A citation stored today must still resolve tomorrow (§4.5.4)."""
    assert [c.chunk_id for c in _chunks(tmp_path)] == [
        c.chunk_id for c in _chunks(tmp_path)
    ]


def test_chunk_ids_differ_between_documents(tmp_path: Path) -> None:
    ops = _chunks(tmp_path, name="ops.md")
    finance = _chunks(tmp_path, name="finance.md")
    assert {c.chunk_id for c in ops}.isdisjoint({c.chunk_id for c in finance})


def test_chunk_text_is_normalised_so_quotes_can_be_matched(tmp_path: Path) -> None:
    """Offsets are computed on this text, so it is stored already folded."""
    chunks = _chunks(tmp_path, "# 标题\n\n按 users.created_at\n归属日期计数。\n")
    assert "按 users.created_at 归属日期计数." in chunks[0].text


def test_content_hash_tracks_the_chunk_not_the_document(tmp_path: Path) -> None:
    """Change detection is per chunk: editing one section must not expire the rest."""
    before = _chunks(tmp_path)
    after = _chunks(tmp_path, DOC.replace("按 status='paid' 的订单金额求和。", "改了。"))
    assert before[0].content_hash == after[0].content_hash
    assert before[2].content_hash != after[2].content_hash


def test_text_before_any_heading_still_becomes_a_chunk(tmp_path: Path) -> None:
    chunks = _chunks(tmp_path, "没有标题的说明。\n\n# 标题\n\n正文。\n")
    assert chunks[0].section_path == ()
    assert "没有标题的说明" in chunks[0].text


def test_an_empty_document_yields_no_chunks(tmp_path: Path) -> None:
    assert _chunks(tmp_path, "") == ()


def test_a_heading_with_no_body_yields_no_chunk(tmp_path: Path) -> None:
    """An empty section is not evidence of anything."""
    chunks = _chunks(tmp_path, "# 只有标题\n\n## 子标题\n\n正文。\n")
    assert len(chunks) == 1
    assert chunks[0].section_path == ("只有标题", "子标题")


def test_the_heading_is_separated_from_the_body_by_content_not_whitespace(
    tmp_path: Path,
) -> None:
    """Normalisation folds a CJK/CJK newline away, welding heading onto body.

    「新增用户口径运营口径按…」 is unreadable as displayed quote context, and
    it manufactures substrings that appear in no document — which a citation
    check would then happily confirm.
    """
    first = _chunks(tmp_path)[0]
    assert first.text.startswith("新增用户口径:")
    assert "口径运营口径" not in first.text
