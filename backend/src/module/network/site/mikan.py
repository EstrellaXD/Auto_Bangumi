def rss_parser(soup):
    torrent_titles = []
    torrent_urls = []
    torrent_homepage = []
    if not len(soup.findall("./channel/item/enclosure")):
        for item in soup.findall("./channel/item"):
            torrent_titles.append(item.find("title").text)
            torrent_urls.append(item.find("link").text)
            torrent_homepage.append(item.find("guid").text)
    else:
        for item in soup.findall("./channel/item"):
            torrent_titles.append(item.find("title").text)
            torrent_urls.append(item.find("enclosure").attrib["url"])
            torrent_homepage.append(item.find("link").text)
    return torrent_titles, torrent_urls, torrent_homepage


def mikan_title(soup):
    return soup.find("title").text
