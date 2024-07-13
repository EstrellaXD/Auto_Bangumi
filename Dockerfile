# syntax=docker/dockerfile:1

FROM alpine:3.18

ENV LANG="C.UTF-8" \
    TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022

WORKDIR /app

COPY backend/requirements.txt .
RUN set -ex && \
    apk add --no-cache \
        bash \
        busybox-suid \
        python3 \
        py3-aiohttp \
        py3-bcrypt \
        py3-pip \
        su-exec \
        shadow \
        tini \
        curl \
        openssl \
        tzdata && \
    python3 -m pip install --no-cache-dir --upgrade pip && \
    sed -i '/bcrypt/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    # Add user
    mkdir -p /home/ab && \
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /home/ab -s /sbin/nologin -u 911 && \
    # Clear
    rm -rf \
        /root/.cache \
        /tmp/*

COPY --chmod=755 backend/src/. .
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Add healthcheck endpoint
HEALTHCHECK --interval=5s --timeout=10s --retries=3 CMD curl --silent --fail http://localhost:7892/api/v1/health || exit 1

ENTRYPOINT ["tini", "-g", "--", "/entrypoint.sh"]

EXPOSE 7892
VOLUME [ "/app/config" , "/app/data" ]
