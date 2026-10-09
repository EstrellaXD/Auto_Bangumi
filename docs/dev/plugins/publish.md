# 上架插件

插件的源码留在作者自己的公开 GitHub 仓库。要上架或更新插件，作者向 `EstrellaXD/Auto_Bangumi` 提交一个 PR（目标分支 `4.0-dev`），新增或修改一个文件：`plugins/registry/<id>.toml`。

CI 自动检查这个文件指向的代码。维护者阅读代码后合并。合并后 CI 打包、签名并发布到签名目录。

::: tip 版本要求
AutoBangumi 4.0.0-beta.2 及之后的版本信任插件密钥。4.0.0-beta.1 无法从新目录安装插件。
:::

## 登记文件

文件 `plugins/registry/<id>.toml` 只有三个字段：

```toml
repo = "owner/name"   # 公开的 GitHub 仓库
commit = "<40 位完整 SHA>"   # tag 可以移动，SHA 不能
path = "."   # 可选。插件所在子目录，默认是仓库根
```

- 文件名必须等于 `plugin.toml` 里的 `id`。
- `commit` 必须是 40 位完整 SHA。短 SHA 和 tag 会被拒绝。
- 名称、版本、`sdk` 范围、作者、权限都从该 commit 的 `plugin.toml` 读取，不在登记文件里重复写。

一个 PR 可以改多个登记文件。建议一个 PR 只含一个插件。

## 步骤

1. 准备仓库。仓库必须公开。`plugin.toml`、插件代码和 `tests/` 都要提交。有前端时，源码放在 `web-src/`，并提交 `package.json` 和 `pnpm-lock.yaml`。
2. 在本地检查：

   ```bash
   ab-plugin validate .
   uv run pytest
   pnpm install --frozen-lockfile && pnpm build   # 仅有前端时
   ```

   `tests/` 至少要有 1 个测试，且全部通过。`ab-plugin new` 生成的契约测试可以满足这一条。
3. 把代码推送到公开仓库。
4. 取得完整 SHA：

   ```bash
   git rev-parse HEAD
   ```

5. Fork `EstrellaXD/Auto_Bangumi`，新增 `plugins/registry/<id>.toml`，向 `4.0-dev` 提交 PR。PR 里只能改 `plugins/registry/` 下的文件。在 PR 描述中选用插件模板（`?template=plugin.md`），逐项勾选清单。

## CI 规则

工作流 `plugin-registry.yml` 的 `check` 任务在 PR 上运行。它只有只读权限，没有任何 secret。对每个改动的登记文件，它先取回固定的 commit，再按下列规则检查。任何一条不满足，CI 拒绝该条目：

- `commit` 不是 40 位完整 SHA。
- 文件名与清单里的 `id` 不同。
- `id` 与内置插件冲突，或是保留 id。
- `ab-plugin validate` 失败。
- 更新时，版本不高于目录中已有的版本。
- 更新时，`repo` 被修改过。要转让插件，见下文「转让插件」。
- `tests/` 里没有测试，或有测试失败。
- 插件有前端，但没有 `web-src/`。前端必须以源码提交在 `web-src/`，带 `package.json` 和 `pnpm-lock.yaml`。CI 用 pnpm 9 / Node 20 运行 `pnpm install --frozen-lockfile --ignore-scripts && pnpm build`，把 `@autobangumi/plugin-ui` 解析为本仓库的包，并丢弃仓库里已提交的 `web/`。

检查通过后，CI 用 `ab-plugin pack` 打包，并写入 Job Summary：

- 版本变化。
- 对比链接（更新）或目录树链接（新插件）。
- validate 和测试结果。
- 扩展点。
- 声明的权限。
- 是否有前端。
- zip 的 sha256。

## 合并之后

维护者（CODEOWNERS：@EstrellaXD）在对比链接中阅读代码，再合并。

合并后，CI 增量重建目录：`commit` 没变的条目复用已有的 zip。然后用专用的插件签名密钥，给 `catalog.json` 和每个 zip 签名。这把密钥不是在线更新密钥。最后 CI 把文件上传到 GitHub release `plugins`。

用户通过 `GET /api/v1/plugins/catalog` 看到新插件或新版本。签名与目录格式见 [签名与分发](/dev/plugins/signing)。

## 更新插件

1. 在自己的仓库里改代码，并提高 `plugin.toml` 里的 `version`。
2. 推送，用 `git rev-parse HEAD` 取得新的完整 SHA。
3. 向 `4.0-dev` 提交 PR，只把 `plugins/registry/<id>.toml` 里的 `commit` 改成新 SHA。

版本必须高于目录中已有的版本，否则 CI 拒绝。

## 转让插件

更新时不能修改 `repo`。要把插件转给另一个仓库，分两个 PR：

1. 第一个 PR 删除 `plugins/registry/<id>.toml`。
2. 合并后，第二个 PR 用新的 `repo` 重新添加这个文件。此时按新插件检查，版本不受旧版本限制。

## 下架插件

提交 PR 删除 `plugins/registry/<id>.toml`。合并后，该插件从目录中移除。用户已经安装的副本不会被删除。

## 依赖与再分发

- 插件只能依赖标准库和 AutoBangumi 已有的包。需要第三方纯 Python 库时，放进 `vendor/`。
- 不要求许可证。但提交 PR 即表示作者同意 AutoBangumi 在其 release 中再分发打包后的插件。
