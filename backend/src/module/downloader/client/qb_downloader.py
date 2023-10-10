import logging
import httpx

logger = logging.getLogger(__name__)


class QbDownloader:
    def __init__(self, host: str, username: str, password: str, ssl: bool):
        self.host = host if "://" in host else "http://" + host
        self.username = username
        self.password = password
        self.ssl = ssl

    async def auth(self):
        resp = await self._client.post(
            url="/api/v2/auth/login",
            data={"username": self.username, "password": self.password},
            timeout=5,
        )
        return resp.text

    async def logout(self):
        logout_api = "/api/v2/auth/logout"
        await self._client.post(url=logout_api, timeout=5)

    async def check_host(self):
        try:
            await self._client.get(
                url="/api/v2/app/version",
                timeout=5
            )
            return True
        except httpx.RequestError:
            return False

    async def prefs_init(self, prefs):
        prefs_api = "/api/v2/app/setPreferences"
        await self._client.post(url=prefs_api, data=prefs)

    async def add_category(self, category):
        await self._client.post(
            url="/api/v2/torrents/createCategory",
            data={"category": category},
            timeout=5,
        )

    async def torrents_info(self, status_filter, category, tag=None):
        data = {
            "filter": status_filter,
            "category": category,
            "tag": tag,
        }
        torrent_info = await self._client.get(
            url="/api/v2/torrents/info",
            params=data,
        )
        return torrent_info.json()

    async def add(self, torrent_urls, torrent_files, save_path, category):
        data = {
            "urls": torrent_urls,
            "torrent_files": torrent_files,
            "save_path": save_path,
            "category": category,
            "is_paused": False,
            "use_auto_torrent_management": False,
        }
        resp = await self._client.post(
            url="/api/v2/torrents/add",
            data=data,
        )
        return resp.status_code == 200

    async def delete(self, _hash):
        data = {
            "hashes": _hash,
            "deleteFiles": True,
        }
        resp = await self._client.post(
            url="/api/v2/torrents/delete",
            data=data,
        )
        return resp.status_code == 200

    async def rename(self, torrent_hash, old_path, new_path) -> bool:
        data = {
            "hash": torrent_hash,
            "oldPath": old_path,
            "newPath": new_path,
        }
        resp = await self._client.post(
            url="/api/v2/torrents/renameFile",
            data=data,
        )
        return resp.status_code == 200

    async def move(self, hashes, new_location):
        data = {
            "hashes": hashes,
            "location": new_location,
        }
        resp = await self._client.post(
            url="/api/v2/torrents/setLocation",
            data=data,
        )
        return resp.status_code == 200

    async def set_category(self, _hash, category):
        data = {
            "category": category,
            "hashes": _hash,
        }
        resp = await self._client.post(
            url="/api/v2/torrents/setCategory",
            data=data,
        )
        return resp.status_code == 200

    async def add_tag(self, _hash, tag):
        data = {
            "hashes": _hash,
            "tags": tag,
        }
        resp = await self._client.post(
            url="/api/v2/torrents/addTags",
            data=data,
        )
        return resp.status_code == 200

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.host,
        )
        try:
            authed = await self.auth()
            if not authed == "Ok.":
                logger.error("[Downloader] Failed authing to qbittorrent.")
                logger.warning("[Downloader] Please check username/password in settings.")
                raise RuntimeError(authed)
            return self
        except httpx.ReadTimeout:
            logger.error("[Downloader] Failed connecting to qbittorrent.")
            logger.warning("[Downloader] Please check host in settings.")
            raise RuntimeError("Failed connecting to qbittorrent.")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()
        await self._client.aclose()
