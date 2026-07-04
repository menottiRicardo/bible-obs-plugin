from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.books import BOOKS, BY_ID


class BibleDataError(Exception):
    """El archivo de datos falta o es inválido."""


@dataclass(frozen=True)
class VerseRef:
    book_id: int
    chapter: int
    verse: int


class Bible:
    """RVR1960 en memoria. Refs 1-based; almacenamiento 0-based."""

    def __init__(self, chapters_by_book: dict[int, list[list[str]]]):
        self._books = dict(sorted(chapters_by_book.items()))
        self._ids = list(self._books)

    def exists(self, ref: VerseRef) -> bool:
        chapters = self._books.get(ref.book_id)
        if chapters is None or not (1 <= ref.chapter <= len(chapters)):
            return False
        return 1 <= ref.verse <= len(chapters[ref.chapter - 1])

    def get_text(self, ref: VerseRef) -> str:
        if not self.exists(ref):
            raise LookupError(f"Referencia inexistente: {ref}")
        return self._books[ref.book_id][ref.chapter - 1][ref.verse - 1]

    def first_ref(self) -> VerseRef:
        return VerseRef(self._ids[0], 1, 1)

    def next_ref(self, ref: VerseRef) -> VerseRef | None:
        chapters = self._books[ref.book_id]
        if ref.verse < len(chapters[ref.chapter - 1]):
            return VerseRef(ref.book_id, ref.chapter, ref.verse + 1)
        if ref.chapter < len(chapters):
            return VerseRef(ref.book_id, ref.chapter + 1, 1)
        idx = self._ids.index(ref.book_id)
        if idx + 1 < len(self._ids):
            return VerseRef(self._ids[idx + 1], 1, 1)
        return None

    def prev_ref(self, ref: VerseRef) -> VerseRef | None:
        if ref.verse > 1:
            return VerseRef(ref.book_id, ref.chapter, ref.verse - 1)
        chapters = self._books[ref.book_id]
        if ref.chapter > 1:
            prev_chapter = ref.chapter - 1
            return VerseRef(ref.book_id, prev_chapter, len(chapters[prev_chapter - 1]))
        idx = self._ids.index(ref.book_id)
        if idx == 0:
            return None
        prev_id = self._ids[idx - 1]
        prev_chapters = self._books[prev_id]
        return VerseRef(prev_id, len(prev_chapters), len(prev_chapters[-1]))

    def books_summary(self) -> list[dict]:
        return [
            {
                "id": book_id,
                "name": BY_ID[book_id].name,
                "chapters": [len(verses) for verses in chapters],
            }
            for book_id, chapters in self._books.items()
        ]

    @classmethod
    def load(cls, path: Path) -> "Bible":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise BibleDataError(
                f"Falta {path} — ejecuta: uv run fetch-bible"
            ) from None
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BibleDataError(f"{path} inválido: {exc}") from exc

        books = raw.get("books") if isinstance(raw, dict) else None
        if not isinstance(books, list) or len(books) != 66:
            raise BibleDataError(f"{path} inválido: se esperaban 66 libros")

        chapters_by_book: dict[int, list[list[str]]] = {}
        for entry in books:
            book_id = entry.get("id")
            meta = BY_ID.get(book_id)
            if meta is None or book_id in chapters_by_book:
                raise BibleDataError(f"{path} inválido: id de libro inesperado {book_id!r}")
            chapters = entry.get("chapters")
            if not isinstance(chapters, list) or len(chapters) != meta.chapter_count:
                raise BibleDataError(
                    f"{path} inválido: {meta.name} debería tener "
                    f"{meta.chapter_count} capítulos"
                )
            for ch_index, verses in enumerate(chapters, start=1):
                if not isinstance(verses, list) or not verses:
                    raise BibleDataError(
                        f"{path} inválido: {meta.name} {ch_index} sin versículos"
                    )
                for v_index, text in enumerate(verses, start=1):
                    if not isinstance(text, str) or not text.strip():
                        raise BibleDataError(
                            f"{path} inválido: versículo vacío en "
                            f"{meta.name} {ch_index}:{v_index}"
                        )
            chapters_by_book[book_id] = chapters
        return cls(chapters_by_book)
