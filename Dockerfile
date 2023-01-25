# syntax=docker/dockerfile:1
FROM python:3.10-buster AS build

RUN mkdir /install
WORKDIR /install
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip \
    && pip install -r requirements.txt --prefix="/install"

FROM python:3.10-alpine

ENV TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000 \
    UMASK=022

WORKDIR /src

RUN apk add --no-cache \
    curl \
    s6-overlay \
    bash

COPY --chmod=777 --from=build /install /usr/local
COPY --chmod=755 autobangumi /src
COPY --chmod=755 ./rootfs /

ENTRYPOINT [ "/init" ]

EXPOSE 7892