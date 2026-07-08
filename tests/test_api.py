import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tiny_bible, tmp_path) -> TestClient:
    return TestClient(
        create_app(tiny_bible, token="", slides_path=tmp_path / "slides.json")
    )


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
