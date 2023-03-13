# syntax=docker/dockerfile:1
FROM python:3.11-alpine

COPY requirements.txt .

RUN pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.cloud.tencent.com && \
    pip install -r requirements.txt


RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.cloud.tencent.com/g' /etc/apk/repositories && \
    apk add --no-cache \
    curl \
    shadow \
    su-exec \
    bash

ENV TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022

WORKDIR /

# Download WebUI
RUN wget "https://github.com/Rewrite0/Auto_Bangumi_WebUI/releases/download/$(curl 'https://api.github.com/repos/Rewrite0/Auto_Bangumi_WebUI/releases/latest' | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g')/dist.zip" && \
    unzip dist.zip && \
    mv dist templates

COPY . .

RUN addgroup -S auto_bangumi -g 1000 && \
    adduser -S auto_bangumi -G auto_bangumi -h /home/auto_bangumi -u 1000 && \
    usermod -s /bin/bash auto_bangumi && \
    mkdir -p "/config" && \
    mkdir -p "/data" && \
    chmod a+x \
        run.sh

EXPOSE 7892

VOLUME [ "/config" , "/data"]

CMD ["sh", "run.sh"]
