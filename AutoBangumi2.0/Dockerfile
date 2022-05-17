# syntax=docker/dockerfile:1
FROM python:3.10-slim-buster
WORKDIR /auto-bangumi
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY ./app /app
COPY ./config /config


CMD [ "python3", "/app/docker_main.py"]