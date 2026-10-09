import logging
import sqlite3
from contextlib import closing
from pathlib import Path

import semver

from module.conf import (
    DATA_PATH,
    LEGACY_DATA_PATH,
    V3_VERSION_PATH,
    VERSION,
    VERSION_PATH,
)
from module.conf.config import CONFIG_PATH

logger = logging.getLogger(__name__)

DATABASE_PATH = Path(DATA_PATH.removeprefix("sqlite:///"))

# 4.0 只支持从 3.3.x 起跳升级；更早版本的跨版本迁移代码已移除。
MIN_UPGRADE_FROM = (3, 3)


class UnsupportedUpgradeError(RuntimeError):
    """已有数据来自过旧的版本，无法直接升级到当前版本。"""


def _upgrade_hint(previous: str, via: str = "3.3.x") -> str:
    # 拒绝前 Settings 已把 config.json 改写为 4.0 格式，旧版本读不懂，
    # 必须先还原迁移前的备份
    backup = f"{CONFIG_PATH}.v3.bak"
    return (
        f"Detected data from AutoBangumi {previous}. Upgrading directly to "
        f"{VERSION} is not supported. If {backup} exists, copy it back to "
        f"{CONFIG_PATH} first. Then upgrade to the latest {via}, "
        "start it once so it migrates your data, then upgrade again. "
        f"检测到 {previous} 版本的数据，无法直接升级到 {VERSION}："
        f"若存在 {backup}，请先用它覆盖 {CONFIG_PATH}；"
        f"再升级到最新的 {via} 并启动一次完成数据迁移，然后再升级。"
    )


def refuse_legacy_data() -> None:
    """残留 2.x 的 ``data.json`` 时抛 :class:`UnsupportedUpgradeError`。

    首次启动（尚无数据库）也要检查：否则会建出新库当作新安装启动，
    之后每次启动才被拒绝。
    """
    if LEGACY_DATA_PATH.exists():
        raise UnsupportedUpgradeError(_upgrade_hint("2.x"))


def _is_v30_database() -> bool:
    """3.0.x 不写 version.info，数据库里也没有 3.1 起才有的 rssitem 表。"""
    with closing(sqlite3.connect(DATABASE_PATH)) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'rssitem'"
        ).fetchone()
    return row is None


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


def _read_v3_version() -> semver.Version | None:
    """3.x 的记录只读不写：回退到 3.3 时它仍要看到自己的版本。"""
    try:
        lines = V3_VERSION_PATH.read_text().splitlines()
        return semver.Version.parse(lines[-1].strip())
    except (IndexError, ValueError) as e:
        logger.warning(f"{V3_VERSION_PATH} is empty or malformed ({e}).")
        return None


def _backup_v3_database() -> None:
    """首次以 4.x 启动 3.x 数据时备份数据库，供回退 3.3 时还原；已有备份不覆盖。"""
    backup = DATABASE_PATH.with_name(DATABASE_PATH.name + ".v3.bak")
    if backup.exists():
        return
    # 用 SQLite 备份接口而不是复制文件：WAL 中未合并的数据也要带上
    with (
        closing(sqlite3.connect(DATABASE_PATH)) as src,
        closing(sqlite3.connect(backup)) as dst,
    ):
        src.backup(dst)
    logger.info(f"Backed up the 3.x database to {backup}.")


def version_check() -> semver.Version | None:
    """校验并记录版本，返回上一次运行的版本（未知时为 None）。

    仅在已有数据库时调用。上一次版本低于 ``MIN_UPGRADE_FROM``，或数据库来自
    3.0.x 时抛出 :class:`UnsupportedUpgradeError`，中止启动。
    """
    if VERSION in ("DEV_VERSION", "local"):
        return None
    if VERSION_PATH.exists():
        last_ver = _read_last_version()
        if last_ver is None:
            return None
    elif V3_VERSION_PATH.exists():
        last_ver = _read_v3_version()
        if last_ver is not None and (last_ver.major, last_ver.minor) < (
            MIN_UPGRADE_FROM
        ):
            raise UnsupportedUpgradeError(_upgrade_hint(str(last_ver)))
        _backup_v3_database()
        VERSION_PATH.write_text(VERSION + "\n")
        return last_ver
    else:
        # 3.3 也不补跑 3.0 → 3.1 的数据迁移（缺 version.info 时跳过），只有 3.1.x 会
        if _is_v30_database():
            raise UnsupportedUpgradeError(_upgrade_hint("3.0", via="3.1.x"))
        VERSION_PATH.write_text(VERSION + "\n")
        return None
    if semver.Version.parse(VERSION) > last_ver:
        with VERSION_PATH.open("a") as f:
            f.write(VERSION + "\n")
    return last_ver
