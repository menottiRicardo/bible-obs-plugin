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
