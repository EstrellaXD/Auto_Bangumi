# syntax=docker/dockerfile:1

FROM alpine:3.18

ENV LANG="C.UTF-8" \
    TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy Python project files
COPY backend/pyproject.toml backend/uv.lock ./

RUN set -ex && \
    apk add --no-cache \
        bash \
        busybox-suid \
        python3 \
        python3-dev \
        py3-aiohttp \
        py3-bcrypt \
        curl \
        gcc \
        musl-dev \
        libffi-dev \
        su-exec \
        shadow \
        tini \
        openssl \
        tzdata \
        rust \
        cargo && \
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    # Verify uv installation and show version
    uv --version && \
    # Check if lock file exists and is readable
    ls -la uv.lock && \
    # Install dependencies using uv
    uv sync --frozen --no-dev && \
    # Remove build dependencies to reduce image size
    apk del \
        rust \
        cargo \
        gcc \
        musl-dev \
        libffi-dev \
        python3-dev && \
    # Add user
    mkdir -p /home/ab && \
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /home/ab -s /sbin/nologin -u 911 && \
    # Clear
    rm -rf \
        /root/.cache \
        /root/.local \
        /tmp/*

COPY --chmod=755 backend/src/. .
COPY --chmod=755 entrypoint.sh /entrypoint.sh

ENTRYPOINT ["tini", "-g", "--", "/entrypoint.sh"]

EXPOSE 7892
VOLUME [ "/app/config" , "/app/data" ]