# ── Stage 1: Build ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY clip.py ./

RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Runtime ────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN useradd --create-home appuser
USER appuser

WORKDIR /app

ENV PYCLIP_CACHE_DIR=/output/.pyclip-cache

ENTRYPOINT ["pyclip"]
