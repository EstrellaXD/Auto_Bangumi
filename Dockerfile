# syntax=docker/dockerfile:1
FROM python:3.10-buster

WORKDIR /src

ADD requirements.txt .

RUN apt-get update && apt-get install python3-lxml
RUN pip install -r requirements.txt

ENV TZ=Asia/Shanghai

ADD ./src /src
RUN mkdir /config
ADD ./templates /templates

RUN chmod a+x run.sh

EXPOSE 7892

CMD ["./run.sh"]
