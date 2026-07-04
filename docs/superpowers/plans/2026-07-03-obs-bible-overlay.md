# OBS Bible Verse Overlay (RVR1960) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local FastAPI server that shows Reina Valera 1960 verses as a lower-third in OBS (Browser Source), controlled live from a Spanish web panel, one verse at a time.

**Architecture:** One FastAPI process serves the overlay page (`/overlay`, added to OBS), the control panel (`/`), REST endpoints that mutate in-memory state (current verse + visibility), and a WebSocket that broadcasts every state change to all connected pages. RVR1960 text is a local JSON file loaded fully into memory at startup; a one-time fetch script downloads and normalizes it.

**Tech Stack:** Python ≥3.11, uv, FastAPI, uvicorn, httpx, pydantic-settings, pytest (+pytest-asyncio, `asyncio_mode=auto`), plain HTML/CSS/JS (no build step).

**Spec:** `docs/superpowers/specs/2026-07-03-obs-bible-overlay-design.md`

## Global Constraints

- Python `>=3.11`; all commands through `uv` (`uv sync`, `uv run …`).
- All user-facing copy (panel UI, CLI messages, README) in **Spanish**. Reference format on screen: `Juan 3:16 (RVR1960)`.
- Exactly one verse on screen at a time; no wraparound at Génesis 1:1 / Apocalipsis 22:21.
- `data/` is **gitignored** — the RVR1960 text is copyrighted; the repo ships only the fetch script. Never commit `data/rvr1960.json`.
- Default port **8777**; all settings via env vars prefixed `BIBLE_` (pydantic-settings).
- Frontend is static files under `app/static/` — no bundler, no npm.
- Work on branch `feat/obs-bible-overlay`; never commit to `main`.
- Commits: Conventional Commits (`type(scope): summary`, imperative, ≤72 chars) and every commit ends with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (use a second `-m`).
- Tests: pytest with `asyncio_mode = "auto"` — no per-test `@pytest.mark.asyncio`.

---

### Task 1: Project scaffold

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/settings.py`
- Test: `tests/test_settings.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `app.settings.settings: Settings` with fields `port: int` (default `8777`) and `data_path: pathlib.Path` (default `Path("data/rvr1960.json")`), overridable via env vars `BIBLE_PORT` / `BIBLE_DATA_PATH`. Package `app` importable; `uv sync` creates `.venv`.

- [ ] **Step 1: Create the branch and commit the spec**

```bash
cd /Users/ricardomenotti/Code/bible-plugin
git checkout -b feat/obs-bible-overlay
git add docs/
git commit -m "docs(spec): add OBS bible overlay design and plan" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
data/
.DS_Store
```

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "bible-obs"
version = "0.1.0"
description = "Versículos RVR1960 como lower-third para OBS"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "pydantic-settings>=2.4",
]

[project.scripts]
fetch-bible = "app.fetch_bible:main"

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 4: Write `app/__init__.py`** (empty file) **and `app/settings.py`**

```python
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "BIBLE_"}

    port: int = 8777
    data_path: Path = Path("data/rvr1960.json")


settings = Settings()
```

- [ ] **Step 5: Write the failing test** — `tests/test_settings.py`

```python
from pathlib import Path

from app.settings import Settings


def test_defaults():
    s = Settings()
    assert s.port == 8777
    assert s.data_path == Path("data/rvr1960.json")


def test_env_override(monkeypatch):
    monkeypatch.setenv("BIBLE_PORT", "9000")
    assert Settings().port == 9000
```

- [ ] **Step 6: Sync env and run the test**

