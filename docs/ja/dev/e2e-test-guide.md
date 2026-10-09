# E2E テストガイド

エンドツーエンドテストは、本番ビルドの AutoBangumi イメージを、ローカルの決定的な上流サービス（モックの RSS、TMDB、プレーヤー、qBittorrent）に対して実行します。テストは公開サービスにアクセスしません。Docker Compose はループバックアドレスにランダムなポートを公開し、サービス同士は内部ネットワークで通信します。

完全な説明（各テストレーン、診断用の成果物、モックシナリオの追加、qBittorrent イメージのダイジェスト更新）はリポジトリの [`e2e/README.md`](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/e2e/README.md) にあります。このページでは、ローカルで実行する最短の手順だけを示します。

## 準備

- Docker Engine と Compose v2
- Python 3.13 と `uv`
- Node.js 20 と pnpm 9.11

```bash
uv sync --directory backend --locked --group dev
pnpm --dir webui install --frozen-lockfile
pnpm --dir webui exec playwright install --with-deps chromium webkit firefox
```

## テストイメージのビルド

```bash
pnpm --dir webui run build
python3 e2e/scripts/build_test_image.py \
  --version 3.3.999-e2e.1 \
  --image auto-bangumi:e2e \
  --dist webui/dist
```

ビルドスクリプトは、WebUI のビルド成果物と生成したバージョンモジュールを一時的な Docker コンテキストに置きます。ソースツリーには書き込みません。

## 実行

実行のたびに新しいプロジェクト名と作業ディレクトリを使います。作業ディレクトリを使い回すとセットアップ状態も使い回すことになり、初回起動のテストが意味を失います。

```bash
export LANE=runtime
export AB_E2E_PROJECT="ab-e2e-local-$LANE-$$"
export AB_E2E_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ab-e2e-$LANE.XXXXXX")"
export AB_E2E_APP_IMAGE=auto-bangumi:e2e

# ランタイムの API とプロセスのテスト
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- uv run --directory backend pytest src/test/e2e/runtime -m e2e -q
```

| レーン | `--` の後のコマンド | `--profile` |
| --- | --- | --- |
| ランタイム | `uv run --directory backend pytest src/test/e2e/runtime -m e2e -q` | `browser` |
| Chromium デスクトップ | `pnpm --dir webui run test:e2e:chromium --retries=0` | `browser` |
| WebKit モバイル | `pnpm --dir webui run test:e2e:webkit --retries=0` | `browser` |
| 実際の qBittorrent とパッケージ済みイメージ | `python3 e2e/scripts/run_downloader_lane.py` | `downloader` |

- 通常の `pytest` は E2E テストを飛ばします。`-m e2e` を明示する必要があります。
- `stack.py run` は Compose を片付ける前に診断情報を集め、`$AB_E2E_WORK_DIR/artifacts` に書き出します。Playwright のスクリーンショットと動画は `webui/test-results`、HTML レポートは `webui/playwright-report` にあります。
- スタックを止めるには：`python3 e2e/scripts/stack.py stop --profile browser --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR"`。

## CI

`.github/workflows/e2e.yml` は PR ごとに、ランタイムのレーン、ブラウザのレーン（Chromium、WebKit モバイル）、実際のダウンローダーのレーンを実行します。`e2e-nightly.yml` は毎晩 Firefox のレーンを実行し、ブラウザのレーンとダウンローダーのレーンをそれぞれ独立して 2 回実行します。エンドポイントの構造や検証など、より速い契約テストは `backend/src/test/test_api_*.py` にあります。
