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
