FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1

# Dependencias primero, para cachear la capa entre builds.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
RUN uv sync --frozen --no-dev

# El texto RVR1960 se descarga al construir: la imagen queda en el
# registro privado de Railway, no se publica ni se sube al repo.
RUN uv run fetch-bible

EXPOSE 8777
CMD uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port ${PORT:-8777}
