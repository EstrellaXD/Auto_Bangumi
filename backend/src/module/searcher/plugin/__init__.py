from .mikan import mikan_url
from .nyaa import nyaa_url
from .dmhy import dmhy_url


def search_url(site: str, keywords: list[str]):
    if site == "mikan":
        return mikan_url(keywords)
    elif site == "nyaa":
        return nyaa_url(keywords)
    elif site == "dmhy":
        return dmhy_url(keywords)
    else:
        raise NotImplementedError(f"site {site} is not supported")
