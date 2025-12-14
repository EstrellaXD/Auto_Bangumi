import logging
import re

from bs4 import BeautifulSoup
from urllib3.util import parse_url

from models import MikanInfo
from module.network import RequestContent
from module.utils import gen_poster_path
from module.exceptions import MikanPageParseError

logger = logging.getLogger("mikan_parser")

MIKAN_SEASON_PATTERN = re.compile(r"\s(?:第(.)季|(贰))$")

# 中文数字到阿拉伯数字的映射（小写和大写，1-10）
CHINESE_NUM_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "壹": 1,
    "贰": 2,
    "叁": 3,
    "肆": 4,
    "伍": 5,
    "陆": 6,
    "柒": 7,
    "捌": 8,
    "玖": 9,
    "拾": 10,
}


def chinese_to_num(text: str) -> int | None:
    """将中文数字转换为阿拉伯数字（1-10）"""
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return CHINESE_NUM_MAP.get(text)


class MikanParser:
    # 对 mikan 的网页进行解析

    async def parser(self, url) -> MikanInfo | None:
        """
        1. 网络问题, 透传
        2. 不是 mikan 页面, 抛出 MikanPageParseError
        3. 还没有被收录, 返回 None
        4. 正常返回 MikanInfo
        """
        # NOTE: 网络错误等异常需要在上层处理
        async with RequestContent() as req:
            content = await req.get_html(url)

        # 验证是否为 mikan 页面
        if "Mikan Project" not in content:
            raise MikanPageParseError(url=url)

        mikan_info = MikanInfo()

        soup = BeautifulSoup(content, "html.parser")
        official_title = soup.select_one("p.bangumi-title")
        if official_title:
            # official_title: <a class="w-other-c" href="/Home/Bangumi/3391#583" style="color:#555" target="_blank">败犬女主太多了！</a>
            # mikan_id = re.search(r".*/Home/Bangumi/(\d+(#\d+)?)", str(official_title))
            # https://mikanani.me/RSS/Bangumi?bangumiId=3060&subgroupid=583
            # mikan_id = re.search(r"Bangumi?bangumiId=(\d+)(&subgroupid=(\d+))?,
            # rss 可以拿到 字幕组 id 和 番剧 id
            rss = soup.select_one('a[href^="/RSS/Bangumi?bangumiId="]')
            # (#\d+)?", str(official_title))
            # 如果没有找到 rss 链接, 1. 虽然是 mikan 页面, 但是不是番剧页面 2. 太早了, 动漫还没有被收录, 不过主要还是2
            if not rss:
                logger.debug(f"[MikanWebParser] No RSS link found for {url}")
                return None
            rss_url = rss.get("href")
            # 并不会出现下面的情况
            if not rss_url:
                logger.debug(f"[MikanWebParser] No RSS URL found for {url}")
                return None

            mikan_id = ""
            if isinstance(rss_url, str):
                bangumi_id = re.search(r"bangumiId=(\d+)", rss_url)
                subgroup_id = re.search(r"subgroupid=(\d+)", rss_url)
                if bangumi_id:
                    mikan_id = bangumi_id.group(1)
                    if subgroup_id:
                        mikan_id += "#" + subgroup_id.group(1)

            official_title = official_title.text.strip()
            # 1. 提取季度信息
            season = 1
            season_match = MIKAN_SEASON_PATTERN.search(official_title)
            print(season_match)
            if season_match:
                for season_info in season_match.groups():
                    if num := chinese_to_num(season_info):
                        season = num
                        break
            # 2. 移除季度信息，获取干净的标题
            title = re.sub(MIKAN_SEASON_PATTERN, "", official_title)
            title = title.strip()
            logger.debug(f"[MikanWebParser] Parsed title: {title}, mikan_id: {mikan_id}")
            mikan_info.id = mikan_id
            mikan_info.official_title = title
            mikan_info.season = season
            mikan_info.poster_link = await self.poster_parser(url)
            logger.debug(f"[MikanWebParser] Parsed mikan info: {mikan_info}")
        return mikan_info

    async def poster_parser(self, url) -> str:
        poster_link = ""
        async with RequestContent() as req:
            content = await req.get_html(url)
        # 检查是不是 mikan 页面
        if "Mikan Project" not in content:
            raise MikanPageParseError(url=url)
        root_path = parse_url(url).host
        soup = BeautifulSoup(content, "html.parser")
        poster_div = soup.find("div", {"class": "bangumi-poster"}).get("style")
        if poster_div:
            poster_path = poster_div.split("url('")[1].split("')")[0].split("?")[0]
            # 判断一下是不是默认图片
            if "noimageavailble" in poster_path:
                return ""
            poster_link = f"https://{root_path}{poster_path}"
            poster_link = gen_poster_path(poster_link)
        return poster_link

    async def bangumi_link_parser(self, url) -> str:
        async with RequestContent() as req:
            content = await req.get_html(url)
        if not content:
            return ""
        root_path = parse_url(url).host
        soup = BeautifulSoup(content, "html.parser")
        bangumi_link = soup.select_one('p.bangumi-title a[href^="/Home/Bangumi/"]')
        if bangumi_link:
            bangumi_link = f"https://{root_path}{bangumi_link.get('href')}"
            # https://mikanani.me/Home/Bangumi/3391#583
            bangumi_link = re.sub(r"#.*", "", bangumi_link)
        else:
            bangumi_link = ""
        return bangumi_link


if __name__ == "__main__":
    import asyncio
    import time

    url = "https://mikanani.me/RSS/Bangumi?bangumiId=3661&subgroupid=370"
    url = "https://mikanani.me/Home/Bangumi/3391"
    # url = "https://mikanani.me/Home/Episode/d69f77ab14a1b7aa6eec778d84e979e0d6e9916e"
    # page = BaseWebPage(url)
    parser = MikanParser()
    start = time.time()
    result = asyncio.run(parser.parser(url))
    print(result)
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    start = time.time()

    result = asyncio.run(parser.bangumi_link_parser(url))
    end = time.time()
    print(f"Time taken: {end - start} seconds")

    start = time.time()
    result = asyncio.run(parser.parser(url))
    end = time.time()
    print(f"Time taken: {end - start} seconds")
    print(result)
