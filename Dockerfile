# syntax=docker/dockerfile:1

FROM alpine:3.18 AS APP

ENV S6_SERVICES_GRACETIME=30000 \
    S6_KILL_GRACETIME=60000 \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
    S6_SYNC_DISKS=1 \
    TERM="xterm" \
    HOME="/ab" \
    LANG="C.UTF-8" \
    TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022

WORKDIR /app

COPY backend/requirements.txt .
RUN set -ex && \
    apk add --no-cache \
        bash \
        ca-certificates \
        coreutils \
        curl \
        jq \
        netcat-openbsd \
        procps-ng \
        python3 \
        py3-bcrypt \
        py3-pip \
        s6-overlay \
        shadow \
        tzdata && \
    python3 -m pip install --no-cache-dir --upgrade pip && \
    sed -i '/bcrypt/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    # Add user
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /ab -s /bin/bash -u 911 && \
    # Clear
    rm -rf \
        /ab/.cache \
        /tmp/*

COPY --chmod=755 backend/src/. .
COPY --chmod=755 docker/ /

ENTRYPOINT [ "/init" ]

EXPOSE 7892
VOLUME [ "/app/config" , "/app/data" ]
