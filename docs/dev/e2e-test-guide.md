# E2E 测试指南

端到端测试用生产构建的 AutoBangumi 镜像，对接本地的、确定性的上游服务（模拟 RSS、TMDB、播放器与 qBittorrent）。测试不访问任何公网服务。Docker Compose 在回环地址上发布随机端口，服务之间走内部网络。

完整说明（各条测试线、诊断产物、添加模拟场景、更新 qBittorrent 镜像摘要）在仓库的 [`e2e/README.md`](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/e2e/README.md)。本页只给出本地运行的最短路径。

## 准备

- Docker Engine 与 Compose v2
- Python 3.13 与 `uv`
- Node.js 20 与 pnpm 9.11

```bash
uv sync --directory backend --locked --group dev
pnpm --dir webui install --frozen-lockfile
pnpm --dir webui exec playwright install --with-deps chromium webkit firefox
```

## 构建测试镜像

```bash
pnpm --dir webui run build
python3 e2e/scripts/build_test_image.py \
  --version 3.3.999-e2e.1 \
  --image auto-bangumi:e2e \
  --dist webui/dist
```

构建脚本在临时的 Docker 上下文里放入 WebUI 产物和生成的版本模块，不会写入源码树。

## 运行

每次运行都用新的项目名和工作目录。重用工作目录会同时重用设置状态，首次运行的覆盖就失效了。

```bash
export LANE=runtime
export AB_E2E_PROJECT="ab-e2e-local-$LANE-$$"
export AB_E2E_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ab-e2e-$LANE.XXXXXX")"
export AB_E2E_APP_IMAGE=auto-bangumi:e2e

# 运行时 API 与进程测试
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- uv run --directory backend pytest src/test/e2e/runtime -m e2e -q
```

| 测试线 | `--` 之后的命令 | `--profile` |
| --- | --- | --- |
| 运行时 | `uv run --directory backend pytest src/test/e2e/runtime -m e2e -q` | `browser` |
| Chromium 桌面 | `pnpm --dir webui run test:e2e:chromium --retries=0` | `browser` |
| WebKit 移动端 | `pnpm --dir webui run test:e2e:webkit --retries=0` | `browser` |
| 真实 qBittorrent 与打包镜像 | `python3 e2e/scripts/run_downloader_lane.py` | `downloader` |

- 普通的 `pytest` 会跳过 E2E 用例，必须显式传入 `-m e2e`。
- `stack.py run` 在拆除 Compose 之前收集诊断信息，写到 `$AB_E2E_WORK_DIR/artifacts`。Playwright 的截图与视频在 `webui/test-results`，HTML 报告在 `webui/playwright-report`。
- 停止一个栈：`python3 e2e/scripts/stack.py stop --profile browser --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR"`。

## CI

`.github/workflows/e2e.yml` 在每个 PR 上运行运行时线、浏览器线（Chromium、WebKit 移动端）和真实下载器线。`e2e-nightly.yml` 每晚运行 Firefox 线，并把浏览器线和下载器线各独立运行两遍。端点结构、参数校验等更快的契约测试仍在 `backend/src/test/test_api_*.py` 中。
