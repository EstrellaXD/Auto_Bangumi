# syntax=docker/dockerfile:1
FROM python:3.11-buster AS build

WORKDIR /install
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip && \
    pip install -r requirements.txt --prefix="/install"

FROM python:3.11-alpine

ENV TZ=Asia/Shanghai \
    PUID=0 \
    PGID=0 \
    UMASK=022

WORKDIR /app

RUN apk add --no-cache \
        curl \
        su-exec \
        dumb-init \
        bash \
        unzip \
    && \
    # Download WebUI
    WEBUI_TAG=$(curl 'https://api.github.com/repos/Rewrite0/Auto_Bangumi_WebUI/releases/latest' | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g') && \
    wget "https://github.com/Rewrite0/Auto_Bangumi_WebUI/releases/download/${WEBUI_TAG}/dist.zip" -O /tmp/dist.zip && \
    unzip /tmp/dist.zip -d /tmp/web && \
    mv /tmp/web/dist /app/templates && \
    # Clear
    rm -rf \
        /var/cache/apk/* \
        /root/.cache \
        /tmp/*

COPY --chmod=777 --from=build /install /usr/local
COPY --chmod=755 . /app

ENTRYPOINT [ "/app/entrypoint.sh" ]

EXPOSE 7892

VOLUME [ "/config" , "/data" ]