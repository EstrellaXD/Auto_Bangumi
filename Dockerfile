# syntax=docker/dockerfile:1

FROM python:3.11-alpine AS Builder
WORKDIR /app
COPY requirements.txt .

RUN   --mount=target=/root/.cache/pip,type=cache,sharing=locked \
    python3 -m pip install --upgrade pip && \
    pip install cython && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf \
        /root/.cache \
        /tmp/*

FROM scratch AS APP

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

COPY --from=Builder / /

WORKDIR /app

RUN apk add --no-cache \
        curl \
        wget \
        jq \
        shadow \
        s6-overlay \
        bash && \
    # Download WebUI
    wget "https://github.com/Rewrite0/Auto_Bangumi_WebUI/releases/latest/download/dist.zip" -O /tmp/dist.zip && \
    unzip -q -d /tmp /tmp/dist.zip && \
    mv /tmp/dist /app/templates && \
    # Add user
    mkdir /ab && \
    addgroup -S ab -g 911 && \
    adduser -S ab -G ab -h /ab -s /bin/bash -u 911 && \
    rm -rf \
        /root/.cache \
        /tmp/*

COPY --chmod=755 src/. .
COPY --chmod=755 ./docker /

ENTRYPOINT [ "/init" ]

EXPOSE 7892
VOLUME [ "/app/config" , "/app/data" ]
