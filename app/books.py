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
