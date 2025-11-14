"""Utilities for persisting and retrieving PDF files within the media directory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from app.config import MEDIA_DIR

_TURNS_SUBDIR = Path("turns")


class StorageError(RuntimeError):
    """Base error raised when storage operations fail."""


def _normalize_subdir(subdir: Optional[Union[str, Path]]) -> Path:
    """Sanitize a user provided sub directory, preventing path traversal."""

    if subdir is None:
        return Path()

    candidate = Path(subdir)
    if candidate.is_absolute():
        raise ValueError("Storage sub directories must be relative paths")

    sanitized_parts: list[str] = []
    for part in candidate.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("Storage sub directories cannot contain parent traversal")
        sanitized_parts.append(part)

    return Path(*sanitized_parts)


def _ensure_turns_directory(subdir: Optional[Union[str, Path]] = None) -> Path:
    """Create the turns directory (and optional sub directories) if needed."""

    relative_dir = _TURNS_SUBDIR / _normalize_subdir(subdir)
    base_dir = MEDIA_DIR.resolve()
    target_dir = (base_dir / relative_dir).resolve()

    try:
        target_dir.relative_to(base_dir)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError("Resolved storage path escapes the media directory") from exc

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def save_pdf_file(filename: str, content: Union[bytes, bytearray], *, subdir: Optional[Union[str, Path]] = None) -> str:
    """Persist PDF binary content under the media/turns directory.

    Args:
        filename: Desired filename for the PDF. Only the name component is used.
        content: Binary payload of the PDF file.
        subdir: Optional sub directory within ``media/turns`` where the file
            should be stored.

    Returns:
        The relative path (from ``media_dir``) where the file was stored. This is
        suitable for persisting in the database.
    """

    if not isinstance(content, (bytes, bytearray)):
        raise TypeError("PDF content must be bytes or bytearray")

    sanitized_name = Path(filename).name
    if not sanitized_name:
        raise ValueError("Filename must include a valid name component")

    target_dir = _ensure_turns_directory(subdir=subdir)
    target_path = target_dir / sanitized_name

    try:
        target_path.write_bytes(bytes(content))
    except OSError as exc:  # pragma: no cover - filesystem specific
        raise StorageError(f"Unable to save PDF file '{sanitized_name}': {exc}") from exc

    return str(target_path.relative_to(MEDIA_DIR.resolve()))


def load_pdf_file(relative_path: Union[str, Path]) -> bytes:
    """Load a PDF file previously stored under ``media/turns``.

    Args:
        relative_path: Path to the PDF relative to ``media_dir``. Paths that do
            not point to ``media/turns`` are rejected.

    Returns:
        The raw bytes of the PDF file.
    """

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("PDF path must be relative to the media directory")

    sanitized_parts: list[str] = []
    for part in candidate.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("Relative path cannot contain parent traversal")
        sanitized_parts.append(part)

    sanitized_path = Path(*sanitized_parts)
    if sanitized_path.parts and sanitized_path.parts[0] != _TURNS_SUBDIR.name:
        sanitized_path = _TURNS_SUBDIR / sanitized_path

    base_dir = MEDIA_DIR.resolve()
    absolute_path = (base_dir / sanitized_path).resolve()

    try:
        absolute_path.relative_to(base_dir)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError("Resolved storage path escapes the media directory") from exc

    if not absolute_path.exists():
        raise FileNotFoundError(f"PDF file '{sanitized_path}' does not exist")

    try:
        return absolute_path.read_bytes()
    except OSError as exc:  # pragma: no cover - filesystem specific
        raise StorageError(f"Unable to load PDF file '{sanitized_path}': {exc}") from exc


__all__ = ["save_pdf_file", "load_pdf_file", "StorageError"]
