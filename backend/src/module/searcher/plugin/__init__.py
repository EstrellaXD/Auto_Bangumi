from .mikan import mikan_url


def search_url(site: str, keywords: list[str]):
    if site == "mikan":
        return mikan_url(keywords)
    else:
        raise NotImplementedError(f"site {site} is not supported")
