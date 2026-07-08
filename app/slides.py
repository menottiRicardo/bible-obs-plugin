from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SlideLibrary:
    """Lista persistente de mensajes reutilizables (data/slides.json)."""

    def __init__(self, path: Path):
        self._path = path
        self._slides: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("se esperaba una lista")
            self._slides = [
                {
                    "id": int(item["id"]),
                    "text": str(item["text"]),
                    "caption": str(item.get("caption", "")),
                }
                for item in data
            ]
        except (ValueError, KeyError, TypeError):
            backup = self._path.with_suffix(".json.bak")
            self._path.replace(backup)
            self._slides = []
            logger.warning("Archivo de mensajes ilegible; movido a %s", backup)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(self._slides, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self._path)

    def list(self) -> list[dict]:
        return [dict(slide) for slide in self._slides]

    def add(self, text: str, caption: str) -> dict:
        slide = {
            "id": max((s["id"] for s in self._slides), default=0) + 1,
            "text": text,
            "caption": caption,
        }
        self._slides.append(slide)
        self._save()
        return dict(slide)

    def update(self, slide_id: int, text: str, caption: str) -> dict | None:
        for slide in self._slides:
            if slide["id"] == slide_id:
                slide["text"] = text
                slide["caption"] = caption
                self._save()
                return dict(slide)
        return None

    def delete(self, slide_id: int) -> bool:
        remaining = [s for s in self._slides if s["id"] != slide_id]
        if len(remaining) == len(self._slides):
            return False
        self._slides = remaining
        self._save()
        return True
