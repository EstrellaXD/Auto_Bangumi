FROM python:3.13.14-alpine3.23@sha256:9fdbf2e3e82628351513560b121e2ee6ce31cac212be9e070c5a5e2769fb5e76

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app
COPY e2e/fake-qb/server.py /app/server.py

EXPOSE 8080
HEALTHCHECK --interval=2s --timeout=3s --start-period=2s --retries=20 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/__admin/state', timeout=2)"]

CMD ["python", "/app/server.py"]
