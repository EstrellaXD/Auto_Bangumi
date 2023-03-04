# syntax=docker/dockerfile:1
FROM python:3.11-buster AS build

RUN mkdir /install
WORKDIR /install
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip \
    && pip install -r requirements.txt --prefix="/install"

FROM python:3.11-alpine

ENV TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022

WORKDIR /app

COPY --from=build --chmod=777 /install /usr/local
COPY --chmod=755 . .

RUN apk add --no-cache \
    curl \
    shadow \
    su-exec \
    bash

# Download WebUI
RUN wget https://github.com/Rewrite0/Auto_Bangumi_WebUI/releases/download/v1.0.4/dist.zip && \
    unzip dist.zip && \
    mv dist template

RUN addgroup -S auto_bangumi -g 1000 && \
    adduser -S auto_bangumi -G auto_bangumi -h /home/auto_bangumi -u 1000 && \
    usermod -s /bin/bash auto_bangumi && \
    mkdir -p "/config" && \
    chmod a+x \
        run.sh \
        setID.sh

EXPOSE 7892

VOLUME [ "/config" , "/data"]

CMD ["sh", "run.sh"]
