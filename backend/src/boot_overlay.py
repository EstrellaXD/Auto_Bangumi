"""容器启动时应用在线更新覆盖层（在应用启动前、以 root 运行）。

由 entrypoint.sh 在启动 main.py 之前调用：

    python /app/boot_overlay.py

信任模型：持久卷 ``config/updates/`` 归 ab（应用用户）所有，其中一切内容都
**不可信**。唯一的信任根是镜像自带的公钥（``/app/ab_update_pubkey.pem``）与
CI 签名的 ``bundle.zip`` + ``bundle.zip.sig``。因此每次启动都重新验签留存的
zip，并且 module 树 / 前端 dist **直接从验签通过的 zip 解包**，绝不从 ab 可写
的 ``current/`` 目录复制——否则拿到 ab 权限的攻击者伪造 applied.json/current
即可让 root 把任意代码落到 /app 并跨镜像升级持久化。

版本比较也以 zip 内 manifest 为准：覆盖层版本高于镜像基线（``/app/
IMAGE_VERSION``）才应用，否则清除过期覆盖层，镜像版本生效。

staged ``.venv`` 是 apply 时由应用（ab 身份）按已验签 lockfile 预装的，无法
被 CI 签名；boot 只做复制、从不执行其内容，运行期由 ab 加载——被篡改最多
维持 ab 级持久化（攻击者本就具备），不构成提权面。

关键约束：本脚本位于 ``/app/boot_overlay.py``，**不在** 覆盖层会替换的
``/app/module`` 里，因此始终是镜像自带的稳定版本在做决策；这里的验签才是
安全边界（apply 时的验签跑在可能已被覆盖的 module 代码里，只是尽早失败的
用户体验）。任何一步失败都不得阻断启动——记录日志后回退镜像版本继续启动。
"""

import errno
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
PUBKEY_PATH = APP_ROOT / "ab_update_pubkey.pem"


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


def _clear_and_fill(dst: Path, src: Path) -> None:
    """删光 dst 的子项后从 src 复制（EXDEV 兜底的非原子核心步骤）。"""
    for child in list(dst.iterdir()):
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir() and not child.is_symlink():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def _replace_contents(dst: Path, src: Path) -> None:
    """让 dst 的子项与 src 一致，但不 rename dst 本身。

    这是 EXDEV 的兜底路径：overlayfs 拒绝把镜像下层目录跨挂载边界 rename，
    但逐文件删/写会触发 copy-up，因而可行。非原子——中途失败（磁盘满/IO
    错误）会留下"删光了但没灌满"的残树，启动进去必然 ImportError 崩溃循环。
    因此先把 dst 现有内容快照到 .ab_bak：快照失败则 dst 未被触碰、直接放弃；
    填充失败则从快照恢复旧树后再抛出，保证 dst 要么是新树要么是旧树。
    """
    backup = dst.parent / (dst.name + ".ab_bak")
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(dst, backup)
    try:
        _clear_and_fill(dst, src)
    except BaseException:
        try:
            _clear_and_fill(dst, backup)
            # 恢复也是 root 在复制：属主变回 root，受限 UMASK 下的 600
            # 模式会让 ab 读不了恢复出来的旧树——同样要交还应用用户
            # （成功路径的 chown 在上层，异常路径走不到那里）。
            _chown_app_tree(dst)
        except Exception:
            logger.critical(
                "Failed to restore %s from its snapshot after a partial "
                "overlay write; the tree may be incomplete.",
                dst,
            )
        raise
    finally:
        shutil.rmtree(backup, ignore_errors=True)


def _chown_app_tree(path: Path) -> None:
    """把覆盖层落地的树交还应用用户（ab）。

    boot_overlay 以 root 运行；extractall/copytree 产物的权限跟随 UMASK
    （entrypoint 在调用前已 ``umask ${UMASK}``），受限 UMASK（如 077）下是
    600/700 root:root——以 ab 运行的 main.py 读不了 /app/module，启动即
    ImportError 崩溃循环。落地后统一 chown 给 ab，使可读性与 UMASK 无关
    （3.2 的每次启动全量 ``chown -R /app`` 已移除，必须在这里补上）。
    只处理刚写入的树，不触碰镜像层文件，避免无谓的 overlayfs copy-up。
    """
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    try:
        import pwd

        pwd.getpwnam("ab")
    except (ImportError, KeyError):
        logger.warning("User 'ab' not found; skipping ownership fix for %s", path)
        return
    import subprocess

    subprocess.run(["chown", "-R", "ab:ab", str(path)], check=False)


