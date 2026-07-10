FROM python:3.13.14-alpine3.23@sha256:9fdbf2e3e82628351513560b121e2ee6ce31cac212be9e070c5a5e2769fb5e76

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0

WORKDIR /app
COPY e2e/port-proxy/server.py /app/server.py

EXPOSE 17892 18888 18080 28080

CMD ["python", "/app/server.py"]
