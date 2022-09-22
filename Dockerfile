# syntax=docker/dockerfile:1
FROM python:3.10-buster AS build

RUN mkdir /install
WORKDIR /install
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip \
    && pip install -r requirements.txt --prefix="/install"

FROM python:3.10-alpine

WORKDIR /src

COPY --from=build /install /usr/local
ADD ./src /src

RUN apk add --update --no-cache \
    curl \
    shadow \
    supervisor

RUN addgroup -S bangumi && \
    adduser -S bangumi -G bangumi -h /home/bangumi && \
    usermod -s /bin/bash bangumi

RUN mkdir -p "/config" "/config/logs/supervisor" && \
    chmod a+x run.sh && \
    chmod a+x getWebUI.sh

ENV TZ=Asia/Shanghai \
    PUID=1000 \
    PGID=1000

EXPOSE 7892

CMD ["sh", "run.sh"]
