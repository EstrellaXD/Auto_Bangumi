import httpx


class TrDownloader:
    def __init__(self, host, username, password, ssl):
        self.host = host
        self.username = username
        self.password = password
        self.ssl = ssl
        self._client = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.host,
            auth=(self.username, self.password),
            timeout=5,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

    async def auth(self):
        resp = await self._client.get("/transmission/rpc")
        resp.raise_for_status()
        return resp