def _replace_tree(src: Path, dst: Path) -> None:
    """用 src 原子地替换 dst（先复制到 .new，再 rename 交换，最后清理 .old）。

    ``/app/module`` 等目录来自镜像的 overlayfs 下层，某些 overlay/内核组合下
    无法把下层目录 rename 到新路径，会抛 ``EXDEV``（Errno 18，跨设备链接）——
    这正是绑定挂载/overlay 布局下在线更新“报告成功却停在旧版本”的根因。
    此时 dst 未被改动（rename 是原子的），退回到就地替换 dst 内容。
    """
    parent = dst.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = parent / (dst.name + ".ab_new")
    old = parent / (dst.name + ".ab_old")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp)
    if old.exists():
        shutil.rmtree(old)
    try:
        if dst.exists():
            os.rename(dst, old)
        os.rename(tmp, dst)
        if old.exists():
            shutil.rmtree(old)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        logger.warning(
            "Cannot rename %s across the mount boundary (EXDEV); "
            "replacing its contents in place instead.",
            dst,
        )
        # 若前一步部分完成把 dst 挪到了 old，先还原，保证 dst 存在。
        if not dst.exists() and old.exists():
            shutil.copytree(old, dst)
        _replace_contents(dst, tmp)
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(old, ignore_errors=True)


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
    verified_root: Path, app_root: Path, baseline_lock: Path | None
) -> None:
    """把 /app/.venv 与当前生效覆盖层的 uv.lock 对齐。

    正常路径下依赖在 apply 时已预装进 staged .venv，这里不会做任何事；只有
    覆盖层带 uv.lock 却没有 staged .venv（回滚到旧覆盖层、或旧版 updater
    落盘的覆盖层）且 lock 与 venv 当前对应的 lock 不一致时才补一次
    uv sync——否则回滚后的旧代码会跑在新依赖上直接启动崩溃。

    ``verified_root`` 必须是**已验签 zip 的解包目录**（pyproject/uv.lock 可信）。
    uv sync 绝不以 root 运行——lockfile 驱动的构建钩子等价于任意代码执行，
    root 下即提权；以 root 启动时降权到 ab 执行。
    失败只记日志：用现有 venv 继续启动好过卡死在启动前。
    """
    overlay_lock = verified_root / "backend" / "uv.lock"
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
    run_kwargs: dict = {}
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        try:
            import pwd

            pwd.getpwnam("ab")
        except (ImportError, KeyError):
            logger.error("User 'ab' not found; refusing to run uv sync as root.")
            return
        # 降权执行前先把 venv 交给 ab，否则无写权限。
        subprocess.run(["chown", "-R", "ab:ab", str(app_root / ".venv")], check=False)
        env["HOME"] = "/home/ab"
        run_kwargs = {"user": "ab", "group": "ab"}
    logger.info("No staged venv; syncing /app/.venv against overlay uv.lock.")
    try:
        subprocess.run(
            [uv, "sync", "--frozen", "--no-dev"],
            cwd=str(verified_root / "backend"),
            env=env,
            check=True,
            **run_kwargs,
        )
        marker.write_text(desired, encoding="utf-8")
    except Exception as exc:
        logger.error("venv reconcile failed; continuing with existing venv: %s", exc)


def _clear_overlay(updates_root: Path) -> None:
    """删除过期/不可信覆盖层标记与 bundle，使运行状态回归镜像版本。"""
    try:
        for name in (
            "applied.json",
            "bundle.zip",
            "bundle.zip.sig",
            "bundle-backup.zip",
            "bundle-backup.zip.sig",
        ):
            target = updates_root / name
            if target.exists():
                target.unlink()
        logger.info("Cleared stale overlay marker; running image version.")
    except OSError as exc:
        logger.warning("Failed to clear stale overlay: %s", exc)


