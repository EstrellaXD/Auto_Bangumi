"""容器启动时应用在线更新覆盖层（在应用启动前、以 root 运行）。

由 entrypoint.sh 在 `exec ... python main.py` 之前调用：

    python /app/boot_overlay.py

逻辑：从持久卷 ``/app/config/updates/`` 读取 ``applied.json``，当覆盖层版本
**高于** 镜像基线版本（``/app/IMAGE_VERSION``）时，把覆盖层的 module 树覆盖到
``/app/module``、前端 dist 覆盖到 ``/app/dist``，并在 ``uv.lock`` 相对镜像基线
变化时 ``uv sync`` 同步依赖到 ``/app/.venv``；否则（镜像更新或相等）忽略并清除
过期覆盖层，让镜像版本生效。

关键约束：本脚本位于 ``/app/boot_overlay.py``，**不在** 覆盖层会替换的
``/app/module`` 里，因此始终是镜像自带的稳定版本在做决策。任何一步失败都不得
阻断启动——记录日志后回退到镜像版本继续启动。
"""

import hashlib
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: [BootOverlay] %(message)s"
)
logger = logging.getLogger("boot_overlay")

APP_ROOT = Path("/app")
UPDATES_ROOT = APP_ROOT / "config" / "updates"
IMAGE_VERSION_PATH = APP_ROOT / "IMAGE_VERSION"
BASELINE_LOCK = APP_ROOT / "uv.lock"
VENV_PATH = APP_ROOT / ".venv"


def _parse_semver(value: str):
    """解析 semver，失败返回 None。semver 是基础依赖，镜像 venv 中始终可用。"""
    try:
        import semver

        return semver.VersionInfo.parse(value.strip().lstrip("v"))
    except Exception:
        return None


def _sha256(path: Path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
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


def _uv_sync(backend_dir: Path) -> None:
    """按覆盖层的 uv.lock 把依赖同步到应用 venv（best-effort）。"""
    uv = shutil.which("uv")
    if not uv:
        logger.error("uv not found on PATH; cannot sync dependencies for the overlay")
        return
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(VENV_PATH)
    try:
        logger.info("Syncing overlay dependencies with uv (uv.lock changed)...")
        subprocess.run(
            [uv, "sync", "--frozen", "--no-dev"],
            cwd=str(backend_dir),
            env=env,
            check=True,
        )
        logger.info("Dependency sync complete.")
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.error("uv sync failed: %s (continuing with existing venv)", exc)


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
    baseline_lock: Path = BASELINE_LOCK,
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
    overlay_lock = current / "backend" / "uv.lock"

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

    # 依赖同步：覆盖层 uv.lock 相对镜像基线 lock 变化时才 uv sync。
    if overlay_lock.exists():
        overlay_lock_sha = _sha256(overlay_lock)
        baseline_lock_sha = _sha256(baseline_lock) if baseline_lock.exists() else None
        if overlay_lock_sha and overlay_lock_sha != baseline_lock_sha:
            _uv_sync(overlay_lock.parent)
        else:
            logger.info("Dependencies unchanged from image baseline; skip uv sync.")

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