Run: `uv sync && uv run pytest tests/test_settings.py -v`
Expected: 2 PASSED (this task's code is written before the test — the "failing" state was the absent project; from Task 2 on, strict test-first).

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml uv.lock app/ tests/
git commit -m "chore(project): scaffold uv project with settings" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Canonical book metadata

**Files:**
- Create: `app/books.py`
- Test: `tests/test_books.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.books.BookMeta` — frozen dataclass: `id: int` (1–66), `name: str` (canonical RVR1960 Spanish name), `abbrevs: tuple[str, ...]` (lowercase, accent-free, space-free), `chapter_count: int`.
  - `app.books.BOOKS: list[BookMeta]` — all 66 in canonical order.
  - `app.books.BY_ID: dict[int, BookMeta]`.

- [ ] **Step 1: Write the failing test** — `tests/test_books.py`

```python
from app.books import BOOKS, BY_ID


def test_sixty_six_books_in_canonical_order():
    assert len(BOOKS) == 66
    assert [b.id for b in BOOKS] == list(range(1, 67))
    assert BOOKS[0].name == "Génesis"
    assert BOOKS[42].name == "Juan"
    assert BOOKS[65].name == "Apocalipsis"


def test_chapter_counts_match_protestant_canon():
    assert sum(b.chapter_count for b in BOOKS) == 1189
    assert BY_ID[19].chapter_count == 150  # Salmos
    assert BY_ID[66].chapter_count == 22   # Apocalipsis


def test_abbrevs_are_normalized_and_globally_unique():
    seen: dict[str, int] = {}
    for book in BOOKS:
        for a in book.abbrevs:
            assert a == a.lower() and " " not in a and "." not in a
            assert a not in seen, f"'{a}' repetido en libros {seen[a]} y {book.id}"
            seen[a] = book.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_books.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.books'`

- [ ] **Step 3: Write `app/books.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class BookMeta:
    id: int
    name: str
    abbrevs: tuple[str, ...]
    chapter_count: int


# (name, abbrevs, chapter_count) in canonical order. Abbrevs are lowercase,
# accent-free and space-free; they must include the normalized full name.
_RAW: list[tuple[str, tuple[str, ...], int]] = [
    ("Génesis", ("gn", "gen", "genesis"), 50),
    ("Éxodo", ("ex", "exo", "exodo"), 40),
    ("Levítico", ("lv", "lev", "levitico"), 27),
    ("Números", ("nm", "num", "numeros"), 36),
    ("Deuteronomio", ("dt", "deu", "deuteronomio"), 34),
    ("Josué", ("jos", "josue"), 24),
    ("Jueces", ("jue", "jueces"), 21),
    ("Rut", ("rt", "rut"), 4),
    ("1 Samuel", ("1s", "1sa", "1sam", "1samuel"), 31),
    ("2 Samuel", ("2s", "2sa", "2sam", "2samuel"), 24),
    ("1 Reyes", ("1r", "1re", "1reyes"), 22),
    ("2 Reyes", ("2r", "2re", "2reyes"), 25),
    ("1 Crónicas", ("1cr", "1cronicas"), 29),
    ("2 Crónicas", ("2cr", "2cronicas"), 36),
    ("Esdras", ("esd", "esdras"), 10),
    ("Nehemías", ("neh", "nehemias"), 13),
    ("Ester", ("est", "ester"), 10),
    ("Job", ("job",), 42),
    ("Salmos", ("sal", "salmo", "salmos"), 150),
    ("Proverbios", ("pr", "prov", "proverbios"), 31),
    ("Eclesiastés", ("ec", "ecl", "eclesiastes"), 12),
    ("Cantares", ("cnt", "cant", "cantares"), 8),
    ("Isaías", ("is", "isa", "isaias"), 66),
    ("Jeremías", ("jer", "jeremias"), 52),
    ("Lamentaciones", ("lm", "lam", "lamentaciones"), 5),
    ("Ezequiel", ("ez", "eze", "ezequiel"), 48),
    ("Daniel", ("dn", "dan", "daniel"), 12),
    ("Oseas", ("os", "oseas"), 14),
    ("Joel", ("jl", "joel"), 3),
    ("Amós", ("am", "amos"), 9),
    ("Abdías", ("abd", "abdias"), 1),
    ("Jonás", ("jon", "jonas"), 4),
    ("Miqueas", ("mi", "miq", "miqueas"), 7),
    ("Nahúm", ("nah", "nahum"), 3),
    ("Habacuc", ("hab", "habacuc"), 3),
    ("Sofonías", ("sof", "sofonias"), 3),
    ("Hageo", ("hag", "hageo"), 2),
    ("Zacarías", ("zac", "zacarias"), 14),
    ("Malaquías", ("mal", "malaquias"), 4),
    ("Mateo", ("mt", "mat", "mateo"), 28),
    ("Marcos", ("mr", "mc", "mar", "marcos"), 16),
    ("Lucas", ("lc", "luc", "lucas"), 24),
    ("Juan", ("jn", "juan"), 21),
    ("Hechos", ("hch", "hech", "hechos"), 28),
    ("Romanos", ("ro", "rom", "romanos"), 16),
    ("1 Corintios", ("1co", "1cor", "1corintios"), 16),
    ("2 Corintios", ("2co", "2cor", "2corintios"), 13),
    ("Gálatas", ("ga", "gal", "galatas"), 6),
    ("Efesios", ("ef", "efe", "efesios"), 6),
    ("Filipenses", ("fil", "flp", "filipenses"), 4),
    ("Colosenses", ("col", "colosenses"), 4),
    ("1 Tesalonicenses", ("1ts", "1tes", "1tesalonicenses"), 5),
    ("2 Tesalonicenses", ("2ts", "2tes", "2tesalonicenses"), 3),
    ("1 Timoteo", ("1ti", "1tim", "1timoteo"), 6),
    ("2 Timoteo", ("2ti", "2tim", "2timoteo"), 4),
    ("Tito", ("tit", "tito"), 3),
    ("Filemón", ("flm", "filemon"), 1),
    ("Hebreos", ("he", "heb", "hebreos"), 13),
    ("Santiago", ("stg", "sant", "santiago"), 5),
    ("1 Pedro", ("1p", "1pe", "1pedro"), 5),
    ("2 Pedro", ("2p", "2pe", "2pedro"), 3),
    ("1 Juan", ("1jn", "1juan"), 5),
    ("2 Juan", ("2jn", "2juan"), 1),
    ("3 Juan", ("3jn", "3juan"), 1),
    ("Judas", ("jud", "judas"), 1),
    ("Apocalipsis", ("ap", "apoc", "apocalipsis"), 22),
]

BOOKS: list[BookMeta] = [
    BookMeta(i + 1, name, abbrevs, chapters)
    for i, (name, abbrevs, chapters) in enumerate(_RAW)
]
BY_ID: dict[int, BookMeta] = {b.id: b for b in BOOKS}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_books.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/books.py tests/test_books.py
git commit -m "feat(bible): add canonical RVR1960 book metadata" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Bible core — refs, lookup, navigation

**Files:**
- Create: `app/bible.py`
- Create: `tests/conftest.py`
- Test: `tests/test_navigation.py`

**Interfaces:**
- Consumes: `app.books.BY_ID`.
- Produces:
  - `app.bible.VerseRef` — frozen dataclass: `book_id: int`, `chapter: int`, `verse: int` (all 1-based).
  - `app.bible.Bible` with:
    - `__init__(self, chapters_by_book: dict[int, list[list[str]]])` — keys are book ids, values are chapters (list) of verses (list of str). No validation here (that's `load`, Task 4).
    - `exists(self, ref: VerseRef) -> bool`
    - `get_text(self, ref: VerseRef) -> str` — assumes `exists(ref)`; raises `LookupError` otherwise.
    - `first_ref(self) -> VerseRef` — first verse of the lowest book id present.
    - `next_ref(self, ref: VerseRef) -> VerseRef | None` — crosses chapter and book boundaries; `None` at the very end.
    - `prev_ref(self, ref: VerseRef) -> VerseRef | None` — symmetric; `None` at the very beginning.
    - `books_summary(self) -> list[dict]` — `[{"id": 1, "name": "Génesis", "chapters": [2, 1]}, ...]` where `chapters` is the verse count per chapter; `name` comes from `BY_ID`.
  - `tests/conftest.py` fixture `tiny_bible` (books 1 and 43 only).

- [ ] **Step 1: Write the fixture** — `tests/conftest.py`

```python
import pytest

from app.bible import Bible


@pytest.fixture
def tiny_bible() -> Bible:
    return Bible(
        {
            1: [  # Génesis: 2 chapters (2 verses, 1 verse)
                ["En el principio creó Dios los cielos y la tierra.", "Segundo versículo."],
                ["Fueron, pues, acabados los cielos y la tierra."],
            ],
            43: [  # Juan: 1 chapter (2 verses)
                ["En el principio era el Verbo.", "Este era en el principio con Dios."],
            ],
        }
    )
```

- [ ] **Step 2: Write the failing tests** — `tests/test_navigation.py`

```python
from app.bible import VerseRef


def test_get_text_and_exists(tiny_bible):
    assert tiny_bible.exists(VerseRef(1, 1, 2))
    assert not tiny_bible.exists(VerseRef(1, 1, 3))
    assert not tiny_bible.exists(VerseRef(2, 1, 1))
    assert not tiny_bible.exists(VerseRef(1, 3, 1))
    assert tiny_bible.get_text(VerseRef(1, 1, 1)).startswith("En el principio creó")


def test_first_ref(tiny_bible):
    assert tiny_bible.first_ref() == VerseRef(1, 1, 1)


def test_next_within_chapter(tiny_bible):
    assert tiny_bible.next_ref(VerseRef(1, 1, 1)) == VerseRef(1, 1, 2)


def test_next_crosses_chapter(tiny_bible):
    assert tiny_bible.next_ref(VerseRef(1, 1, 2)) == VerseRef(1, 2, 1)


def test_next_crosses_book(tiny_bible):
    assert tiny_bible.next_ref(VerseRef(1, 2, 1)) == VerseRef(43, 1, 1)


def test_next_at_end_returns_none(tiny_bible):
    assert tiny_bible.next_ref(VerseRef(43, 1, 2)) is None


def test_prev_within_chapter(tiny_bible):
    assert tiny_bible.prev_ref(VerseRef(1, 1, 2)) == VerseRef(1, 1, 1)


def test_prev_crosses_chapter(tiny_bible):
    assert tiny_bible.prev_ref(VerseRef(1, 2, 1)) == VerseRef(1, 1, 2)


def test_prev_crosses_book(tiny_bible):
    assert tiny_bible.prev_ref(VerseRef(43, 1, 1)) == VerseRef(1, 2, 1)


def test_prev_at_start_returns_none(tiny_bible):
    assert tiny_bible.prev_ref(VerseRef(1, 1, 1)) is None


def test_books_summary(tiny_bible):
    assert tiny_bible.books_summary() == [
        {"id": 1, "name": "Génesis", "chapters": [2, 1]},
        {"id": 43, "name": "Juan", "chapters": [2]},
    ]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_navigation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.bible'`

- [ ] **Step 4: Write `app/bible.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from app.books import BY_ID


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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_navigation.py -v`
Expected: 11 PASSED

- [ ] **Step 6: Commit**

```bash
git add app/bible.py tests/conftest.py tests/test_navigation.py
git commit -m "feat(bible): add verse lookup and navigation core" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Data file loading and validation

**Files:**
- Modify: `app/bible.py` (add `Bible.load` classmethod at the end of the class)
- Test: `tests/test_bible_load.py`

**Interfaces:**
- Consumes: `app.books.BOOKS`, `BY_ID`; `BibleDataError`, `Bible` from Task 3.
- Produces: `Bible.load(cls, path: Path) -> Bible` — reads the JSON data file, validates it, raises `BibleDataError` (Spanish message) on any problem. Expected file shape:
  `{"version": "RVR1960", "books": [{"id": 1, "name": "Génesis", "abbrevs": [...], "chapters": [["v1", "v2"], ...]}, ...]}`

- [ ] **Step 1: Write the failing tests** — `tests/test_bible_load.py`

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bible_load.py -v`
Expected: FAIL — `AttributeError: type object 'Bible' has no attribute 'load'`

- [ ] **Step 3: Add `load` to `app/bible.py`**

Add imports at the top of the file:

```python
import json
from pathlib import Path

from app.books import BOOKS, BY_ID
```

(replacing the existing `from app.books import BY_ID` line), and add this classmethod at the end of the `Bible` class:

```python
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
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run pytest -v`
Expected: all PASSED (settings + books + navigation + load)

- [ ] **Step 5: Commit**

```bash
git add app/bible.py tests/test_bible_load.py
git commit -m "feat(bible): load and validate local RVR1960 data file" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Quick-search reference parser

**Files:**
- Create: `app/refparse.py`
- Test: `tests/test_refparse.py`

**Interfaces:**
- Consumes: `app.books.BOOKS`; `app.bible.VerseRef`.
- Produces:
  - `app.refparse.normalize(token: str) -> str` — lowercase, accents stripped, spaces and dots removed.
  - `app.refparse.parse(q: str) -> VerseRef | None` — **syntactic only** (existence is checked by the API with `bible.exists`). Accepts `jn 3 16`, `Juan 3:16`, `juan 3.16`, `1co 13 4`, `1 corintios 13:4`, `salmos 23` (verse defaults to 1). Returns `None` when the book is unknown or the shape doesn't match.

- [ ] **Step 1: Write the failing tests** — `tests/test_refparse.py`

```python
import pytest

from app.bible import VerseRef
from app.books import BOOKS
from app.refparse import normalize, parse


def test_normalize():
    assert normalize("1 Corintios") == "1corintios"
    assert normalize("Génesis") == "genesis"
    assert normalize("S. Mateo") == "smateo"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("jn 3 16", VerseRef(43, 3, 16)),
        ("Juan 3:16", VerseRef(43, 3, 16)),
        ("juan 3.16", VerseRef(43, 3, 16)),
        ("1co 13 4", VerseRef(46, 13, 4)),
        ("1 corintios 13:4", VerseRef(46, 13, 4)),
        ("salmos 23", VerseRef(19, 23, 1)),
        ("génesis 1 1", VerseRef(1, 1, 1)),
        ("genesis 1 1", VerseRef(1, 1, 1)),
        ("  APOC 22:21  ", VerseRef(66, 22, 21)),
    ],
)
def test_parse_accepted_formats(query, expected):
    assert parse(query) == expected