def _verify_bundle(bundle: Path, sig: Path, pubkey_path: Path) -> bool:
    """用镜像自带公钥验证 bundle 的 ed25519 签名；任何失败都拒绝覆盖层。"""
    import base64

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except ImportError:
        logger.error("cryptography unavailable; refusing overlay.")
        return False
    try:
        public_key = load_pem_public_key(pubkey_path.read_bytes())
        if not isinstance(public_key, Ed25519PublicKey):
            logger.error("Overlay pubkey is not ed25519; refusing overlay.")
            return False
        signature = base64.b64decode(sig.read_text().strip(), validate=True)
        public_key.verify(signature, bundle.read_bytes())
        return True
    except Exception as exc:  # noqa: BLE001 - 验签失败必须拒绝
        logger.error("Bundle signature verification failed: %s", exc)
        return False


def _read_zip_manifest(bundle: Path) -> dict | None:
    import json
    import zipfile

    try:
        with zipfile.ZipFile(bundle) as zf:
            data = json.loads(zf.read("manifest.json"))
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _safe_extract_zip(bundle: Path, dest: Path) -> None:
    """解压已验签 zip 到 dest，拒绝绝对路径/`..` 越界成员（防 zip-slip）。"""
    import zipfile

    dest_resolved = dest.resolve()
    with zipfile.ZipFile(bundle) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not target.is_relative_to(dest_resolved):
                raise ValueError(f"Unsafe path in bundle: {member}")
        zf.extractall(dest)


def apply_overlay(
    app_root: Path = APP_ROOT,
    updates_root: Path = UPDATES_ROOT,
    image_version_path: Path = IMAGE_VERSION_PATH,
    baseline_lock: Path | None = None,
    pubkey_path: Path = PUBKEY_PATH,
) -> bool:
    """验签并应用覆盖层。返回是否实际把覆盖层落地（供测试断言）。"""
    import tempfile

    applied = _read_applied(updates_root)
    bundle = updates_root / "bundle.zip"
    sig = updates_root / "bundle.zip.sig"

    if not bundle.exists() or not sig.exists():
        if applied:
            logger.warning(
                "Overlay marker present but signed bundle is missing; "
                "refusing legacy/unsigned overlay."
            )
            _clear_overlay(updates_root)
        else:
            logger.info("No applied overlay; using image version.")
        return False

    if not _verify_bundle(bundle, sig, pubkey_path):
        _clear_overlay(updates_root)
        return False

    # 版本以已验签 zip 内的 manifest 为准；ab 可写的 applied.json 只是 UI 状态。
    manifest = _read_zip_manifest(bundle) or {}
    overlay_version = str(manifest.get("version") or "")
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

    logger.info(
        "Applying overlay version %s over image %s (signature verified).",
        overlay_version,
        image_version,
    )
    # module 树与前端 dist 直接从已验签 zip 解包到 root 私有临时目录，
    # 不从 ab 可写的 current/ 复制。
    tmp = Path(tempfile.mkdtemp(prefix="ab-overlay-"))
    try:
        try:
            _safe_extract_zip(bundle, tmp)
        except Exception as exc:
            logger.error("Failed to unpack verified bundle: %s", exc)
            return False

        src_module = tmp / "backend" / "src" / "module"
        if not src_module.exists():
            logger.warning("Verified bundle has no module tree; skipping.")
            return False

        try:
            _replace_tree(src_module, app_root / "module")
        except Exception as exc:
            logger.error("Failed to overlay module tree: %s", exc)
            return False
        _chown_app_tree(app_root / "module")

        src_dist = tmp / "webui-dist"
        if src_dist.exists():
            try:
                _replace_tree(src_dist, app_root / "dist")
                _chown_app_tree(app_root / "dist")
            except Exception as exc:
                logger.error("Failed to overlay webui dist: %s", exc)

        # staged venv 见模块 docstring：只复制、从不以 root 执行其内容。
        src_venv = updates_root / "current" / ".venv"
        if src_venv.exists():
            try:
                _replace_tree(src_venv, app_root / ".venv")
                lock_sha = _sha256_file(tmp / "backend" / "uv.lock")
                if lock_sha:
                    (app_root / ".venv" / _VENV_LOCK_MARKER).write_text(
                        lock_sha, encoding="utf-8"
                    )
                _chown_app_tree(app_root / ".venv")
            except Exception as exc:
                logger.error("Failed to overlay staged venv: %s", exc)
        else:
            try:
                _sync_venv_to_lock(tmp, app_root, baseline_lock)
            except Exception as exc:
                logger.error("Failed to reconcile venv with overlay lock: %s", exc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

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
