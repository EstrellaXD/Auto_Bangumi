import pytest
from custom_rss_site import CustomRssSite

from ab_sdk.ingest import HttpRequest
from ab_sdk.testing import SearchSiteContract, create_plugin


class TestSite(SearchSiteContract):
    def create(self):
        plugin, _ = create_plugin(CustomRssSite)
        return plugin.site()


@pytest.mark.parametrize(
    ("url", "cookie"),
    [
        ("https://tracker.example.org/rss?search=a", "uid=1"),
        ("https://other.example.com/feed", None),
    ],
)
def test_add_cookie_only_for_own_host(url, cookie):
    plugin, _ = create_plugin(CustomRssSite, {"cookie": "uid=1"})
    result = plugin.add_cookie(HttpRequest("GET", url, {}))
    assert (result.headers["Cookie"] if result else None) == cookie


def test_add_cookie_empty_cookie_leaves_request_alone():
    plugin, _ = create_plugin(CustomRssSite)
    request = HttpRequest("GET", "https://tracker.example.org/rss", {})
    assert plugin.add_cookie(request) is None
