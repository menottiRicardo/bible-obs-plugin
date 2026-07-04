"""Descarga la RVR1960 y la normaliza al formato local de la app.

El texto RVR1960 tiene derechos de autor; se descarga a data/ (fuera de git)
para uso local de la congregación, no se redistribuye con este repositorio.
"""

import hashlib
import json
import sys

import httpx

from app.books import BOOKS
from app.settings import settings

SOURCE_URL = (
    "https://raw.githubusercontent.com/dscottpi/bibles/master/"
    "RVR1960%20-%20Spanish.json"
)
SOURCE_SHA256 = "5e9cb2d5f1ee60f9b66236d884fa6f7c97ef564987f63c6eb42e62e25c097b6c"

# Nombres de la fuente que difieren de los canónicos de app/books.py.
SOURCE_NAME_FIXES = {
    "S. Mateo": "Mateo",
    "S. Marcos": "Marcos",
    "S. Lucas": "Lucas",
    "S.Juan": "Juan",
}
_CANONICAL_TO_SOURCE = {v: k for k, v in SOURCE_NAME_FIXES.items()}


def convert_chapters(name: str, chapter_count: int, raw_book: dict) -> list[list[str]]:
    chapters: list[list[str]] = []
    for ch_num in range(1, chapter_count + 1):
        raw_chapter = raw_book.get(str(ch_num))
        if raw_chapter is None:
            raise ValueError(f"{name}: falta el capítulo {ch_num}")
        verses: list[str] = []
        for v_num in range(1, len(raw_chapter) + 1):
            text = raw_chapter.get(str(v_num))
            if text is None or not text.strip():
                raise ValueError(f"{name} {ch_num}: versículo {v_num} vacío o faltante")
            verses.append(text.strip())
        chapters.append(verses)
    return chapters


def normalize_source(source: dict) -> dict:
    books = []
    for meta in BOOKS:
        source_name = _CANONICAL_TO_SOURCE.get(meta.name, meta.name)
        raw_book = source.get(source_name)
        if raw_book is None:
            raise ValueError(f"Libro faltante en la fuente: {source_name}")
        books.append(
            {
                "id": meta.id,
                "name": meta.name,
                "abbrevs": list(meta.abbrevs),
                "chapters": convert_chapters(meta.name, meta.chapter_count, raw_book),
            }
        )
    return {"version": "RVR1960", "books": books}


def main() -> None:
    print(f"Descargando RVR1960 de {SOURCE_URL} ...")
    response = httpx.get(SOURCE_URL, timeout=60, follow_redirects=True)
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    if digest != SOURCE_SHA256:
        sys.exit(
            "La descarga no coincide con el checksum esperado.\n"
            f"  esperado: {SOURCE_SHA256}\n  obtenido: {digest}"
        )
    source = json.loads(response.content.decode("utf-8-sig"))
    source.pop("lang", None)
    data = normalize_source(source)
    settings.data_path.parent.mkdir(parents=True, exist_ok=True)
    settings.data_path.write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    total = sum(len(ch) for book in data["books"] for ch in book["chapters"])
    print(f"OK: {len(data['books'])} libros, {total} versículos → {settings.data_path}")
    print(f"Verificación (Juan 3:16): {data['books'][42]['chapters'][2][15]}")
