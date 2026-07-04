import logging

logger = logging.getLogger(__name__)


def rss_parser(soup):
    results = []
    for item in soup.findall("./channel/item"):
        try:
            title = item.find("title").text
            enclosure = item.find("enclosure")
            if enclosure is not None:
                homepage = item.find("link").text
                url = enclosure.attrib.get("url")
            else:
                url = item.find("link").text
                homepage = ""
            results.append((title, url, homepage))
        except Exception as e:
            logger.warning("Failed to parse RSS item: %s", e)
            continue
    return results


def mikan_title(soup):
    return soup.find("title").text
