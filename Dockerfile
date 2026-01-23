# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.5-python3.12-alpine AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY backend/src ./src


FROM python:3.12-alpine AS runtime

RUN apk add --no-cache \
    bash \
    su-exec \
    shadow \
    tini \
    tzdata

ENV LANG="C.UTF-8" \
    TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022

WORKDIR /app

# Copy venv and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src .
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Add user
RUN mkdir -p /home/ab && \
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /home/ab -s /sbin/nologin -u 911

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 7892
VOLUME ["/app/config", "/app/data"]

ENTRYPOINT ["tini", "-g", "--", "/entrypoint.sh"]
