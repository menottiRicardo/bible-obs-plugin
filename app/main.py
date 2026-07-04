import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import refparse
from app.bible import Bible, BibleDataError, VerseRef
from app.settings import settings
from app.state import ConnectionManager, OverlayState

STATIC_DIR = Path(__file__).parent / "static"


class VersePayload(BaseModel):
    book_id: int
    chapter: int
    verse: int


class VisibilityPayload(BaseModel):
    visible: bool


def create_app(bible: Bible | None = None) -> FastAPI:
    if bible is None:
        try:
            bible = Bible.load(settings.data_path)
        except BibleDataError as exc:
            sys.exit(str(exc))

    app = FastAPI(title="bible-obs")
    state = OverlayState(bible)
    manager = ConnectionManager()

    def current_state() -> dict:
        message = state.snapshot()
        message["overlays"] = manager.overlay_count
        return message

    async def push_state() -> dict:
        message = current_state()
        await manager.broadcast(message)
        return message

    @app.get("/api/books")
    def books() -> list[dict]:
        return bible.books_summary()

    @app.get("/api/state")
    def get_state() -> dict:
        return current_state()

    @app.post("/api/verse")
    async def set_verse(payload: VersePayload) -> dict:
        ref = VerseRef(payload.book_id, payload.chapter, payload.verse)
        if not bible.exists(ref):
            raise HTTPException(status_code=422, detail="Referencia inválida")
        state.set_verse(ref)
        return await push_state()

    @app.post("/api/next")
    async def next_verse() -> dict:
        state.step(1)
        return await push_state()

    @app.post("/api/prev")
    async def prev_verse() -> dict:
        state.step(-1)
        return await push_state()

    @app.post("/api/visibility")
    async def set_visibility(payload: VisibilityPayload) -> dict:
        state.set_visible(payload.visible)
        return await push_state()

    @app.get("/api/search")
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

    @app.get("/")
    def panel_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "panel" / "index.html")

    @app.get("/overlay")
    def overlay_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "overlay" / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
