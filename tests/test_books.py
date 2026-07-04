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
