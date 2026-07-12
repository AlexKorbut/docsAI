from pathlib import Path

from app.config import get_settings
from app.storage import files


def _use_tmp_upload_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))


def test_save_and_resolve_roundtrip(tmp_path, monkeypatch) -> None:
    _use_tmp_upload_dir(tmp_path, monkeypatch)
    stored = files.save_upload("справка о задолженности.md", b"content")
    path = files.resolve(stored)
    assert path is not None
    assert path.read_bytes() == b"content"


def test_filenames_are_sanitized_and_unique(tmp_path, monkeypatch) -> None:
    _use_tmp_upload_dir(tmp_path, monkeypatch)
    first = files.save_upload("../../etc/passwd", b"a")
    second = files.save_upload("../../etc/passwd", b"b")
    assert first != second
    for stored in (first, second):
        assert "/" not in stored
        resolved = files.resolve(stored)
        assert resolved is not None
        assert resolved.is_relative_to(tmp_path)


def test_resolve_refuses_path_traversal(tmp_path, monkeypatch) -> None:
    _use_tmp_upload_dir(tmp_path, monkeypatch)
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("secret")
    assert files.resolve("../secret.txt") is None


def test_delete_removes_file(tmp_path, monkeypatch) -> None:
    _use_tmp_upload_dir(tmp_path, monkeypatch)
    stored = files.save_upload("doc.md", b"x")
    files.delete(stored)
    assert files.resolve(stored) is None