@pytest.mark.parametrize("query", ["", "juan", "xyz 3 16", "3 16", "juan tres 16"])
def test_parse_rejects(query):
    assert parse(query) is None


def test_full_names_of_all_66_books_parse():
    for book in BOOKS:
        assert parse(f"{book.name} 1 1") == VerseRef(book.id, 1, 1), book.name
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_refparse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.refparse'`

- [ ] **Step 3: Write `app/refparse.py`**

```python
import re
import unicodedata

from app.bible import VerseRef
from app.books import BOOKS

_INDEX: dict[str, int] = {
    abbrev: book.id for book in BOOKS for abbrev in book.abbrevs
}

_REF = re.compile(r"^(?P<book>.+?)\s+(?P<chapter>\d+)(?:[\s:.]+(?P<verse>\d+))?$")


def normalize(token: str) -> str:
    decomposed = unicodedata.normalize("NFD", token.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s.]+", "", stripped)


def parse(q: str) -> VerseRef | None:
    match = _REF.match(q.strip())
    if match is None:
        return None
    book_id = _INDEX.get(normalize(match.group("book")))
    if book_id is None:
        return None
    return VerseRef(book_id, int(match.group("chapter")), int(match.group("verse") or 1))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_refparse.py -v`
Expected: all PASSED (note: `test_parse_rejects["3 16"]` passes because book token `"3"` is not an abbrev)

- [ ] **Step 5: Commit**

