# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.5-python3.13-alpine AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY backend/src ./src


FROM python:3.13-alpine AS runtime

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

# uv 二进制 + 基线 lock：在线自动更新落地时，若覆盖层的 uv.lock 相对基线变化，
# entrypoint 会用 uv 按锁文件把依赖同步到 /app/.venv。
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /app/uv.lock /app/uv.lock

# 构建期写入镜像基线版本，供 boot_overlay 判断“镜像 vs 覆盖层”谁更新，以及
# 在线更新的 min_image_version 兼容性检查。CI 通过 build-arg 注入真实版本。
ARG VERSION=DEV_VERSION
RUN echo "${VERSION}" > /app/IMAGE_VERSION

# Add user
RUN mkdir -p /home/ab && \
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /home/ab -s /sbin/nologin -u 911

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 7892
VOLUME ["/app/config", "/app/data"]

# Liveness probe against the unauthenticated /health route; give the app
# room to run migrations on first boot before failures count.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:7892/health || exit 1

ENTRYPOINT ["tini", "-g", "--", "/entrypoint.sh"]
