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