```bash
git add app/refparse.py tests/test_refparse.py
git commit -m "feat(bible): parse quick-search references with Spanish abbrevs" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Fetch script for the RVR1960 data

**Files:**
- Create: `app/fetch_bible.py`
- Test: `tests/test_fetch_bible.py`

**Interfaces:**
- Consumes: `app.books.BOOKS`; `app.settings.settings`.
- Produces:
  - `app.fetch_bible.convert_chapters(name: str, chapter_count: int, raw_book: dict) -> list[list[str]]` — converts one source book (`{"1": {"1": "text", ...}, ...}`) to ordered chapter/verse lists, stripping whitespace; raises `ValueError` (Spanish) on missing chapters/verses or empty text.
  - `app.fetch_bible.normalize_source(source: dict) -> dict` — full source dict → the data-file shape consumed by `Bible.load` (Task 4).
  - `app.fetch_bible.main() -> None` — console entry point `uv run fetch-bible`: downloads, checks SHA-256, normalizes, writes `settings.data_path`.
- Verified source facts (checked 2026-07-03): dict keyed by Spanish book name plus a `"lang": "SPAN"` key to drop; gospels appear as `"S. Mateo"`, `"S. Marcos"`, `"S. Lucas"`, `"S.Juan"` (no space); text confirmed RVR1960 (Juan 3:16 "…ha dado a su Hijo unigénito…"); 31,104 verses total; verses have trailing spaces to strip.

- [ ] **Step 1: Write the failing tests** — `tests/test_fetch_bible.py`

```python
import pytest

from app.fetch_bible import SOURCE_NAME_FIXES, convert_chapters


def test_convert_chapters_orders_and_strips():
    raw = {"2": {"1": "c "}, "1": {"2": " b", "1": " a "}}
    assert convert_chapters("X", 2, raw) == [["a", "b"], ["c"]]


def test_convert_chapters_missing_chapter():
    with pytest.raises(ValueError, match="X"):
        convert_chapters("X", 2, {"1": {"1": "a"}})


def test_convert_chapters_missing_verse():
    with pytest.raises(ValueError, match="X 1"):
        convert_chapters("X", 1, {"1": {"1": "a", "3": "c"}})


def test_convert_chapters_empty_verse():
    with pytest.raises(ValueError, match="X 1"):
        convert_chapters("X", 1, {"1": {"1": "   "}})


