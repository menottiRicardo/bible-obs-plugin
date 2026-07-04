from __future__ import annotations

from typing import Any

from app.bible import Bible, VerseRef
from app.books import BY_ID


class OverlayState:
    def __init__(self, bible: Bible):
        self._bible = bible
        self.ref: VerseRef = bible.first_ref()
        self.visible: bool = False

    def set_verse(self, ref: VerseRef) -> None:
        self.ref = ref

    def step(self, direction: int) -> bool:
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
        return {
            "type": "state",
            "visible": self.visible,
            "book_id": self.ref.book_id,
            "book_name": BY_ID[self.ref.book_id].name,
            "chapter": self.ref.chapter,
            "verse": self.ref.verse,
            "text": self._bible.get_text(self.ref),
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
