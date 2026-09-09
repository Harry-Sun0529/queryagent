"""Slice 1B: turning files into positioned blocks.

This layer proves parsing and location only. Chunking is
test_knowledge_chunker.py; retrieval and permissions are T28's files.

The recurring assertion: a file we could not read must say so. Returning
empty text would let "we failed to parse this" be rendered as "the document
does not mention this rule" — a statement about the world, made wrongly.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from queryagent.knowledge.errors import DocumentParseError, UnsupportedFormat
from queryagent.knowledge.loaders import load_document

MARKDOWN = """\
# 新增用户口径

运营口径按注册日期计数。

## 排除规则

不含 channel='internal_test' 的测试账号。

# 成交额口径

按支付金额求和。
"""

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _write_docx(path: Path, paragraphs: list[tuple[str | None, str]]) -> None:
    """Build a .docx with stdlib only — the loader must not need python-docx.

    Each paragraph is (style, text); text is split across two runs so the
    test also covers Word's habit of fragmenting a sentence mid-word.
    """
    body = ""
    for style, text in paragraphs:
        style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        half = len(text) // 2
        runs = f"<w:r><w:t>{text[:half]}</w:t></w:r><w:r><w:t>{text[half:]}</w:t></w:r>"
        body += f"<w:p>{style_xml}{runs}</w:p>"
    document = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
    path.write_bytes(buffer.getvalue())


# ------------------------------------------------------------------ markdown


def test_markdown_headings_become_a_section_path(tmp_path: Path) -> None:
    path = tmp_path / "ops.md"
    path.write_text(MARKDOWN, encoding="utf-8")
    document = load_document(path)
    paths = [block.section_path for block in document.blocks if not block.is_heading]
    assert ("新增用户口径",) in paths
    assert ("新增用户口径", "排除规则") in paths
    assert ("成交额口径",) in paths


def test_markdown_blocks_carry_their_line_number(tmp_path: Path) -> None:
    """A citation has to point somewhere a person can open and check."""
    path = tmp_path / "ops.md"
    path.write_text(MARKDOWN, encoding="utf-8")
    document = load_document(path)
    body = next(b for b in document.blocks if "注册日期" in b.text)
    assert body.unit == "line"
    assert MARKDOWN.splitlines()[body.position - 1] == body.text


def test_document_title_comes_from_the_first_heading(tmp_path: Path) -> None:
    path = tmp_path / "ops.md"
    path.write_text(MARKDOWN, encoding="utf-8")
    assert load_document(path).title == "新增用户口径"


def test_content_hash_changes_with_content_not_with_path(tmp_path: Path) -> None:
    """Revocation and change detection compare hashes, not mtimes (§4.5.6)."""
    first = tmp_path / "a.md"
    second = tmp_path / "b.md"
    first.write_text(MARKDOWN, encoding="utf-8")
    second.write_text(MARKDOWN, encoding="utf-8")
    assert load_document(first).content_hash == load_document(second).content_hash

    second.write_text(MARKDOWN + "\n补充：按自然月统计。\n", encoding="utf-8")
    assert load_document(first).content_hash != load_document(second).content_hash


# ---------------------------------------------------------------------- docx


def test_docx_is_parsed_without_python_docx(tmp_path: Path) -> None:
    path = tmp_path / "finance.docx"
    _write_docx(
        path,
        [
            ("Heading1", "成交额口径"),
            (None, "财务口径需扣除已退款订单。"),
            ("Heading2", "退款处理"),
            (None, "退款按原单日期冲减。"),
        ],
    )
    document = load_document(path)
    texts = [b.text for b in document.blocks]
    assert "财务口径需扣除已退款订单。" in texts  # runs rejoined
    body = next(b for b in document.blocks if "退款按原单日期" in b.text)
    assert body.section_path == ("成交额口径", "退款处理")
    assert body.unit == "paragraph"


def test_a_docx_without_a_document_part_is_a_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.docx"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
    path.write_bytes(buffer.getvalue())
    with pytest.raises(DocumentParseError, match="broken.docx"):
        load_document(path)


# -------------------------------------------------------------- failure paths


def test_a_file_that_is_not_a_zip_is_a_parse_error_naming_the_file(
    tmp_path: Path,
) -> None:
    """K8: never return empty text and let it read as 'the document is silent'."""
    path = tmp_path / "notreally.docx"
    path.write_text("这不是 docx", encoding="utf-8")
    with pytest.raises(DocumentParseError, match="notreally.docx"):
        load_document(path)


def test_an_unknown_suffix_is_refused_rather_than_guessed(tmp_path: Path) -> None:
    path = tmp_path / "notes.rtf"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(UnsupportedFormat, match="rtf"):
        load_document(path)


def test_a_missing_file_names_the_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_document(tmp_path / "nope.md")


def test_an_empty_markdown_file_parses_to_no_blocks(tmp_path: Path) -> None:
    """Empty is a legitimate document, unlike unreadable — no exception."""
    path = tmp_path / "empty.md"
    path.write_text("", encoding="utf-8")
    assert load_document(path).blocks == ()


def test_a_pdf_without_the_extra_names_the_install_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The optional-extra contract, same shape as the ClickHouse driver.

    Markdown and DOCX must keep working with pypdf absent — the extra buys
    one format, not the document pipeline.
    """
    import sys

    monkeypatch.setitem(sys.modules, "pypdf", None)
    monkeypatch.delitem(sys.modules, "queryagent.knowledge.loaders.pdf", raising=False)
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF-1.4\n")
    with pytest.raises(ImportError):
        load_document(path)

    markdown = tmp_path / "still.md"
    markdown.write_text(MARKDOWN, encoding="utf-8")
    assert load_document(markdown).title == "新增用户口径"
