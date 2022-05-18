# syntax=docker/dockerfile:1
FROM python:3.10-slim-buster
WORKDIR /auto-bangumi
COPY requirements.txt .

RUN pip install -r requirements.txt

ENV TZ=Asia/Shanghai
ENV TIME=1800

COPY ./app /app

CMD [ "python3", "/app/docker_main.py"]