def test_gospel_name_fixes():
    assert SOURCE_NAME_FIXES == {
        "S. Mateo": "Mateo",
        "S. Marcos": "Marcos",
        "S. Lucas": "Lucas",
        "S.Juan": "Juan",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_fetch_bible.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.fetch_bible'`

- [ ] **Step 3: Write `app/fetch_bible.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_fetch_bible.py -v`
Expected: 5 PASSED

- [ ] **Step 5: Run the real fetch (network) and verify**

Run: `uv run fetch-bible`
Expected output (exact numbers):

```
OK: 66 libros, 31104 versículos → data/rvr1960.json
Verificación (Juan 3:16): Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito, para que todo aquel que en él cree, no se pierda, mas tenga vida eterna.
```

Then confirm the loader accepts the real file:

Run: `uv run python -c "from app.bible import Bible; from app.settings import settings; b = Bible.load(settings.data_path); from app.bible import VerseRef; print(b.get_text(VerseRef(19, 23, 1)))"`
Expected: `Jehová es mi pastor; nada me faltará.`

And that git ignores it: `git status --short data/` → no output.

- [ ] **Step 6: Commit**

```bash
git add app/fetch_bible.py tests/test_fetch_bible.py
git commit -m "feat(data): add pinned RVR1960 fetch script" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Overlay state and connection manager

**Files:**
- Create: `app/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `app.bible.Bible`, `VerseRef`; `app.books.BY_ID`.
- Produces:
  - `app.state.OverlayState`:
    - `__init__(self, bible: Bible)` — starts at `bible.first_ref()`, `visible = False`.
    - `ref: VerseRef`, `visible: bool` (attributes).
    - `set_verse(self, ref: VerseRef) -> None` — caller validates existence first.
    - `step(self, direction: int) -> bool` — `+1` next / `-1` prev; returns `False` (state unchanged) at canon edges.
    - `set_visible(self, visible: bool) -> None`
    - `snapshot(self) -> dict` — `{"type": "state", "visible": bool, "book_id": int, "book_name": str, "chapter": int, "verse": int, "text": str}` (no `overlays` key — `main.py` adds it).
  - `app.state.ConnectionManager`:
    - `add(self, ws, role: str) -> None` / `remove(self, ws) -> None` (idempotent remove).
    - `overlay_count: int` property — connections added with `role == "overlay"`.
    - `async broadcast(self, message: dict) -> None` — `await ws.send_json(message)` on every connection; a connection that raises is removed, the rest still receive.

- [ ] **Step 1: Write the failing tests** — `tests/test_state.py`

```python
from app.bible import VerseRef
from app.state import ConnectionManager, OverlayState


class FakeWS:
    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    async def send_json(self, data: dict) -> None:
        if self.fail:
            raise RuntimeError("conexión perdida")
        self.sent.append(data)


def test_initial_state(tiny_bible):
    state = OverlayState(tiny_bible)
    assert state.ref == VerseRef(1, 1, 1)
    assert state.visible is False


def test_snapshot_fields(tiny_bible):
    state = OverlayState(tiny_bible)
    snap = state.snapshot()
    assert snap == {
        "type": "state",
        "visible": False,
        "book_id": 1,
        "book_name": "Génesis",
        "chapter": 1,
        "verse": 1,
        "text": "En el principio creó Dios los cielos y la tierra.",
    }


def test_step_and_edges(tiny_bible):
    state = OverlayState(tiny_bible)
    assert state.step(-1) is False                # borde inicial: no-op
    assert state.ref == VerseRef(1, 1, 1)
    assert state.step(1) is True
    assert state.ref == VerseRef(1, 1, 2)
    state.set_verse(VerseRef(43, 1, 2))           # último versículo
    assert state.step(1) is False
    assert state.ref == VerseRef(43, 1, 2)


def test_set_visible(tiny_bible):
    state = OverlayState(tiny_bible)
    state.set_visible(True)
    assert state.snapshot()["visible"] is True


async def test_broadcast_and_overlay_count():
    manager = ConnectionManager()
    overlay, panel, broken = FakeWS(), FakeWS(), FakeWS(fail=True)
    manager.add(overlay, "overlay")
    manager.add(panel, "panel")
    manager.add(broken, "overlay")
    assert manager.overlay_count == 2

    await manager.broadcast({"type": "state"})
    assert overlay.sent == [{"type": "state"}]
    assert panel.sent == [{"type": "state"}]
    assert manager.overlay_count == 1             # el roto fue eliminado

    manager.remove(overlay)
    manager.remove(overlay)                        # remove idempotente
    assert manager.overlay_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.state'`

- [ ] **Step 3: Write `app/state.py`**

```python
from __future__ import annotations

from typing import Any

from app.bible import Bible, VerseRef
from app.books import BY_ID


class OverlayState:
    def __init__(self, bible: Bible):
        self._bible = bible
        self.ref: VerseRef = bible.first_ref()
        self.visible: bool = False

    def set_verse(self, ref: VerseRef) -> None:
        self.ref = ref

    def step(self, direction: int) -> bool:
        moved = (
            self._bible.next_ref(self.ref)
            if direction > 0
            else self._bible.prev_ref(self.ref)
        )
        if moved is None:
            return False
        self.ref = moved
        return True

    def set_visible(self, visible: bool) -> None:
        self.visible = visible

    def snapshot(self) -> dict:
        return {
            "type": "state",
            "visible": self.visible,
            "book_id": self.ref.book_id,
            "book_name": BY_ID[self.ref.book_id].name,
            "chapter": self.ref.chapter,
            "verse": self.ref.verse,
            "text": self._bible.get_text(self.ref),
        }


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[Any, str] = {}

    def add(self, ws: Any, role: str) -> None:
        self._conns[ws] = role

    def remove(self, ws: Any) -> None:
        self._conns.pop(ws, None)

    @property
    def overlay_count(self) -> int:
        return sum(1 for role in self._conns.values() if role == "overlay")

    async def broadcast(self, message: dict) -> None:
        for ws in list(self._conns):
            try:
                await ws.send_json(message)
            except Exception:
                self.remove(ws)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_state.py -v`
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/state.py tests/test_state.py
git commit -m "feat(server): add overlay state and websocket connection manager" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: FastAPI app — REST endpoints

**Files:**
- Create: `app/main.py`
- Create: `app/static/.gitkeep` (placeholder so StaticFiles mount works before Tasks 10–11)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: everything above — `Bible`, `BibleDataError`, `VerseRef`, `OverlayState`, `ConnectionManager`, `refparse.parse`, `settings`.
- Produces: `app.main.create_app(bible: Bible | None = None) -> FastAPI`. With `bible=None` it calls `Bible.load(settings.data_path)` and exits the process with the Spanish error message if that fails (uvicorn runs it with `--factory`). Routes:
  - `GET /api/books` → `bible.books_summary()`
  - `GET /api/state` → snapshot dict + `"overlays": int`
  - `POST /api/verse` body `{"book_id": int, "chapter": int, "verse": int}` → 422 `{"detail": "Referencia inválida"}` if it doesn't exist; else set + broadcast, returns state
  - `POST /api/next`, `POST /api/prev` (no body) → step (no-op at edges), broadcast, returns state
  - `POST /api/visibility` body `{"visible": bool}` → set + broadcast, returns state
  - `GET /api/search?q=…` → `{"found": false}` or `{"found": true, "book_id": int, "chapter": int, "verse": int}` (found only if it parses **and** exists)
  - `GET /` and `GET /overlay` → `FileResponse` of the panel/overlay `index.html`; `/static` mounted on `app/static/`
  - `WS /ws` — added in Task 9 (this task's tests cover REST only)

- [ ] **Step 1: Write the failing tests** — `tests/test_api.py`

```python
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tiny_bible) -> TestClient:
    return TestClient(create_app(tiny_bible))


def test_books(client):
    books = client.get("/api/books").json()
    assert [b["id"] for b in books] == [1, 43]
    assert books[0]["chapters"] == [2, 1]


def test_initial_state(client):
    state = client.get("/api/state").json()
    assert state["book_name"] == "Génesis"
    assert state["chapter"] == 1 and state["verse"] == 1
    assert state["visible"] is False
    assert state["overlays"] == 0


def test_set_verse(client):
    resp = client.post("/api/verse", json={"book_id": 43, "chapter": 1, "verse": 2})
    assert resp.status_code == 200
    assert resp.json()["book_name"] == "Juan"
    assert client.get("/api/state").json()["verse"] == 2


def test_set_invalid_verse(client):
    resp = client.post("/api/verse", json={"book_id": 43, "chapter": 9, "verse": 1})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Referencia inválida"
    assert client.get("/api/state").json()["book_name"] == "Génesis"


def test_next_and_prev(client):
    assert client.post("/api/next").json()["verse"] == 2
    assert client.post("/api/prev").json()["verse"] == 1


def test_prev_at_start_is_noop(client):
    state = client.post("/api/prev").json()
    assert state["book_id"] == 1 and state["chapter"] == 1 and state["verse"] == 1


def test_visibility_toggle(client):
    assert client.post("/api/visibility", json={"visible": True}).json()["visible"] is True
    assert client.get("/api/state").json()["visible"] is True


def test_search_found(client):
    res = client.get("/api/search", params={"q": "jn 1 2"}).json()
    assert res == {"found": True, "book_id": 43, "chapter": 1, "verse": 2}


def test_search_parses_but_does_not_exist(client):
    # Salmos está en el índice de abreviaturas pero no en tiny_bible.
    assert client.get("/api/search", params={"q": "salmos 23"}).json() == {"found": False}


def test_search_unparseable(client):
    assert client.get("/api/search", params={"q": "zzz 1 1"}).json() == {"found": False}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write `app/main.py`** (and create empty `app/static/.gitkeep`)

```python
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import refparse
from app.bible import Bible, BibleDataError, VerseRef
from app.settings import settings
from app.state import ConnectionManager, OverlayState

STATIC_DIR = Path(__file__).parent / "static"


class VersePayload(BaseModel):
    book_id: int
    chapter: int
    verse: int


class VisibilityPayload(BaseModel):
    visible: bool


def create_app(bible: Bible | None = None) -> FastAPI:
    if bible is None:
        try:
            bible = Bible.load(settings.data_path)
        except BibleDataError as exc:
            sys.exit(str(exc))

    app = FastAPI(title="bible-obs")
    state = OverlayState(bible)
    manager = ConnectionManager()

    def current_state() -> dict:
        message = state.snapshot()
        message["overlays"] = manager.overlay_count
        return message

    async def push_state() -> dict:
        message = current_state()
        await manager.broadcast(message)
        return message

    @app.get("/api/books")
    def books() -> list[dict]:
        return bible.books_summary()

    @app.get("/api/state")
    def get_state() -> dict:
        return current_state()

    @app.post("/api/verse")
    async def set_verse(payload: VersePayload) -> dict:
        ref = VerseRef(payload.book_id, payload.chapter, payload.verse)
        if not bible.exists(ref):
            raise HTTPException(status_code=422, detail="Referencia inválida")
        state.set_verse(ref)
        return await push_state()

    @app.post("/api/next")
    async def next_verse() -> dict:
        state.step(1)
        return await push_state()

    @app.post("/api/prev")
    async def prev_verse() -> dict:
        state.step(-1)
        return await push_state()

    @app.post("/api/visibility")
    async def set_visibility(payload: VisibilityPayload) -> dict:
        state.set_visible(payload.visible)
        return await push_state()

    @app.get("/api/search")
    def search(q: str = "") -> dict:
        ref = refparse.parse(q)
        if ref is None or not bible.exists(ref):
            return {"found": False}
        return {
            "found": True,
            "book_id": ref.book_id,
            "chapter": ref.chapter,
            "verse": ref.verse,
        }

    @app.get("/")
    def panel_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "panel" / "index.html")

    @app.get("/overlay")
    def overlay_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "overlay" / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: 10 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/static/.gitkeep tests/test_api.py
git commit -m "feat(server): add REST API for verse control" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: WebSocket endpoint

**Files:**
- Modify: `app/main.py` (add `/ws` route inside `create_app`, before the `@app.get("/")` route)
- Test: `tests/test_ws.py`

**Interfaces:**
- Consumes: `ConnectionManager`, `push_state` from Task 8's `create_app` internals.
- Produces: `WS /ws?role=overlay|panel` (default `panel`). On connect: accept, register, broadcast fresh state (every client, including the new one, receives it with the updated `overlays` count). Incoming text frames are read and ignored (keepalive). On disconnect: deregister and broadcast again.

- [ ] **Step 1: Write the failing tests** — `tests/test_ws.py`

```python
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tiny_bible) -> TestClient:
    return TestClient(create_app(tiny_bible))


def test_overlay_receives_snapshot_on_connect(client):
    with client.websocket_connect("/ws?role=overlay") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert msg["book_name"] == "Génesis"
        assert msg["overlays"] == 1


def test_verse_change_is_broadcast(client):
    with client.websocket_connect("/ws?role=overlay") as ws:
        ws.receive_json()  # snapshot inicial
        client.post("/api/verse", json={"book_id": 43, "chapter": 1, "verse": 1})
        msg = ws.receive_json()
        assert msg["book_name"] == "Juan"
        assert msg["text"] == "En el principio era el Verbo."


def test_panel_role_does_not_count_as_overlay(client):
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["overlays"] == 0


def test_overlay_count_via_rest_after_connect(client):
    assert client.get("/api/state").json()["overlays"] == 0
    with client.websocket_connect("/ws?role=overlay") as ws:
        ws.receive_json()
        assert client.get("/api/state").json()["overlays"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ws.py -v`
Expected: FAIL — websocket connection rejected (403/404), no `/ws` route

- [ ] **Step 3: Add the WebSocket route to `app/main.py`**

Extend the fastapi import line to include the websocket types:

```python
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
```

Add inside `create_app`, after the `search` route and before `panel_page`:

```python
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        role = ws.query_params.get("role", "panel")
        await ws.accept()
        manager.add(ws, role)
        await push_state()
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            manager.remove(ws)
            await push_state()
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `uv run pytest -v`
Expected: all PASSED

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_ws.py
git commit -m "feat(server): broadcast state over websocket" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: Overlay frontend

**Files:**
- Create: `app/static/overlay/index.html`
- Create: `app/static/overlay/overlay.css`
- Create: `app/static/overlay/overlay.js`
- Delete: `app/static/.gitkeep` (no longer needed)

**Interfaces:**
- Consumes: `WS /ws?role=overlay` state messages (Task 9 schema).
- Produces: the page OBS renders. No JS framework, no external assets.

- [ ] **Step 1: Write `app/static/overlay/index.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Overlay RVR1960</title>
<link rel="stylesheet" href="/static/overlay/overlay.css">
</head>
<body>
<div id="lower-third" class="hidden">
  <p id="verse-text"></p>
  <p id="verse-ref"></p>
</div>
<script src="/static/overlay/overlay.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `app/static/overlay/overlay.css`**

```css
html, body {
  margin: 0;
  padding: 0;
  background: transparent;
  overflow: hidden;
}

#lower-third {
  position: fixed;
  left: 50%;
  bottom: 4vh;
  transform: translateX(-50%);
  width: min(90vw, 1600px);
  box-sizing: border-box;
  padding: 1.1em 1.6em;
  background: rgba(10, 15, 25, 0.82);
  border-radius: 14px;
  font-family: "Helvetica Neue", Arial, sans-serif;
  color: #ffffff;
  text-align: center;
  opacity: 1;
  transition: opacity 300ms ease;
}

#lower-third.hidden {
  opacity: 0;
}

#verse-text {
  margin: 0;
  font-size: 2.4vw;
  line-height: 1.35;
}

#lower-third.len-lg #verse-text { font-size: 2vw; }
#lower-third.len-xl #verse-text { font-size: 1.7vw; }

#verse-ref {
  margin: 0.5em 0 0;
  font-size: 1.3vw;
  font-weight: 600;
  color: #ffd166;
}
```

- [ ] **Step 3: Write `app/static/overlay/overlay.js`**

```javascript
(function () {
  const box = document.getElementById("lower-third");
  const textEl = document.getElementById("verse-text");
  const refEl = document.getElementById("verse-ref");
  let currentKey = null;
  let pending = null;
  let retryMs = 1000;

  function apply(msg) {
    textEl.textContent = msg.text;
    refEl.textContent = `${msg.book_name} ${msg.chapter}:${msg.verse} (RVR1960)`;
    box.classList.remove("len-lg", "len-xl");
    if (msg.text.length > 320) box.classList.add("len-xl");
    else if (msg.text.length > 200) box.classList.add("len-lg");
  }

  function render(msg) {
    if (msg.type !== "state") return;
    const key = `${msg.book_id}:${msg.chapter}:${msg.verse}`;
    if (pending) { clearTimeout(pending); pending = null; }

    if (!msg.visible) {
      box.classList.add("hidden");
      currentKey = key;
      pending = setTimeout(() => apply(msg), 300);
      return;
    }
    if (box.classList.contains("hidden")) {
      apply(msg);
      box.classList.remove("hidden");
      currentKey = key;
      return;
    }
    if (key === currentKey) {
      apply(msg);
      return;
    }
    // Cambio de versículo con el overlay visible: fundido salida → entrada.
    box.classList.add("hidden");
    pending = setTimeout(() => {
      apply(msg);
      box.classList.remove("hidden");
    }, 300);
    currentKey = key;
  }

  function connect() {
    const ws = new WebSocket(`ws://${location.host}/ws?role=overlay`);
    ws.onopen = () => { retryMs = 1000; };
    ws.onmessage = (ev) => render(JSON.parse(ev.data));
    ws.onclose = () => {
      box.classList.add("hidden");
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 5000);
    };
  }

  connect();
})();
```

- [ ] **Step 4: Manual verification (requires Task 6's real data)**

```bash
uv run uvicorn --factory app.main:create_app --port 8777
```

In a browser open `http://localhost:8777/overlay` (page looks empty — the box is hidden). In a second terminal:

