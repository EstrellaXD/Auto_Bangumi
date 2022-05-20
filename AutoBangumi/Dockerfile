# syntax=docker/dockerfile:1
FROM python:3.10-slim-buster
WORKDIR /auto-bangumi
COPY requirements.txt .

RUN pip install -r requirements.txt

ENV TZ=Asia/Shanghai
ENV TIME=1800
ENV HOST=127.0.0.1:8080
ENV USER=admin
ENV PASSWORD=adminadmin
ENV METHOD=pn

COPY ./app /app
COPY ./config /config

CMD [ "python3", "/app/docker_main.py"]