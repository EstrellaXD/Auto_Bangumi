from module.network import RequestContent


search_url = lambda e: \
        f"https://api.bgm.tv/search/subject/{e}?responseGroup=large"


def bgm_parser(title):
    url = search_url(title)
    with RequestContent() as req:
        contents = req.get_json(url)
        if contents:
            return contents[0]
        else:
            return None

