"""生成并签名插件目录（``plugins`` tag 的发布产物）。

用法（需要更新签名私钥，见 CLAUDE.md 的发布说明）::

    uv run --no-project --with cryptography python scripts/build_plugin_catalog.py \
        --key ~/.autobangumi/update-signing-key.pem --min-ab 4.0.0 \
        --out release-assets  dist/*.zip

输入是 ``ab-plugin pack`` 打出的 zip。输出目录里有 ``catalog.json``、每个 zip 以及
它们的 ``.sig``（对文件全部字节做 ed25519 签名，base64 文本），一并上传到 GitHub
release ``plugins`` 即可。安装端的校验见 ``backend/src/module/plugin/installer.py``。
"""

import argparse
import base64
import hashlib
import json
import shutil
import tomllib
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

CATALOG_SCHEMA = 2


def _entry(archive: Path, min_ab: str) -> dict:
    with zipfile.ZipFile(archive) as zf:
        plugin = tomllib.loads(zf.read("plugin.toml").decode("utf-8"))["plugin"]
    return {
        "id": plugin["id"],
        "name": plugin["name"],
        "version": plugin["version"],
        "kind": "plugin",
        "extension_points": plugin.get("extension_points", []),
        "sdk": plugin["sdk"],
        "min_ab_version": min_ab,
        "description": plugin.get("description", ""),
        "asset": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }


def _sign(key: Ed25519PrivateKey, path: Path) -> None:
    signature = key.sign(path.read_bytes())
    Path(str(path) + ".sig").write_text(base64.b64encode(signature).decode() + "\n")


def build(archives: list[Path], out: Path, key_path: Path, min_ab: str) -> Path:
    key = load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("签名密钥必须是 ed25519")
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for archive in sorted(archives):
        entries.append(_entry(archive, min_ab))
        shutil.copy2(archive, out / archive.name)
        _sign(key, out / archive.name)
    catalog = out / "catalog.json"
    catalog.write_text(
        json.dumps({"schema": CATALOG_SCHEMA, "plugins": entries}, indent=2) + "\n",
        encoding="utf-8",
    )
    _sign(key, catalog)
    return catalog


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--min-ab", default="4.0.0")
    args = parser.parse_args()
    print(build(args.archives, args.out, args.key, args.min_ab))
