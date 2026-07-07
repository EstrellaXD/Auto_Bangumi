"""Tests for module.conf.search_provider: {url, parser} storage and
backward-compatible loading of legacy url-only provider configs."""

import pytest

from module.conf import search_provider as search_provider_module
from module.conf.search_provider import _normalize, load_provider, save_provider


@pytest.fixture(autouse=True)
def _isolate_provider_state(tmp_path, monkeypatch):
    """Point PROVIDER_PATH at a scratch file and restore SEARCH_CONFIG after
    each test, so tests never touch the real config/search_provider.json or
    leak module-level state into other tests."""
    monkeypatch.setattr(
        search_provider_module, "PROVIDER_PATH", tmp_path / "search_provider.json"
    )
    original = search_provider_module.SEARCH_CONFIG
    yield
    search_provider_module.SEARCH_CONFIG = original


class TestNormalize:
    def test_normalize_legacy_string_config_migrates_to_dict(self):
        """Old {"site": "url"} entries gain a default parser field."""
        legacy = {
            "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
            "nyaa": "https://nyaa.si/?page=rss&q=%s",
        }
        result = _normalize(legacy)
        assert result["mikan"] == {
            "url": "https://mikanani.me/RSS/Search?searchstr=%s",
            "parser": "mikan",
        }
        assert result["nyaa"] == {
            "url": "https://nyaa.si/?page=rss&q=%s",
            "parser": "tmdb",
        }

    def test_normalize_new_dict_config_preserves_parser(self):
        """Already-migrated {"site": {"url", "parser"}} entries pass through."""
        new_format = {"custom": {"url": "https://x.example/%s", "parser": "tmdb"}}
        result = _normalize(new_format)
        assert result == new_format

    def test_normalize_missing_parser_field_defaults(self):
        """A dict entry missing "parser" falls back to the default rule."""
        result = _normalize({"custom": {"url": "https://x.example/%s"}})
        assert result["custom"]["parser"] == "tmdb"


class TestLoadProvider:
    def test_load_provider_backward_compatible_with_legacy_file(
        self, tmp_path, monkeypatch
    ):
        """A pre-existing url-only JSON config file still loads successfully."""
        from module.utils import json_config

        legacy_path = tmp_path / "search_provider.json"
        json_config.save(
            legacy_path,
            {"mikan": "https://mikanani.me/RSS/Search?searchstr=%s"},
        )
        monkeypatch.setattr(search_provider_module, "PROVIDER_PATH", legacy_path)

        result = load_provider()

        assert result["mikan"]["url"] == "https://mikanani.me/RSS/Search?searchstr=%s"
        assert result["mikan"]["parser"] == "mikan"

    def test_load_provider_creates_default_file_when_missing(self, tmp_path):
        """A missing config file falls back to DEFAULT_PROVIDER and persists it."""
        result = load_provider()
        assert result == search_provider_module.DEFAULT_PROVIDER
        assert search_provider_module.PROVIDER_PATH.exists()


class TestSaveProvider:
    def test_save_provider_stores_url_and_parser(self):
        """Saving a full {url, parser} config round-trips through SEARCH_CONFIG."""
        save_provider({"custom": {"url": "https://x.example/%s", "parser": "tmdb"}})
        assert search_provider_module.get_provider()["custom"] == {
            "url": "https://x.example/%s",
            "parser": "tmdb",
        }

    def test_save_provider_url_only_update_preserves_existing_parser(self):
        """Saving just a URL for a site with a saved custom parser keeps that
        parser instead of resetting it to the site-name-based default."""
        save_provider({"custom": {"url": "https://old.example/%s", "parser": "mikan"}})

        save_provider({"custom": "https://new.example/%s"})

        result = search_provider_module.get_provider()["custom"]
        assert result["url"] == "https://new.example/%s"
        assert result["parser"] == "mikan"

    def test_save_provider_url_only_new_site_uses_default_parser(self):
        """A brand-new site saved as a bare URL gets the default parser rule."""
        save_provider({"custom": "https://x.example/%s"})
        assert search_provider_module.get_provider()["custom"]["parser"] == "tmdb"
