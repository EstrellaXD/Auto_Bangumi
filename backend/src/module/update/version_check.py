import logging

import semver

from module.conf import LEGACY_DATA_PATH, VERSION, VERSION_PATH

logger = logging.getLogger(__name__)

# 4.0 只支持从 3.3.x 起跳升级；更早版本的跨版本迁移代码已移除。
MIN_UPGRADE_FROM = (3, 3)


class UnsupportedUpgradeError(RuntimeError):
    """已有数据来自过旧的版本，无法直接升级到当前版本。"""


def _upgrade_hint(previous: str) -> str:
    return (
        f"Detected data from AutoBangumi {previous}. Upgrading directly to "
        f"{VERSION} is not supported: please upgrade to the latest 3.3.x first, "
        "start it once so it migrates your data, then upgrade again. "
        f"检测到 {previous} 版本的数据，无法直接升级到 {VERSION}："
        "请先升级到最新的 3.3.x 并启动一次完成数据迁移，再升级到本版本。"
    )


def _read_last_version() -> semver.Version | None:
    try:
        lines = VERSION_PATH.read_text().splitlines()
        return semver.Version.parse(lines[-1].strip())
    except (IndexError, ValueError) as e:
        logger.warning(
            f"{VERSION_PATH} is empty or malformed ({e}); "
            "rewriting with the current version."
        )
        VERSION_PATH.write_text(VERSION + "\n")
        return None


def version_check() -> semver.Version | None:
    """校验并记录版本，返回上一次运行的版本（未知时为 None）。

    仅在已有数据库时调用。上一次版本低于 ``MIN_UPGRADE_FROM``，或残留 2.x 的
    ``data.json`` 时抛出 :class:`UnsupportedUpgradeError`，中止启动。
    """
    if LEGACY_DATA_PATH.exists():
        raise UnsupportedUpgradeError(_upgrade_hint("2.x"))
    if VERSION in ("DEV_VERSION", "local"):
        return None
    if not VERSION_PATH.exists():
        VERSION_PATH.write_text(VERSION + "\n")
        return None
    last_ver = _read_last_version()
    if last_ver is None:
        return None
    if (last_ver.major, last_ver.minor) < MIN_UPGRADE_FROM:
        raise UnsupportedUpgradeError(_upgrade_hint(str(last_ver)))
    if semver.Version.parse(VERSION) > last_ver:
        with VERSION_PATH.open("a") as f:
            f.write(VERSION + "\n")
    return last_ver
