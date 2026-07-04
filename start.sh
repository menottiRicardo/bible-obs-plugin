#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "Falta uv. Instálalo desde https://docs.astral.sh/uv/ y vuelve a intentar."
  exit 1
fi

echo "Preparando entorno..."
uv sync --quiet

if [ ! -f data/rvr1960.json ]; then
  echo "Descargando la Biblia RVR1960 (solo la primera vez)..."
  uv run fetch-bible
fi

PORT="${BIBLE_PORT:-8777}"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || echo "IP-de-esta-Mac")"

echo ""
echo "  Panel de control:  http://localhost:${PORT}/"
echo "  Panel (teléfono):  http://${LAN_IP}:${PORT}/"
echo "  Overlay para OBS:  http://localhost:${PORT}/overlay"
echo ""

( sleep 1; open "http://localhost:${PORT}/" ) &
exec uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port "${PORT}"
