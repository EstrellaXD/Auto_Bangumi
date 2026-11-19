from unittest.mock import AsyncMock

import pytest

from module.network import RequestContent
from module.plugin import metadata


async def test_metadata_uses_host_client_cache_and_distinguishes_media_types(
    monkeypatch,
):
    metadata._cache.clear()
    get = AsyncMock(
        return_value={
            "results": [{"id": 12, "name": "Example", "first_air_date": "2024-01-01"}]
        }
    )
    monkeypatch.setattr(RequestContent, "get_json", get)
    service = metadata.HostMetadataService()
    tv = await service.search("Example", media_type="tv")
    again = await service.search("Example", media_type="tv")
    movie = await service.search("Example", media_type="movie")
    assert tv == again and tv[0].media_type == "tv" and movie[0].media_type == "movie"
    assert get.await_count == 2
    assert not hasattr(tv[0], "api_key")


async def test_metadata_failure_does_not_leak_key_or_poison_cache(monkeypatch):
    metadata._cache.clear()
    get = AsyncMock(side_effect=RuntimeError("https://private-host/?api_key=secret"))
    monkeypatch.setattr(RequestContent, "get_json", get)
    with pytest.raises(RuntimeError, match="^TMDB request failed$"):
        await metadata.HostMetadataService().get(12)
    assert not metadata._cache
    with pytest.raises(ValueError):
        await metadata.HostMetadataService().get(12, language="../../invalid")
