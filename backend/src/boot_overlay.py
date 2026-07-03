"""容器启动时应用在线更新覆盖层（在应用启动前、以 root 运行）。

由 entrypoint.sh 在 `exec ... python main.py` 之前调用：

    python /app/boot_overlay.py

逻辑：从持久卷 ``/app/config/updates/`` 读取 ``applied.json``，当覆盖层版本
**高于** 镜像基线版本（``/app/IMAGE_VERSION``）时，把覆盖层的 module 树覆盖到
``/app/module``、前端 dist 覆盖到 ``/app/dist``，并在更新包已预先准备好
``.venv`` 时替换 ``/app/.venv``；否则（镜像更新或相等）忽略并清除过期覆盖层，
让镜像版本生效。

关键约束：本脚本位于 ``/app/boot_overlay.py``，**不在** 覆盖层会替换的
``/app/module`` 里，因此始终是镜像自带的稳定版本在做决策。任何一步失败都不得
阻断启动——记录日志后回退到镜像版本继续启动。
"""

import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: [BootOverlay] %(message)s"
)
logger = logging.getLogger("boot_overlay")

APP_ROOT = Path("/app")
UPDATES_ROOT = APP_ROOT / "config" / "updates"
IMAGE_VERSION_PATH = APP_ROOT / "IMAGE_VERSION"


def _parse_semver(value: str):
    """解析 semver，失败返回 None。semver 是基础依赖，镜像 venv 中始终可用。"""
    try:
        import semver

        return semver.VersionInfo.parse(value.strip().lstrip("v"))
    except Exception:
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _read_applied(updates_root: Path) -> dict | None:
    import json

    applied = updates_root / "applied.json"
    try:
        data = json.loads(applied.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _replace_tree(src: Path, dst: Path) -> None:
    """用 src 原子地替换 dst（先复制到 .new，再 rename 交换，最后清理 .old）。"""
    parent = dst.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / (dst.name + ".ab_new")
    old = parent / (dst.name + ".ab_old")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp)
    if old.exists():
        shutil.rmtree(old)
    if dst.exists():
        os.rename(dst, old)
    os.rename(tmp, dst)
    if old.exists():
        shutil.rmtree(old)


def _sha256_file(path: Path) -> str | None:
    import hashlib

    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


# 记录 /app/.venv 当前对应的 uv.lock 哈希；缺失即视为镜像基线 venv。
_VENV_LOCK_MARKER = ".ab-lock-sha256"


def _sync_venv_to_lock(
    current: Path, app_root: Path, baseline_lock: Path | None
) -> None:
    """把 /app/.venv 与当前生效覆盖层的 uv.lock 对齐。

    正常路径下依赖在 apply 时已预装进 staged .venv，这里不会做任何事；只有
    覆盖层带 uv.lock 却没有 staged .venv（回滚到旧覆盖层、或旧版 updater
    落盘的覆盖层）且 lock 与 venv 当前对应的 lock 不一致时才补一次
    uv sync——否则回滚后的旧代码会跑在新依赖上直接启动崩溃。
    失败只记日志：用现有 venv 继续启动好过卡死在启动前。
    """
    overlay_lock = current / "backend" / "uv.lock"
    if not overlay_lock.exists():
        return
    image_lock = baseline_lock if baseline_lock is not None else app_root / "uv.lock"
    desired = _sha256_file(overlay_lock)
    marker = app_root / ".venv" / _VENV_LOCK_MARKER
    actual = _read_text(marker) or (
        _sha256_file(image_lock) if image_lock.exists() else None
    )
    if desired is None or actual == desired:
        return

    uv = shutil.which("uv")
    if not uv:
        logger.error("uv not found; cannot reconcile venv with overlay lockfile.")
        return

    import subprocess

    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str((app_root / ".venv").resolve())
    logger.info("No staged venv; syncing /app/.venv against overlay uv.lock.")
    try:
        subprocess.run(
            [uv, "sync", "--frozen", "--no-dev"],
            cwd=str(current / "backend"),
            env=env,
            check=True,
        )
        marker.write_text(desired, encoding="utf-8")
    except Exception as exc:
        logger.error("venv reconcile failed; continuing with existing venv: %s", exc)


def _clear_overlay(updates_root: Path) -> None:
    """删除过期覆盖层标记，使运行状态回归镜像版本。"""
    applied = updates_root / "applied.json"
    try:
        if applied.exists():
            applied.unlink()
        logger.info("Cleared stale overlay marker; running image version.")
    except OSError as exc:
        logger.warning("Failed to clear stale overlay: %s", exc)


def apply_overlay(
    app_root: Path = APP_ROOT,
    updates_root: Path = UPDATES_ROOT,
    image_version_path: Path = IMAGE_VERSION_PATH,
    baseline_lock: Path | None = None,
) -> bool:
    """应用覆盖层。返回是否实际把覆盖层落地（供测试断言）。"""
    applied = _read_applied(updates_root)
    if not applied:
        logger.info("No applied overlay; using image version.")
        return False

    overlay_version = str(applied.get("version") or "")
    image_version = _read_text(image_version_path) or "DEV_VERSION"

    overlay_ver = _parse_semver(overlay_version)
    image_ver = _parse_semver(image_version)
    if overlay_ver is None or image_ver is None:
        logger.warning(
            "Cannot compare overlay (%s) vs image (%s); using image version.",
            overlay_version,
            image_version,
        )
        return False

    if overlay_ver <= image_ver:
        logger.info(
            "Image version %s >= overlay %s; image wins.",
            image_version,
            overlay_version,
        )
        _clear_overlay(updates_root)
        return False

    current = updates_root / "current"
    src_module = current / "backend" / "src" / "module"
    src_dist = current / "webui-dist"
    src_venv = current / ".venv"

    if not src_module.exists():
        logger.warning(
            "Overlay marked applied but %s is missing; skipping.", src_module
        )
        return False

    logger.info(
        "Applying overlay version %s over image %s.", overlay_version, image_version
    )
    try:
        _replace_tree(src_module, app_root / "module")
    except Exception as exc:
        logger.error("Failed to overlay module tree: %s", exc)
        return False

    if src_dist.exists():
        try:
            _replace_tree(src_dist, app_root / "dist")
        except Exception as exc:
            logger.error("Failed to overlay webui dist: %s", exc)

    if src_venv.exists():
        try:
            _replace_tree(src_venv, app_root / ".venv")
            lock_sha = _sha256_file(current / "backend" / "uv.lock")
            if lock_sha:
                (app_root / ".venv" / _VENV_LOCK_MARKER).write_text(
                    lock_sha, encoding="utf-8"
                )
        except Exception as exc:
            logger.error("Failed to overlay staged venv: %s", exc)
    else:
        try:
            _sync_venv_to_lock(current, app_root, baseline_lock)
        except Exception as exc:
            logger.error("Failed to reconcile venv with overlay lock: %s", exc)

    logger.info("Overlay applied successfully.")
    return True


def main() -> int:
    try:
        apply_overlay()
    except Exception as exc:  # 绝不阻断启动
        logger.error("Overlay application errored, continuing boot: %s", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