```bash
curl -s -X POST localhost:8777/api/verse -H 'Content-Type: application/json' -d '{"book_id": 43, "chapter": 3, "verse": 16}'
curl -s -X POST localhost:8777/api/visibility -H 'Content-Type: application/json' -d '{"visible": true}'
curl -s -X POST localhost:8777/api/next
curl -s -X POST localhost:8777/api/visibility -H 'Content-Type: application/json' -d '{"visible": false}'
```

Expected: Juan 3:16 fades in on the dark band with reference `Juan 3:16 (RVR1960)`; `next` cross-fades to 3:17; the last call fades it out. Kill the server, confirm the band disappears; restart it, confirm the overlay reconnects (state resets to hidden Génesis 1:1 — in-memory state is per-process, which is fine).

- [ ] **Step 5: Commit**

```bash
git rm --cached app/static/.gitkeep 2>/dev/null; rm -f app/static/.gitkeep
git add app/static/overlay/
git commit -m "feat(overlay): add lower-third browser source page" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 11: Control panel frontend

**Files:**
- Create: `app/static/panel/index.html`
- Create: `app/static/panel/panel.css`
- Create: `app/static/panel/panel.js`

**Interfaces:**
- Consumes: `GET /api/books`, `GET /api/search`, `POST /api/verse|next|prev|visibility`, `WS /ws` (role `panel`).
- Produces: the operator UI. All copy in Spanish.

- [ ] **Step 1: Write `app/static/panel/index.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel — Biblia RVR1960</title>
<link rel="stylesheet" href="/static/panel/panel.css">
</head>
<body>
<header>
  <h1>Biblia RVR1960 · OBS</h1>
  <span id="conn-dot" class="dot off" title="Overlay desconectado"></span>
