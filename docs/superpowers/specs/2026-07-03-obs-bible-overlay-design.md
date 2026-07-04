# OBS Bible Verse Overlay — Design

**Date:** 2026-07-03
**Status:** Approved (brainstorming session)

## Goal

Show Reina Valera 1960 (RVR1960) Bible verses as a lower-third overlay in OBS
during live church streams. One verse on screen at a time, controlled live from
a web control panel (Spanish UI) on the streaming Mac or a phone on the same
network. Everything runs locally — no internet dependency during the service.

## Decisions (from brainstorming)

| Topic         | Decision                                             |
| ------------- | ---------------------------------------------------- |
| Integration   | OBS Browser Source + local FastAPI server            |
| Control       | Web control panel (desktop or phone on LAN)          |
| Bible data    | Offline local JSON, fetched once by a script         |
| Granularity   | Exactly one verse at a time                          |
| UI language   | Spanish                                              |
| Platform      | macOS (streaming machine)                            |
| Startup       | Single command `./start.sh`; env auto-created via uv |

## Architecture

One Python process (FastAPI + uvicorn, Python ≥3.11, managed with `uv`) serving:

- **`/overlay`** — page added to OBS as a Browser Source (1920×1080, transparent
  background). Renders the lower-third. Holds a WebSocket to the server;
  re-syncs state on reconnect (OBS refresh, server restart).
- **`/`** — control panel (Spanish, phone-friendly). Sets the current verse via
  REST; receives state updates over the same WebSocket channel so preview and
  multiple panels stay in sync.
- **REST + WebSocket** — server holds current state in memory (current verse +
  visibility) and broadcasts every change to all connected clients.

Frontend is plain HTML/CSS/JS (no build step). Bible text is one JSON file
loaded fully into memory at startup (~31k verses, a few MB).

## Components

### Project layout

```
bible-plugin/
  pyproject.toml          # deps: fastapi, uvicorn, httpx (fetch only), pydantic-settings
  start.sh                # the one command: env + data + server + open panel
  scripts/fetch_bible.py  # `uv run fetch-bible` — one-time RVR1960 download
  app/
    settings.py           # pydantic-settings: port (default 8777), data path
    bible.py              # data load/validation, navigation, reference parsing
    state.py              # current verse + visibility; WS broadcast
    main.py               # FastAPI app: routes, WebSocket, static files
    static/
      overlay/            # index.html, overlay.css, overlay.js
      panel/              # index.html, panel.css, panel.js
  data/rvr1960.json       # gitignored (copyrighted text; local use only)
  tests/                  # pytest, asyncio_mode=auto
  docs/superpowers/...    # this spec + plans
```

### Startup (`./start.sh`)

Idempotent, one command, first run and every run:

1. `uv sync` — creates/updates `.venv` automatically.
2. If `data/rvr1960.json` is missing → run `uv run fetch-bible`.
3. Start server (`uv run uvicorn app.main:app --host 0.0.0.0 --port 8777`).
4. Open `http://localhost:8777/` in the default browser; print the overlay URL
   (`http://localhost:8777/overlay`) and the LAN panel URL for phones.

### Bible data

- `fetch_bible.py` downloads RVR1960 from a pinned public source URL (chosen at
  implementation time, checksum pinned) and normalizes to:

```json
{
  "version": "RVR1960",
  "books": [
    {
      "id": 43,
      "name": "Juan",
      "abbrevs": ["jn", "juan", "jhn"],
      "chapters": [["verse 1 text", "verse 2 text", "..."]]
    }
  ]
}
```

- Load-time validation: exactly 66 books, canonical chapter count per book,
  every chapter non-empty. Missing/corrupt file → exit with clear message:
  “Falta data/rvr1960.json — ejecuta `uv run fetch-bible`”.
- `data/` is gitignored: the repo ships the fetch script, never the copyrighted
  text.

### Reference parsing (quick search)

- Accepts `jn 3 16`, `juan 3:16`, `Juan 3.16`, `1co 13 4`, `1 corintios 13:4`.
- Normalizes case/accents; matches against per-book abbreviation lists.
- No match → panel shows “No encontrado”; on-air verse unchanged.

### API

| Endpoint               | Method | Purpose                                        |
| ---------------------- | ------ | ---------------------------------------------- |
| `/api/books`           | GET    | Books with chapter/verse counts (for pickers)  |
| `/api/state`           | GET    | Current verse + visibility                     |
| `/api/verse`           | POST   | Set current verse `{book_id, chapter, verse}`  |
| `/api/next` `/api/prev`| POST   | Step one verse (crosses chapter/book bounds)   |
| `/api/visibility`      | POST   | `{visible: bool}` — Mostrar/Ocultar            |
| `/api/search?q=`       | GET    | Parse quick-search string → reference or null  |
| `/ws`                  | WS     | State broadcasts to overlay(s) and panel(s)    |

WS message (server → clients):
`{"type": "state", "visible": true, "book_id": 43, "book_name": "Juan", "chapter": 3, "verse": 16, "text": "Porque de tal manera..."}`

## Control panel UX (Spanish)

- Quick-search box (primary flow) + Libro/Capítulo/Versículo dropdowns
  (constrained to valid values — invalid references unselectable).
- Big buttons: **← Anterior**, **Siguiente →**, **Mostrar/Ocultar** (toggle;
  hiding keeps position).
- Live preview of what is on stream; connection dot (green = overlay connected).
- Responsive layout, large touch targets for phone use.

## Overlay appearance & behavior

- Lower-third band at the bottom: verse text, then reference —
  *“…” — Juan 3:16 (RVR1960)*.
- Dark translucent band, white text, accent color on the reference. One default
  theme in plain CSS (no theming system in v1).
- ~300 ms fade on verse change and show/hide. Long verses shrink font
  progressively so text never overflows the band.
- Auto-reconnect WebSocket with backoff; fetch `/api/state` on reconnect.

## Error handling

- Invalid selections impossible via constrained dropdowns.
- `Siguiente` at Apocalipsis 22:21 and `Anterior` at Génesis 1:1: no-op (no
  wraparound).
- Overlay disconnect → red dot on panel; overlay retries until reconnected.
- Data file missing/corrupt → fail fast at startup with the fetch instruction.

## Testing

- **Unit:** reference parser (abbreviations, all accepted formats, accents),
  navigation across chapter/book boundaries and at canon edges, data validation.
- **API:** endpoints + WS broadcast via FastAPI test client (pytest,
  `asyncio_mode=auto`).
- **Manual smoke (documented in README):** `./start.sh`, add Browser Source in
  OBS, change verses from a phone, kill/restart server, refresh source.

## Out of scope (v1)

- Multiple Bible versions; verse ranges; playlists/scheduled passages;
- Theming system / style editor; OBS hotkeys; Windows/Linux launch scripts;
- Authentication on the panel (LAN-only, trusted network).
