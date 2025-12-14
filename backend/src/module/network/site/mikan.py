from xml.etree import ElementTree


def rss_parser(soup: ElementTree.Element) -> tuple[list[str], list[str], list[str]]:
    torrent_titles = []
    torrent_urls = []
    torrent_homepage = []
    for item in soup.findall("./channel/item"):
        title_ = item.find("title")
        link_ = item.find("link")
        # 对于mikan 来说 也不存在 link 为空的情况(只能说其 homepage不存在)
        if link_ is None or title_ is None:
            continue
        torrent_titles.append(title_.text)
        enclosure = item.find("enclosure")
        # 对于 mikan enclosure 存在则为直链下载地址
        # homepage 为 mikan 专属的字段,用于存储详情页链接
        if enclosure is not None:
            torrent_homepage.append(link_.text)
            torrent_urls.append(enclosure.attrib.get("url"))
        else:
            torrent_urls.append(link_.text)
            torrent_homepage.append("")
    return torrent_titles, torrent_urls, torrent_homepage

