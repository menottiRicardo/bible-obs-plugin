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
        "mode": "verse",
        "visible": False,
        "book_id": 1,
        "book_name": "Génesis",
        "chapter": 1,
        "verse": 1,
        "text": "En el principio creó Dios los cielos y la tierra.",
        "caption": "",
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


def test_set_slide_shows_message_and_keeps_ref(tiny_bible):
    state = OverlayState(tiny_bible)
    state.set_slide("Bienvenidos", "Anuncios")
    snap = state.snapshot()
    assert snap["mode"] == "slide"
    assert snap["visible"] is True
    assert snap["text"] == "Bienvenidos"
    assert snap["caption"] == "Anuncios"
    # La referencia bíblica no se pierde.
    assert (snap["book_id"], snap["chapter"], snap["verse"]) == (1, 1, 1)


def test_verse_actions_return_to_verse_mode(tiny_bible):
    state = OverlayState(tiny_bible)
    state.set_slide("Bienvenidos")
    assert state.step(1) is True
    snap = state.snapshot()
    assert snap["mode"] == "verse"
    assert snap["caption"] == ""
    assert snap["text"] == "Segundo versículo."

    state.set_slide("Otro mensaje")
    state.set_verse(VerseRef(43, 1, 1))
    assert state.snapshot()["mode"] == "verse"


def test_step_at_edge_still_returns_to_verse_mode(tiny_bible):
    state = OverlayState(tiny_bible)
    state.set_verse(VerseRef(1, 1, 1))
    state.set_slide("Mensaje")
    assert state.step(-1) is False
    assert state.snapshot()["mode"] == "verse"


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