</header>
<main>
  <form id="search-form" autocomplete="off">
    <input id="search-input" type="text" placeholder="Buscar: jn 3 16 · 1co 13:4 · salmos 23" aria-label="Buscar referencia">
    <button type="submit">Ir</button>
  </form>
  <p id="search-error" class="error hidden">No encontrado</p>

  <div id="pickers">
    <select id="book-select" aria-label="Libro"></select>
    <select id="chapter-select" aria-label="Capítulo"></select>
    <select id="verse-select" aria-label="Versículo"></select>
    <button id="set-btn">Ir al versículo</button>
  </div>

  <section id="preview">
    <p id="preview-status">Oculto</p>
    <p id="preview-text"></p>
    <p id="preview-ref"></p>
  </section>

  <div id="controls">
    <button id="prev-btn">← Anterior</button>
    <button id="toggle-btn">Mostrar</button>
    <button id="next-btn">Siguiente →</button>
  </div>
</main>
<script src="/static/panel/panel.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write `app/static/panel/panel.css`**

```css
* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Helvetica Neue", Arial, sans-serif;
  background: #10141c;
  color: #f2f4f8;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.8rem 1rem;
  background: #171d29;
}

header h1 { margin: 0; font-size: 1.1rem; }

.dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  display: inline-block;
}
.dot.on { background: #2ecc71; }
.dot.off { background: #e74c3c; }

main {
  max-width: 640px;
  margin: 0 auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

#search-form { display: flex; gap: 0.5rem; }

#search-input {
  flex: 1;
  font-size: 1.1rem;
  padding: 0.7rem;
  border-radius: 8px;
  border: 1px solid #39445a;
  background: #1c2333;
  color: inherit;
}

button {
  font-size: 1.05rem;
  padding: 0.7rem 1rem;
  border: none;
  border-radius: 8px;
  background: #2d6cdf;
  color: #ffffff;
  cursor: pointer;
}

button:active { background: #1e4fa8; }

.error { color: #ff7675; margin: 0; }
.hidden { display: none; }

#pickers { display: flex; gap: 0.5rem; flex-wrap: wrap; }

#pickers select {
  flex: 1;
  min-width: 30%;
  font-size: 1.05rem;
  padding: 0.6rem;
  border-radius: 8px;
  border: 1px solid #39445a;
  background: #1c2333;
  color: inherit;
}

#pickers button { width: 100%; }

#preview {
  background: #171d29;
  border-radius: 10px;
  padding: 0.9rem 1rem;
  min-height: 6.5rem;
}

#preview.live { outline: 2px solid #2ecc71; }

#preview-status {
  margin: 0 0 0.4rem;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8fa1bf;
}

#preview.live #preview-status { color: #2ecc71; }

#preview-text { margin: 0; font-size: 1.1rem; line-height: 1.4; }

#preview-ref { margin: 0.4rem 0 0; color: #ffd166; font-weight: 600; }

#controls { display: flex; gap: 0.5rem; }

#controls button { flex: 1; padding: 1rem 0.5rem; }

#toggle-btn { background: #27ae60; }
#toggle-btn.showing { background: #c0392b; }
```

- [ ] **Step 3: Write `app/static/panel/panel.js`**

```javascript
const $ = (id) => document.getElementById(id);

let books = [];
let currentState = null;

async function api(path, options) {
  const response = await fetch(path, options);
  return response.json();
}

function postJSON(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

function fillSelect(select, values, labels) {
  select.innerHTML = "";
  values.forEach((value, i) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labels ? labels[i] : value;
    select.appendChild(option);
  });
}

function selectedBook() {
  return books.find((b) => b.id === Number($("book-select").value));
}

function populateBooks() {
  fillSelect($("book-select"), books.map((b) => b.id), books.map((b) => b.name));
  populateChapters();
}

function populateChapters() {
  const book = selectedBook();
  fillSelect($("chapter-select"), book.chapters.map((_, i) => i + 1));
  populateVerses();
}

function populateVerses() {
  const book = selectedBook();
  const chapter = Number($("chapter-select").value);
  const count = book.chapters[chapter - 1];
  fillSelect($("verse-select"), Array.from({ length: count }, (_, i) => i + 1));
}

function renderState(msg) {
  if (msg.type !== "state") return;
  currentState = msg;
  $("preview-text").textContent = msg.text;
  $("preview-ref").textContent = `${msg.book_name} ${msg.chapter}:${msg.verse} (RVR1960)`;
  $("preview-status").textContent = msg.visible ? "EN PANTALLA" : "Oculto";
  $("preview").classList.toggle("live", msg.visible);
  const toggle = $("toggle-btn");
  toggle.textContent = msg.visible ? "Ocultar" : "Mostrar";
  toggle.classList.toggle("showing", msg.visible);
  const dot = $("conn-dot");
  const connected = msg.overlays > 0;
  dot.classList.toggle("on", connected);
  dot.classList.toggle("off", !connected);
  dot.title = connected ? "Overlay conectado" : "Overlay desconectado";
}

function connect() {
  const ws = new WebSocket(`ws://${location.host}/ws?role=panel`);
  ws.onmessage = (ev) => renderState(JSON.parse(ev.data));
  ws.onclose = () => setTimeout(connect, 1500);
}

