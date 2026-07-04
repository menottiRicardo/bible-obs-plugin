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
