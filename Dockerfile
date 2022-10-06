# syntax=docker/dockerfile:1
FROM python:3.10-buster AS build

RUN mkdir /install
WORKDIR /install
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip \
    && pip install -r requirements.txt --prefix="/install"

FROM python:3.10-alpine

WORKDIR /src

COPY --from=build --chmod=777 /install /usr/local
ADD ./src /src

RUN apk add --update --no-cache \
    curl \
    shadow \
    su-exec \
    bash

RUN addgroup -S auto_bangumi && \
    adduser -S auto_bangumi -G auto_bangumi -h /home/auto_bangumi && \
    usermod -s /bin/bash auto_bangumi && \
    mkdir -p "/config" && \
    chmod a+x run.sh && \
    chmod a+x getWebUI.sh

ENV TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000

EXPOSE 7892

VOLUME [ "/config" ]

CMD ["sh", "run.sh"]
