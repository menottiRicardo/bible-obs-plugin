from __future__ import annotations

from typing import Any

from app.bible import Bible, VerseRef
from app.books import BY_ID


class OverlayState:
    def __init__(self, bible: Bible):
        self._bible = bible
        self.ref: VerseRef = bible.first_ref()
        self.visible: bool = False
        self.mode: str = "verse"
        self.slide_text: str = ""
        self.slide_caption: str = ""

    def set_verse(self, ref: VerseRef) -> None:
        self.ref = ref
        self.mode = "verse"

    def set_slide(self, text: str, caption: str = "") -> None:
        self.mode = "slide"
        self.slide_text = text
        self.slide_caption = caption
        self.visible = True

    def step(self, direction: int) -> bool:
        self.mode = "verse"
        moved = (
            self._bible.next_ref(self.ref)
            if direction > 0
            else self._bible.prev_ref(self.ref)
        )
        if moved is None:
            return False
        self.ref = moved
        return True

    def set_visible(self, visible: bool) -> None:
        self.visible = visible

    def snapshot(self) -> dict:
        in_slide = self.mode == "slide"
        return {
            "type": "state",
            "mode": self.mode,
            "visible": self.visible,
            "book_id": self.ref.book_id,
            "book_name": BY_ID[self.ref.book_id].name,
            "chapter": self.ref.chapter,
            "verse": self.ref.verse,
            "text": self.slide_text if in_slide else self._bible.get_text(self.ref),
            "caption": self.slide_caption if in_slide else "",
        }


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[Any, str] = {}

    def add(self, ws: Any, role: str) -> None:
        self._conns[ws] = role

    def remove(self, ws: Any) -> None:
        self._conns.pop(ws, None)

    @property
    def overlay_count(self) -> int:
        return sum(1 for role in self._conns.values() if role == "overlay")

    async def broadcast(self, message: dict) -> None:
        for ws in list(self._conns):
            try:
                await ws.send_json(message)
            except Exception:
                self.remove(ws)
