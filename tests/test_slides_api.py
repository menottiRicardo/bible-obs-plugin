import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tiny_bible, tmp_path) -> TestClient:
    return TestClient(
        create_app(tiny_bible, token="", slides_path=tmp_path / "slides.json")
    )


def test_show_slide_changes_state(client):
    resp = client.post(
        "/api/slide", json={"text": "Bienvenidos", "caption": "Anuncios"}
    )
    assert resp.status_code == 200
    state = resp.json()
    assert state["mode"] == "slide"
    assert state["visible"] is True
    assert state["text"] == "Bienvenidos"
    assert state["caption"] == "Anuncios"


def test_show_slide_strips_and_rejects_empty_text(client):
    resp = client.post("/api/slide", json={"text": "   "})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Texto vacío"


def test_show_slide_rejects_too_long_text(client):
    resp = client.post("/api/slide", json={"text": "x" * 501})
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Texto demasiado largo"


def test_verse_action_after_slide_returns_to_verse_mode(client):
    client.post("/api/slide", json={"text": "Aviso"})
    state = client.post("/api/next").json()
    assert state["mode"] == "verse"
    assert state["text"] == "Segundo versículo."


def test_slides_crud_roundtrip(client):
    created = client.post(
        "/api/slides", json={"text": "Bienvenidos", "caption": "Anuncios"}
    ).json()
    assert created == {"id": 1, "text": "Bienvenidos", "caption": "Anuncios"}
    assert client.get("/api/slides").json() == [created]

    updated = client.put(
        "/api/slides/1", json={"text": "Bienvenida", "caption": ""}
    ).json()
    assert updated == {"id": 1, "text": "Bienvenida", "caption": ""}

    assert client.delete("/api/slides/1").json() == {"ok": True}
    assert client.get("/api/slides").json() == []


def test_saving_a_slide_does_not_touch_screen_state(client):
    client.post("/api/slides", json={"text": "Guardado"})
    state = client.get("/api/state").json()
    assert state["mode"] == "verse"
    assert state["visible"] is False


def test_unknown_slide_id_is_404(client):
    assert client.put("/api/slides/99", json={"text": "x"}).status_code == 404
    assert client.delete("/api/slides/99").status_code == 404


def test_slide_is_broadcast_to_overlay(client):
    with client.websocket_connect("/ws?role=overlay") as ws:
        ws.receive_json()  # snapshot inicial
        client.post("/api/slide", json={"text": "Bienvenidos"})
        msg = ws.receive_json()
        assert msg["mode"] == "slide"
        assert msg["text"] == "Bienvenidos"


def test_slide_endpoints_require_token(tiny_bible, tmp_path):
    client = TestClient(
        create_app(tiny_bible, token="s3", slides_path=tmp_path / "slides.json")
    )
    assert client.post("/api/slide", json={"text": "x"}).status_code == 401
    assert client.get("/api/slides").status_code == 401
    assert client.get("/api/slides?token=s3").status_code == 200
