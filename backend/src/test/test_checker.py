"""Checker.check_downloader_detail —— 构造错误也要被捕获，不得击穿启动循环。"""

from unittest.mock import MagicMock, patch

from module.checker import Checker


async def test_construction_error_returns_false_not_raises():
    """下载器类型无法识别时 DownloadClient() 构造即抛，必须捕获为
    (False, 'unreachable')，否则会击穿 _wait_for_downloader 的等待循环。"""
    settings = MagicMock()
    settings.downloader.type = "bogus-type"
    with (
        patch("module.checker.checker.settings", settings),
        patch(
            "module.downloader.DownloadClient",
            side_effect=Exception("Unsupported downloader type: bogus-type"),
        ),
    ):
        ok, reason = await Checker.check_downloader_detail()

    assert ok is False
    assert reason == "unreachable"


async def test_mock_downloader_short_circuits_ok():
    settings = MagicMock()
    settings.downloader.type = "mock"
    with patch("module.checker.checker.settings", settings):
        ok, reason = await Checker.check_downloader_detail()
    assert ok is True
    assert reason is None
