# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.5-python3.13-alpine AS builder

WORKDIR /app
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

# 更新签名公钥：在线更新的信任根。必须位于覆盖层不会替换的位置（/app 下、
# 而非 /app/module 内），boot_overlay 每次启动都用它验签留存的 bundle。私钥
# 只在 CI 的 UPDATE_SIGNING_KEY secret 里。它随 src 一起 COPY 进来，这里显式
# 再放一次以固化信任根位置、防止后续目录调整把它漏掉。
COPY backend/src/ab_update_pubkey.pem /app/ab_update_pubkey.pem

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
