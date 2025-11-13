from pathlib import Path

import pytest

from app.core.services import storage as storage_service


def test_save_pdf_file_creates_directories_and_returns_relative_path(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "media_dir", tmp_path)

    relative_path = storage_service.save_pdf_file("document.pdf", b"sample")

    assert relative_path == "turns/document.pdf"
    stored_file = tmp_path / Path(relative_path)
    assert stored_file.exists()
    assert stored_file.read_bytes() == b"sample"


def test_load_pdf_file_reads_previously_saved_content(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "media_dir", tmp_path)

    stored_relative = storage_service.save_pdf_file("turn-summary.pdf", b"payload")
    loaded_content = storage_service.load_pdf_file(stored_relative)

    assert loaded_content == b"payload"


def test_load_pdf_file_accepts_paths_without_turns_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "media_dir", tmp_path)

    storage_service.save_pdf_file("report.pdf", b"payload")
    loaded_content = storage_service.load_pdf_file("report.pdf")

    assert loaded_content == b"payload"


def test_load_pdf_file_raises_for_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_service, "media_dir", tmp_path)

    with pytest.raises(FileNotFoundError):
        storage_service.load_pdf_file("turns/missing.pdf")
