# syntax=docker/dockerfile:1
FROM python:3.10-slim-buster

WORKDIR /auto_bangumi

ADD requirements.txt .

RUN pip install -r requirements.txt

ENV TZ=Asia/Shanghai

ADD ./auto_bangumi /auto_bangumi
ADD ./config /config

CMD [ "python3", "app.py"]
