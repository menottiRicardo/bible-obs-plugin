import secrets
import sys
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import refparse
from app.bible import Bible, BibleDataError, VerseRef
from app.settings import settings
from app.state import ConnectionManager, OverlayState

STATIC_DIR = Path(__file__).parent / "static"

DENIED_HTML = """<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>No autorizado</title></head>
<body style="font-family: system-ui, sans-serif; background: #111; color: #eee;
             text-align: center; padding-top: 4rem;">
  <h1>Acceso no autorizado</h1>
  <p>Falta el token o no es válido. Abre el enlace completo con <code>?token=...</code></p>
</body>
</html>
"""


class VersePayload(BaseModel):
    book_id: int
    chapter: int
    verse: int


class VisibilityPayload(BaseModel):
    visible: bool


def create_app(bible: Bible | None = None, token: str | None = None) -> FastAPI:
    if bible is None:
        try:
            bible = Bible.load(settings.data_path)
        except BibleDataError as exc:
            sys.exit(str(exc))
    required_token = settings.token if token is None else token

    app = FastAPI(title="bible-obs")
    state = OverlayState(bible)
    manager = ConnectionManager()

    def token_ok(provided: str | None) -> bool:
        if not required_token:
            return True
        return provided is not None and secrets.compare_digest(provided, required_token)

    def require_token(token: str | None = None) -> None:
        if not token_ok(token):
            raise HTTPException(status_code=401, detail="No autorizado")

    api = APIRouter(prefix="/api", dependencies=[Depends(require_token)])

    def current_state() -> dict:
        message = state.snapshot()
        message["overlays"] = manager.overlay_count
        return message

    async def push_state() -> dict:
        message = current_state()
        await manager.broadcast(message)
        return message

    @api.get("/books")
    def books() -> list[dict]:
        return bible.books_summary()

    @api.get("/state")
    def get_state() -> dict:
        return current_state()

    @api.post("/verse")
    async def set_verse(payload: VersePayload) -> dict:
        ref = VerseRef(payload.book_id, payload.chapter, payload.verse)
        if not bible.exists(ref):
            raise HTTPException(status_code=422, detail="Referencia inválida")
        state.set_verse(ref)
        return await push_state()

    @api.post("/next")
    async def next_verse() -> dict:
        state.step(1)
        return await push_state()

    @api.post("/prev")
    async def prev_verse() -> dict:
        state.step(-1)
        return await push_state()

    @api.post("/visibility")
    async def set_visibility(payload: VisibilityPayload) -> dict:
        state.set_visible(payload.visible)
        return await push_state()

    @api.get("/search")
    def search(q: str = "") -> dict:
        ref = refparse.parse(q)
        if ref is None or not bible.exists(ref):
            return {"found": False}
        return {
            "found": True,
            "book_id": ref.book_id,
            "chapter": ref.chapter,
            "verse": ref.verse,
        }

    app.include_router(api)

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket) -> None:
        role = ws.query_params.get("role", "panel")
        await ws.accept()
        manager.add(ws, role)
        await push_state()
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            manager.remove(ws)
            await push_state()

    @app.get("/")
    def panel_page(token: str | None = None) -> Response:
        if not token_ok(token):
            return HTMLResponse(DENIED_HTML, status_code=401)
        return FileResponse(STATIC_DIR / "panel" / "index.html")

    @app.get("/overlay")
    def overlay_page(token: str | None = None) -> Response:
        if not token_ok(token):
            return HTMLResponse(DENIED_HTML, status_code=401)
        return FileResponse(STATIC_DIR / "overlay" / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
