# ── base : ce qui est commun ──
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN useradd --create-home app
COPY pyproject.toml uv.lock ./

# ── ingest : la collecte (dépendances principales seulement) ──
FROM base AS ingest
RUN uv sync --locked --no-dev --no-default-groups --no-install-project
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-default-groups
USER app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["irail-ingestion"]

# ── transform : la transformation (+ le groupe transform) ──
FROM base AS transform
RUN uv sync --locked --no-dev --no-default-groups --group transform --no-install-project
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-default-groups --group transform
USER app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["irail-transform"]