async function init() {
  books = await api("/api/books");
  populateBooks();

  $("book-select").onchange = populateChapters;
  $("chapter-select").onchange = populateVerses;

  $("set-btn").onclick = () =>
    postJSON("/api/verse", {
      book_id: Number($("book-select").value),
      chapter: Number($("chapter-select").value),
      verse: Number($("verse-select").value),
    });

  $("next-btn").onclick = () => postJSON("/api/next");
  $("prev-btn").onclick = () => postJSON("/api/prev");
  $("toggle-btn").onclick = () =>
    postJSON("/api/visibility", { visible: !(currentState && currentState.visible) });

  $("search-form").onsubmit = async (event) => {
    event.preventDefault();
    const q = $("search-input").value.trim();
    if (!q) return;
    const result = await api(`/api/search?q=${encodeURIComponent(q)}`);
    if (!result.found) {
      $("search-error").classList.remove("hidden");
      return;
    }
    $("search-error").classList.add("hidden");
    await postJSON("/api/verse", {
      book_id: result.book_id,
      chapter: result.chapter,
      verse: result.verse,
    });
    $("search-input").select();
  };

  connect();
}

init();
```

- [ ] **Step 4: Manual verification**

With the server from Task 10 still running (or restart `uv run uvicorn --factory app.main:create_app --port 8777`), open `http://localhost:8777/` and `http://localhost:8777/overlay` side by side. Verify, in order:

1. Dropdowns list 66 books; chapter/verse ranges change with the book.
2. Search `jn 3 16` + Ir → preview shows Juan 3:16; search `zzz 9 9` → "No encontrado" appears and the state is unchanged.
3. Mostrar → overlay fades in, preview shows "EN PANTALLA" (green outline), button turns red "Ocultar".
4. Siguiente/Anterior update overlay and preview together; at Génesis 1:1, Anterior does nothing.
5. Connection dot: green while the overlay tab is open, red within seconds of closing it (server broadcast on disconnect), green again on reopen.
6. Open the panel from a phone on the same Wi-Fi (`http://<mac-lan-ip>:8777/`) and confirm the buttons are usable.

- [ ] **Step 5: Commit**

```bash
git add app/static/panel/
git commit -m "feat(panel): add Spanish control panel" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 12: One-command startup and README

**Files:**
- Create: `start.sh` (executable)
- Create: `README.md`

**Interfaces:**
- Consumes: everything.
- Produces: `./start.sh` — the single command from the spec: env, data, server, browser.

- [ ] **Step 1: Write `start.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "Falta uv. Instálalo desde https://docs.astral.sh/uv/ y vuelve a intentar."
  exit 1
fi

echo "Preparando entorno..."
uv sync --quiet

if [ ! -f data/rvr1960.json ]; then
  echo "Descargando la Biblia RVR1960 (solo la primera vez)..."
  uv run fetch-bible
fi

PORT="${BIBLE_PORT:-8777}"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || echo "IP-de-esta-Mac")"

echo ""
echo "  Panel de control:  http://localhost:${PORT}/"
echo "  Panel (teléfono):  http://${LAN_IP}:${PORT}/"
echo "  Overlay para OBS:  http://localhost:${PORT}/overlay"
echo ""

( sleep 1; open "http://localhost:${PORT}/" ) &
exec uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port "${PORT}"
```

Then: `chmod +x start.sh`

- [ ] **Step 2: Write `README.md`**

````markdown
# Biblia RVR1960 para OBS

Muestra versículos de la Reina-Valera 1960 como franja inferior (lower-third)
en OBS, controlados en vivo desde un panel web en español — desde la misma
Mac o desde un teléfono en la misma red.

## Requisitos

- macOS con [uv](https://docs.astral.sh/uv/) instalado
- OBS Studio

## Uso

```bash
./start.sh
```

Eso es todo: crea el entorno, descarga la Biblia la primera vez, arranca el
servidor y abre el panel en el navegador.

## Configurar OBS (una sola vez)

1. En la escena, agrega una fuente **Navegador** (Browser Source).
2. URL: `http://localhost:8777/overlay` — Ancho: `1920`, Alto: `1080`.
3. Listo. Cuando pulses **Mostrar** en el panel, el versículo aparece abajo.

## Panel

- **Buscar**: escribe `jn 3 16`, `1co 13:4` o `salmos 23` y pulsa **Ir**.
- **← Anterior / Siguiente →**: avanza versículo por versículo.
- **Mostrar / Ocultar**: enciende o apaga la franja sin perder la posición.
- Punto verde = overlay conectado en OBS; rojo = desconectado.

Desde un teléfono en la misma red: `http://<IP-de-la-Mac>:8777/`
(la IP aparece al ejecutar `./start.sh`).

## Prueba manual antes del servicio

1. `./start.sh` y overlay agregado en OBS.
2. Busca un versículo, pulsa **Mostrar**, verifica que se ve en OBS.
3. **Siguiente** un par de veces; verifica el fundido entre versículos.
4. **Ocultar**; verifica que la franja desaparece.
5. Reinicia el servidor y refresca la fuente en OBS; todo debe reconectar.

## Nota sobre derechos

El texto RVR1960 tiene derechos de autor (Sociedades Bíblicas Unidas). Este
repositorio no incluye ni redistribuye el texto: `data/` está fuera de git y
la descarga es para uso local de la congregación.

## Desarrollo

```bash
uv run pytest        # tests
uv run fetch-bible   # re-descargar la Biblia
```
````

- [ ] **Step 3: Full-suite check and end-to-end smoke**

Run: `uv run pytest -v`
Expected: all PASSED

Run: `./start.sh`
Expected: URLs printed, browser opens the panel, server starts. In OBS, add the Browser Source per the README and run the 5-step "Prueba manual" checklist above. All five must pass.

- [ ] **Step 4: Commit**

```bash
git add start.sh README.md
git commit -m "feat(project): add one-command startup and README" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review (completed at plan time)

- **Spec coverage:** architecture (T8–T9), startup/env (T1, T12), data + copyright (T6, `.gitignore` in T1), parser formats (T5), navigation edges (T3), panel UX incl. dot and "No encontrado" (T11), overlay fade/auto-shrink/reconnect (T10), error handling (T4, T8), testing (every task + manual smoke in T12). Spec's "fetch `/api/state` on reconnect" is satisfied differently: the server pushes a fresh snapshot to every client on connect (T9) — same outcome, simpler.
- **Placeholder scan:** none.
- **Type consistency:** `VerseRef(book_id, chapter, verse)` used uniformly; `snapshot()` schema in T7 matches WS assertions in T9 and JS field access in T10–T11; `books_summary()` shape in T3 matches `/api/books` tests in T8 and `panel.js` usage in T11.
