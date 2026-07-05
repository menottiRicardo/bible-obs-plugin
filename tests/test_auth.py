import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app

TOKEN = "secreto-prueba"


@pytest.fixture
def client(tiny_bible) -> TestClient:
    return TestClient(create_app(tiny_bible, token=TOKEN))


def test_api_rejects_missing_token(client):
    assert client.get("/api/state").status_code == 401


def test_api_rejects_wrong_token(client):
    assert client.get("/api/state?token=malo").status_code == 401


def test_api_accepts_valid_token(client):
    response = client.get("/api/state?token=secreto-prueba")
    assert response.status_code == 200
    assert response.json()["type"] == "state"


def test_post_routes_require_token(client):
    assert client.post("/api/next").status_code == 401
    assert client.post("/api/next?token=secreto-prueba").status_code == 200


def test_pages_reject_missing_token(client):
    response = client.get("/")
    assert response.status_code == 401
    assert "Acceso no autorizado" in response.text
    assert client.get("/overlay").status_code == 401


def test_pages_accept_valid_token(client):
    assert client.get("/?token=secreto-prueba").status_code == 200
    assert client.get("/overlay?token=secreto-prueba").status_code == 200


def test_without_configured_token_everything_stays_open(tiny_bible):
    open_client = TestClient(create_app(tiny_bible, token=""))
    assert open_client.get("/api/state").status_code == 200
    assert open_client.get("/").status_code == 200


def test_ws_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?role=overlay"):
            pass


def test_ws_rejects_wrong_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?role=overlay&token=malo"):
            pass


def test_ws_accepts_valid_token(client):
    with client.websocket_connect(f"/ws?role=overlay&token={TOKEN}") as ws:
        assert ws.receive_json()["type"] == "state"
