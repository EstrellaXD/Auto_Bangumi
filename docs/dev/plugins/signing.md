# 签名与分发

插件有四种来源，信任级别不同：

| 来源 | 位置 | 签名 | 如何启用 |
| --- | --- | --- | --- |
| 内置 | AB 自带 | 随 AB 发布 | 默认可用 |
| 签名目录 | `config/plugins/<id>/<版本>/` | ed25519 签名，AB 验签 | 调用安装 API，安装即启用 |
| 本地目录 | `config/plugins/local/<id>/` | 无 | 开启「允许未签名插件」后启用 |
| pip 包 | entry point `autobangumi.plugins` | 无 | 同上 |

同名插件的优先级：内置 > 签名目录 > 本地 > pip。未签名插件需要用户在 设置 → 插件 中先开启「允许未签名插件」，再启用它。未开启时，AB 不会执行未签名插件的任何代码。

## 签名目录

AB 从 GitHub release `plugins` 下载 `catalog.json`。目录包含：

```json
{
  "schema": 2,
  "plugins": [
    {
      "id": "ntfy-notifier",
      "name": "ntfy 通知",
      "version": "0.1.0",
      "kind": "plugin",
      "extension_points": ["notifier"],
      "sdk": ">=0.5,<1",
      "min_ab_version": "4.0.0-beta.1",
      "description": "…",
      "asset": "ntfy-notifier-0.1.0.zip",
      "sha256": "…"
    }
  ]
}
```

`catalog.json` 和每个 zip 都有同名的 `.sig` 文件：对文件全部字节做 ed25519 签名，再用 base64 编码。公钥随 AB 镜像分发，与在线更新使用同一把密钥。

安装时 AB 依次检查：

1. `catalog.json` 的签名。
2. zip 的 sha256 与签名。拒绝未签名和坏签名的包。
3. 解包时防 zip-slip，拒绝路径越界。
4. 清单必须通过 `ab-plugin validate` 同等的校验。清单的 `id`、`version` 必须与目录条目一致，`sdk` 范围必须包含当前 SDK，AB 版本必须不低于 `min_ab_version`。
5. id 不能是保留 id（`core`、`local`），也不能与内置插件同名。

通过后插件解包到 `config/plugins/<id>/<版本>/`，并写入指向该版本的 `installed.json`，然后加载并启用。卸载只删除带 `installed.json` 的目录，不会删除用户的本地插件。

签名目录的插件只能依赖标准库和 AB 已有的包，不做 pip 安装。需要第三方纯 Python 库时放进 `vendor/`。

::: tip 在 WebUI 中安装
在 设置 → 插件 的「插件目录」区点击「浏览目录」，可以安装、更新目录中的插件。经目录安装的插件卡片上有「卸载」按钮；内置、本地和 pip 插件没有。
:::

API：

| 请求 | 说明 |
| --- | --- |
| `GET /api/v1/plugins/catalog` | 目录条目加本机已装版本；目录不可达返回 502 |
| `POST /api/v1/plugins/{id}/install` | 安装并启用 |
| `DELETE /api/v1/plugins/{id}` | 卸载 |

::: warning 保留路径
`/plugins/{id}/install` 和 `/plugins/catalog` 由宿主占用。插件自己的 `api_router` 不能使用 `install`、`catalog` 或 `web` 作为路由路径。
:::

## 发布一个插件

只有持有签名私钥的维护者能发布目录。流程：

1. 作者：`ab-plugin pack .`，得到 zip。
2. 作者：在 GitHub issue 里提交 zip 和源码地址，申请上架。
3. 维护者审核源码后，对一个或多个 zip 运行：

   ```bash
   uv run --no-project --with cryptography python scripts/build_plugin_catalog.py \
       --key ~/.autobangumi/update-signing-key.pem --min-ab 4.0.0-beta.1 \
       --out release-assets dist/*.zip
   ```

   脚本输出 `catalog.json`、各 zip 及其 `.sig`。`--min-ab` 不要写成 `4.0.0`：按 semver，`4.0.0-beta.N` 低于 `4.0.0`，4.0 beta 用户将无法安装。
4. 维护者把整个目录上传到 release `plugins`（覆盖旧文件）。

用户端通过 `GET /api/v1/plugins/catalog` 看到新版本。

## 发布 SDK

SDK 轮子与插件开发 skill 由 CI 构建，附在每个 4.0 beta / 正式版的 GitHub Release 上，维护者不需要手动发布。下载和安装见 [获取 SDK](/dev/plugins/sdk)。
