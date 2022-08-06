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

RUN apk add curl

RUN mkdir "/config" && \
    chmod a+x run.sh

ENV TZ=Asia/Shanghai

EXPOSE 7892

CMD ["sh", "run.sh"]
