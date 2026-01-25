import asyncio
import logging

import httpx

from module.ab_decorator import qb_connect_failed_wait

logger = logging.getLogger(__name__)


class QbDownloader:
    def __init__(self, host: str, username: str, password: str, ssl: bool):
        if "://" not in host:
            scheme = "https" if ssl else "http"
            self.host = f"{scheme}://{host}"
        else:
            self.host = host
        self.username = username
        self.password = password
        self.ssl = ssl
        self._client: httpx.AsyncClient | None = None

    def _url(self, endpoint: str) -> str:
        return f"{self.host}/api/v2/{endpoint}"

    async def auth(self, retry=3):
        times = 0
        timeout = httpx.Timeout(connect=3.1, read=10.0, write=10.0, pool=10.0)
        self._client = httpx.AsyncClient(
            timeout=timeout, verify=self.ssl
        )
        while times < retry:
            try:
                resp = await self._client.post(
                    self._url("auth/login"),
                    data={"username": self.username, "password": self.password},
                )
                if resp.status_code == 200 and resp.text == "Ok.":
                    return True
                elif resp.status_code == 403:
                    logger.error("Login refused by qBittorrent Server")
                    logger.info("Please release the IP in qBittorrent Server")
                    break
                else:
                    logger.error(
                        f"Can't login qBittorrent Server {self.host} by {self.username}, retry in 5 seconds."
                    )
                    await asyncio.sleep(5)
                    times += 1
            except httpx.ConnectError:
                logger.error("Cannot connect to qBittorrent Server")
                logger.info("Please check the IP and port in WebUI settings")
                await asyncio.sleep(10)
                times += 1
            except Exception as e:
                logger.error(f"Unknown error: {e}")
                break
        return False

    async def logout(self):
        if self._client:
            try:
                await self._client.post(self._url("auth/logout"))
            except Exception:
                pass
            await self._client.aclose()
            self._client = None

    async def check_host(self):
        try:
            resp = await self._client.get(self._url("app/version"))
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.RequestError):
            return False

    def check_rss(self, rss_link: str):
        pass

    @qb_connect_failed_wait
    async def prefs_init(self, prefs):
        resp = await self._client.post(
            self._url("app/setPreferences"),
            data={"json": __import__("json").dumps(prefs)},
        )
        return resp

    @qb_connect_failed_wait
    async def get_app_prefs(self):
        resp = await self._client.get(self._url("app/preferences"))
        return resp.json()

    async def add_category(self, category):
        await self._client.post(
            self._url("torrents/createCategory"),
            data={"category": category, "savePath": ""},
        )

    @qb_connect_failed_wait
    async def torrents_info(self, status_filter, category, tag=None):
        params = {}
        if status_filter:
            params["filter"] = status_filter
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag
        resp = await self._client.get(self._url("torrents/info"), params=params)
        return resp.json()

    @qb_connect_failed_wait
    async def torrents_files(self, torrent_hash: str):
        resp = await self._client.get(
            self._url("torrents/files"), params={"hash": torrent_hash}
        )
        return resp.json()

    async def add_torrents(self, torrent_urls, torrent_files, save_path, category):
        data = {
            "savepath": save_path,
            "category": category,
            "paused": "false",
            "autoTMM": "false",
            "contentLayout": "NoSubfolder",
        }
        files = {}
        if torrent_urls:
            if isinstance(torrent_urls, list):
                data["urls"] = "\n".join(torrent_urls)
            else:
                data["urls"] = torrent_urls
        if torrent_files:
            if isinstance(torrent_files, list):
                for i, f in enumerate(torrent_files):
                    files[f"torrents_{i}"] = (f"torrent_{i}.torrent", f, "application/x-bittorrent")
            else:
                files["torrents"] = ("torrent.torrent", torrent_files, "application/x-bittorrent")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = await self._client.post(
                    self._url("torrents/add"),
                    data=data,
                    files=files if files else None,
                )
                return resp.text == "Ok."
            except (httpx.ReadError, httpx.ConnectError, httpx.RequestError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[Downloader] Network error adding torrent (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(2)
                else:
                    logger.error(f"[Downloader] Failed to add torrent after {max_retries} attempts: {e}")
                    raise

    async def torrents_delete(self, hash, delete_files: bool = True):
        await self._client.post(
            self._url("torrents/delete"),
            data={"hashes": hash, "deleteFiles": str(delete_files).lower()},
        )

    async def torrents_pause(self, hashes: str):
        await self._client.post(
            self._url("torrents/pause"),
            data={"hashes": hashes},
        )

    async def torrents_resume(self, hashes: str):
        await self._client.post(
            self._url("torrents/resume"),
            data={"hashes": hashes},
        )

    async def torrents_rename_file(self, torrent_hash, old_path, new_path) -> bool:
        try:
            resp = await self._client.post(
                self._url("torrents/renameFile"),
                data={"hash": torrent_hash, "oldPath": old_path, "newPath": new_path},
            )
            if resp.status_code == 409:
                logger.debug(f"Conflict409Error: {old_path} >> {new_path}")
                return False
            return resp.status_code == 200
        except Exception:
            return False

    async def rss_add_feed(self, url, item_path):
        resp = await self._client.post(
            self._url("rss/addFeed"),
            data={"url": url, "path": item_path},
        )
        if resp.status_code == 409:
            logger.warning(f"[Downloader] RSS feed {url} already exists")

    async def rss_remove_item(self, item_path):
        resp = await self._client.post(
            self._url("rss/removeItem"),
            data={"path": item_path},
        )
        if resp.status_code == 409:
            logger.warning(f"[Downloader] RSS item {item_path} does not exist")

    async def rss_get_feeds(self):
        resp = await self._client.get(self._url("rss/items"))
        return resp.json()

    async def rss_set_rule(self, rule_name, rule_def):
        import json
        await self._client.post(
            self._url("rss/setRule"),
            data={"ruleName": rule_name, "ruleDef": json.dumps(rule_def)},
        )

    async def move_torrent(self, hashes, new_location):
        await self._client.post(
            self._url("torrents/setLocation"),
            data={"hashes": hashes, "location": new_location},
        )

    async def get_download_rule(self):
        resp = await self._client.get(self._url("rss/rules"))
        return resp.json()

    async def get_torrent_path(self, _hash):
        resp = await self._client.get(
            self._url("torrents/info"), params={"hashes": _hash}
        )
        torrents = resp.json()
        if torrents:
            return torrents[0].get("save_path", "")
        return ""

    async def set_category(self, _hash, category):
        resp = await self._client.post(
            self._url("torrents/setCategory"),
            data={"hashes": _hash, "category": category},
        )
        if resp.status_code == 409:
            logger.warning(f"[Downloader] Category {category} does not exist")
            await self.add_category(category)
            await self._client.post(
                self._url("torrents/setCategory"),
                data={"hashes": _hash, "category": category},
            )

    async def check_connection(self):
        resp = await self._client.get(self._url("app/version"))
        return resp.text

    async def remove_rule(self, rule_name):
        await self._client.post(
            self._url("rss/removeRule"),
            data={"ruleName": rule_name},
        )

    async def add_tag(self, _hash, tag):
        await self._client.post(
            self._url("torrents/addTags"),
            data={"hashes": _hash, "tags": tag},
        )
