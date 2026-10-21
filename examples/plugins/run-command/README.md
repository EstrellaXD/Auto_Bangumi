# 运行外部命令（示例插件）

种子整理完成（`torrent.organized`）或文件被重命名（`file.renamed`）后运行一条外部命令，例如自己的清理脚本、FileBot、hlink。演示：

- `@subscribe("*", timeout=...)` 订阅全部事件，按配置过滤；处理超时放宽到命令超时之上
- `asyncio.create_subprocess_exec` 直接执行参数列表，不经过 shell
- 命令超时被杀掉，退出码非 0 时记录 stderr 末尾；失败只记日志，不让插件被熔断

## 配置

| 字段 | 说明 |
| --- | --- |
| 命令 | 程序及其参数，每项一个，如 `/config/scripts/link.sh`、`{files}`。不经过 shell，管道、重定向、`$变量` 都不会展开；需要时把命令写成脚本 |
| 事件 | 在哪些事件后运行，默认只有 `torrent.organized` |
| 超时（秒） | 默认 300，最大 3600。超时后杀掉命令 |

## 传给命令的字段

每个字段既是环境变量，也可以在参数里写成占位符（环境变量名去掉 `AB_` 后的小写，如 `{torrent_hash}`）。未知的占位符原样保留。

| 环境变量 | 事件 | 内容 |
| --- | --- | --- |
| `AB_EVENT` | 全部 | 事件名 |
| `AB_BANGUMI_ID` | 全部 | 番剧 id；旧种子没有 `ab:<id>` 标签时为空 |
| `AB_DOWNLOADER_ID` | 全部 | 下载器实例 id |
| `AB_TORRENT_HASH` | `torrent.organized` | 种子 hash |
| `AB_FILES` | `torrent.organized` | 正片与字幕的最终路径，每行一个 |
| `AB_OLD_PATH` / `AB_NEW_PATH` | `file.renamed` | 重命名前后的路径 |
| `AB_FILE_KIND` | `file.renamed` | `media` 或 `subtitle` |

事件里没有种子的保存目录，需要时从 `AB_FILES` 取。路径是**下载器视角**，AutoBangumi 与下载器的挂载不同时，脚本要自己换算。命令按事件顺序逐个运行，一个命令运行时后面的事件排队。

`torrent.organized` 的投递是「至少一次」：每次 AutoBangumi 重启，已整理的种子会再发布一次。脚本必须幂等。

## 安装

```bash
cp -r examples/plugins/run-command config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用并填写命令。Docker 中命令在 AutoBangumi 的容器里运行，只能使用镜像里有的程序和挂载进来的脚本。

## 测试

```bash
cd examples/plugins/run-command && uv run pytest
```

对应 issue：[#897](https://github.com/EstrellaXD/Auto_Bangumi/issues/897)、[#668](https://github.com/EstrellaXD/Auto_Bangumi/issues/668)
