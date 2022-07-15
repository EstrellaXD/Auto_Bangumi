# syntax=docker/dockerfile:1
FROM python:3.10-slim-buster

WORKDIR /auto_bangumi

ADD requirements.txt .

RUN pip install -r requirements.txt

ENV TZ=Asia/Shanghai

ADD src /auto_bangumi
RUN mkdir /config
ADD ./templates /templates

RUN chmod a+x run.sh

CMD ["./run.sh"]
