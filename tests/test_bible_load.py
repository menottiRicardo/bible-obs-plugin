import json

import pytest

from app.bible import Bible, BibleDataError, VerseRef
from app.books import BOOKS


def full_valid_data() -> dict:
    """66 libros con los conteos canónicos de capítulos; 1 versículo por capítulo."""
    return {
        "version": "RVR1960",
        "books": [
            {
                "id": b.id,
                "name": b.name,
                "abbrevs": list(b.abbrevs),
                "chapters": [[f"{b.name} {c + 1}:1"] for c in range(b.chapter_count)],
            }
            for b in BOOKS
        ],
    }


def write(tmp_path, data) -> str:
    path = tmp_path / "rvr1960.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_valid_file(tmp_path):
    bible = Bible.load(write(tmp_path, full_valid_data()))
    assert bible.get_text(VerseRef(43, 3, 1)) == "Juan 3:1"
    assert len(bible.books_summary()) == 66


def test_missing_file_says_run_fetch(tmp_path):
    with pytest.raises(BibleDataError, match="fetch-bible"):
        Bible.load(tmp_path / "no-existe.json")


def test_corrupt_json(tmp_path):
    path = tmp_path / "rvr1960.json"
    path.write_text("{no es json", encoding="utf-8")
    with pytest.raises(BibleDataError, match="inválido"):
        Bible.load(path)


def test_wrong_book_count(tmp_path):
    data = full_valid_data()
    data["books"].pop()
    with pytest.raises(BibleDataError, match="66"):
        Bible.load(write(tmp_path, data))


def test_wrong_chapter_count(tmp_path):
    data = full_valid_data()
    data["books"][0]["chapters"].pop()  # Génesis con 49 capítulos
    with pytest.raises(BibleDataError, match="Génesis"):
        Bible.load(write(tmp_path, data))


def test_empty_verse_rejected(tmp_path):
    data = full_valid_data()
    data["books"][0]["chapters"][0][0] = "   "
    with pytest.raises(BibleDataError, match="vacío"):
        Bible.load(write(tmp_path, data))
