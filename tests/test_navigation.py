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
