def rss_parser(soup):
    results = []
    for item in soup.findall("./channel/item"):
        title = item.find("title").text
        enclosure = item.find("enclosure")
        if enclosure is not None:
            homepage = item.find("link").text
            url = enclosure.attrib.get("url")
        else:
            url = item.find("link").text
            homepage = ""
        results.append((title, url, homepage))
    return results


def mikan_title(soup):
    return soup.find("title").text
