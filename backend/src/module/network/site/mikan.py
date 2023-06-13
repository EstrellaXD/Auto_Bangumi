def mikan_parser(soup):
    torrent_titles = []
    torrent_urls = []
    torrent_homepage = []
    for item in soup.findall("./channel/item"):
        torrent_titles.append(item.find("title").text)
        torrent_urls.append(item.find("enclosure").attrib["url"])
        torrent_homepage.append(item.find("link").text)
    return torrent_titles, torrent_urls, torrent_homepage
