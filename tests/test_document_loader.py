import tempfile
from pathlib import Path

from src.document_loader import load_documents, summarize


def test_load_from_temp_dirs():
    with tempfile.TemporaryDirectory() as samples, tempfile.TemporaryDirectory() as notion:
        s = Path(samples)
        n = Path(notion)
        (s / "policy.md").write_text("# 정책\n내용", encoding="utf-8")
        (n / "notion-page.md").write_text("# Notion 페이지\n내용", encoding="utf-8")

        docs = load_documents(samples_dir=s, notion_dir=n)
        summary = summarize(docs)

        assert summary["total"] == 2
        assert summary["samples"] == 1
        assert summary["notion"] == 1


def test_empty_dirs():
    with tempfile.TemporaryDirectory() as samples, tempfile.TemporaryDirectory() as notion:
        docs = load_documents(samples_dir=Path(samples), notion_dir=Path(notion))
        assert docs == []


def test_missing_notion_dir():
    with tempfile.TemporaryDirectory() as samples:
        docs = load_documents(
            samples_dir=Path(samples),
            notion_dir=Path("/nonexistent_notion_dir_xyz"),
        )
        assert isinstance(docs, list)
