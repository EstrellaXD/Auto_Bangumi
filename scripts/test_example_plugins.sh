#!/usr/bin/env bash
# 逐个示例插件：校验清单，再跑它自己的测试（与插件作者在示例目录里 `uv run pytest` 一致）。
# 在仓库根目录运行；CI 与本地共用。
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
for dir in "$root"/examples/plugins/*/; do
  name="$(basename "$dir")"
  echo "== $name"
  uv run ab-plugin validate "$dir"
  if [ -d "$dir/tests" ]; then
    uv run pytest -q -c "$dir/pyproject.toml" --rootdir "$dir" -p no:cacheprovider "$dir/tests"
  fi
done
