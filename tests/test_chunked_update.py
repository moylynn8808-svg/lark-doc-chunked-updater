# lark-doc-chunked-updater 单元测试

"""
运行方式:
    python -m pytest tests/test_chunked_update.py -v
    python -m pytest tests/test_chunked_update.py -v --cov=. --cov-report=term-missing
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path

# Ensure chunked_update is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chunked_update import (
    extract_doc_id,
    split_by_sections,
    split_large_section,
    STATE_FILE,
)


# ─── extract_doc_id ───────────────────────────────────────────────


class TestExtractDocId:
    def test_plain_id(self):
        assert extract_doc_id("DXwRdeid2oYoavxzAVqcnyy1neC") == "DXwRdeid2oYoavxzAVqcnyy1neC"

    def test_docx_url(self):
        url = "https://example.feishu.cn/docx/DXwRdeid2oYoavxzAVqcnyy1neC"
        assert extract_doc_id(url) == "DXwRdeid2oYoavxzAVqcnyy1neC"

    def test_doc_url(self):
        url = "https://example.feishu.cn/doc/DXwRdeid2oYoavxzAVqcnyy1neC"
        assert extract_doc_id(url) == "DXwRdeid2oYoavxzAVqcnyy1neC"

    def test_wiki_url(self):
        url = "https://example.feishu.cn/wiki/wiki123abc"
        assert extract_doc_id(url) == "wiki123abc"

    def test_invalid_url(self):
        with pytest.raises(ValueError, match="无法从 URL 提取文档 ID"):
            extract_doc_id("https://example.com/unknown/abc")


# ─── split_by_sections ─────────────────────────────────────────────


class TestSplitBySections:
    def test_single_section(self):
        content = "# Hello\n\nWorld content"
        chunks = split_by_sections(content, 4000)
        assert len(chunks) == 1
        assert "# Hello" in chunks[0]

    def test_two_sections(self):
        content = "# Part 1\n\n---\n\n## Part 2\n\nContent 2"
        chunks = split_by_sections(content, 4000)
        assert len(chunks) == 1  # small sections get merged

    def test_split_by_separator(self):
        content = "# Part 1\n\n" + "A" * 3000 + "\n\n---\n\n## Part 2\n\n" + "B" * 3000
        chunks = split_by_sections(content, 4000)
        assert len(chunks) == 2

    def test_empty_sections_filtered(self):
        content = "# A\n\n" + "X" * 2000 + "\n\n---\n\n\n---\n\n## B\n\n" + "Y" * 2000
        chunks = split_by_sections(content, 4000)
        assert all(c.strip() for c in chunks)

    def test_small_chunk_size(self):
        content = "Hello\n\nWorld\n\nFoo\n\nBar"
        chunks = split_by_sections(content, 20)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) <= 20

    def test_preserves_markdown_syntax(self):
        content = "## Table\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n---\n\n## List\n\n- x\n- y"
        chunks = split_by_sections(content, 4000)
        assert len(chunks) == 1
        assert "| a | b |" in chunks[0]

    def test_table_content_not_corrupted(self):
        table = "| Header 1 | Header 2 |\n|----------|----------|\n"
        table += "| Row 1 Col 1 | Row 1 Col 2 |\n"
        table += "| Row 2 Col 1 | Row 2 Col 2 |\n"
        content = "# Title\n\n" + table + "\n---\n\n## End\n\nDone"
        chunks = split_by_sections(content, 4000)
        assert len(chunks) == 1
        assert "Header 1" in chunks[0]
        assert "Row 2 Col 2" in chunks[0]


# ─── split_large_section ───────────────────────────────────────────


class TestSplitLargeSection:
    def test_small_section_unchanged(self):
        result = split_large_section("short", 100)
        assert result == ["short"]

    def test_splits_at_paragraph_boundary(self):
        section = "Para 1.\n\nPara 2.\n\nPara 3."
        result = split_large_section(section, 15)
        assert len(result) >= 2
        # Ensure each chunk respects size limit
        for r in result:
            assert len(r) <= 15

    def test_splits_at_line_boundary_for_long_para(self):
        para = "Line 1\nLine 2\nLine 3\nLine 4\n"
        result = split_large_section(para, 15)
        assert len(result) >= 2

    def test_no_chunk_exceeds_limit(self):
        section = "\n\n".join([f"Paragraph {i}: " + "X" * 50 for i in range(10)])
        result = split_large_section(section, 100)
        for r in result:
            assert len(r) <= 100, f"Chunk too large: {len(r)}"


# ─── state file helpers ─────────────────────────────────────────────


class TestStateFile:
    def test_save_and_load_state(self, monkeypatch, tmp_path):
        """Test that state can be saved and loaded correctly."""
        state_path = str(tmp_path / STATE_FILE)
        monkeypatch.setattr("chunked_update.STATE_FILE", state_path)

        # Import the functions after patching
        from chunked_update import save_state, load_state, clear_state

        save_state("doc123", "file.md", 5, [1, 2, 3])

        state = load_state()
        assert state is not None
        assert state["doc_id"] == "doc123"
        assert state["file_path"] == "file.md"
        assert state["total_chunks"] == 5
        assert state["completed"] == [1, 2, 3]

        clear_state()
        assert not os.path.exists(state_path)

    def test_load_state_missing_file(self, monkeypatch, tmp_path):
        from chunked_update import load_state
        state_path = str(tmp_path / "nonexistent.json")
        monkeypatch.setattr("chunked_update.STATE_FILE", state_path)
        assert load_state() is None


# ─── integration: full pipeline ─────────────────────────────────────


class TestFullPipeline:
    def test_dry_run_pipeline(self, tmp_path):
        """Test the full split pipeline on a realistic document."""
        doc = """# 视频脚本策划

## 基础信息

| 项目 | 内容 |
|------|------|
| 集数 | EP01 |
| 主题 | 自我和解 |

---

## 完整脚本

### 开场段 (0:00-0:15)

镜号 1: 特写, 5秒
镜号 2: 近景, 5秒

---

## 发布文案

这是发布文案部分。
包含标签和话题。

---

## 核心金句

1. 金句 A
2. 金句 B
3. 金句 C
"""
        chunks = split_by_sections(doc, 3000)
        assert len(chunks) >= 1
        # Verify total content is preserved
        full_text = "\n\n---\n\n".join(chunks)
        assert "# 视频脚本策划" in full_text
        assert "## 核心金句" in full_text
        assert "| 集数 | EP01 |" in full_text
