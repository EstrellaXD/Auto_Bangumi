# syntax=docker/dockerfile:1
FROM python:3.10-slim-buster

WORKDIR /src

ADD requirements.txt .

RUN pip install -r requirements.txt

ENV TZ=Asia/Shanghai

ADD ./src /src
RUN mkdir /config
ADD ./templates /templates

RUN chmod a+x run.sh

CMD ["./run.sh"]
