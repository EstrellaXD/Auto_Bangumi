
# syntax=docker/dockerfile:1

# 构建阶段
FROM alpine:3.18 AS builder


# 安装构建依赖
RUN apk add --no-cache \
    python3 \
    python3-dev \
    gcc \
    musl-dev \
    libffi-dev \
    rust \
    cargo \
    curl

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 设置工作目录
WORKDIR /build

# 复制依赖文件并安装（这层会被缓存，除非依赖文件改变）
COPY backend/pyproject.toml backend/uv.lock backend/requirements.txt ./

# 安装Python依赖
RUN uv sync --frozen --no-dev

# 运行阶段
FROM alpine:3.18 AS runtime

ENV LANG="C.UTF-8" \
    TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 只安装运行时依赖
RUN set -ex && \
    apk add --no-cache \
    bash \
    busybox-suid \
    python3 \
    py3-aiohttp \
    py3-bcrypt \
    curl \
    su-exec \
    shadow \
    tini \
    openssl \
    tzdata && \
    # 添加用户
    mkdir -p /home/ab && \
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /home/ab -s /sbin/nologin -u 911 && \
    # 清理缓存
    rm -rf /var/cache/apk/* /tmp/*

# 从构建阶段复制虚拟环境
# COPY --from=builder $VENV_PATH $VENV_PATH
COPY --from=builder /build/.venv /app/.venv

# 复制应用代码（放在最后，因为代码变更最频繁）
COPY --chmod=755 backend/src/. ./src
COPY --chmod=755 backend/dist/. ./dist
COPY --chmod=755 entrypoint.sh /entrypoint.sh

ENTRYPOINT ["tini", "-g", "--", "/entrypoint.sh"]
EXPOSE 7892
VOLUME [ "/app/config" , "/app/data" ]


