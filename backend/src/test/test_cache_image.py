"""Tests for module.utils.cache_image: async, off-event-loop file I/O.

save_image/load_image do real file I/O and are awaited from the RSS hot path
and telegram sends; they must not block the event loop. Tests chdir into a
tmp_path so they never touch the real backend/data/ directory.
"""

import asyncio

from module.utils.cache_image import load_image, save_image


class TestSaveImage:
    async def test_save_image_returns_none_when_img_is_none(self):
        """Fetching the poster failed upstream: skip caching, no filesystem I/O."""
        result = await save_image(None, "jpg")
        assert result is None

    async def test_save_image_writes_file_and_returns_relative_path(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "posters").mkdir(parents=True)

        result = await save_image(b"fake-image-bytes", "jpg")

        assert result is not None
        assert result.startswith("posters/")
        assert result.endswith(".jpg")
        assert (tmp_path / "data" / result).read_bytes() == b"fake-image-bytes"

    async def test_save_image_offloads_write_to_a_thread(self, tmp_path, monkeypatch):
        """The write must go through asyncio.to_thread, not run inline on the
        event loop (regression test for the blocking-I/O fix)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "posters").mkdir(parents=True)

        real_to_thread = asyncio.to_thread
        calls = []

        async def spy_to_thread(func, /, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr("module.utils.cache_image.asyncio.to_thread", spy_to_thread)

        await save_image(b"payload", "png")

        assert len(calls) == 1


class TestLoadImage:
    async def test_load_image_returns_none_for_falsy_path(self):
        assert await load_image(None) is None
        assert await load_image("") is None

    async def test_load_image_reads_file_relative_to_data_dir(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        posters_dir = tmp_path / "data" / "posters"
        posters_dir.mkdir(parents=True)
        (posters_dir / "abc123.jpg").write_bytes(b"cached-poster-bytes")

        result = await load_image("posters/abc123.jpg")

        assert result == b"cached-poster-bytes"

    async def test_load_image_offloads_read_to_a_thread(self, tmp_path, monkeypatch):
        """The read must go through asyncio.to_thread, not run inline on the
        event loop (regression test for the blocking-I/O fix)."""
        monkeypatch.chdir(tmp_path)
        posters_dir = tmp_path / "data" / "posters"
        posters_dir.mkdir(parents=True)
        (posters_dir / "abc123.jpg").write_bytes(b"cached-poster-bytes")

        real_to_thread = asyncio.to_thread
        calls = []

        async def spy_to_thread(func, /, *args, **kwargs):
            calls.append(func)
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr("module.utils.cache_image.asyncio.to_thread", spy_to_thread)

        await load_image("posters/abc123.jpg")

        assert len(calls) == 1
