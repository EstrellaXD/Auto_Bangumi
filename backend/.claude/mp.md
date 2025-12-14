# MoviePilot 版本管理参考

## 版本文件

位置：项目根目录 `version.py`

```python
APP_VERSION = 'v1.9.19'
```

## CI 工作流 (build.yml)

### 触发条件

```yaml
on:
  workflow_dispatch:  # 手动触发
  push:
    branches:
      - main
    paths:
      - 'version.py'  # 只有 version.py 变化才触发
```

### 读取版本号

```yaml
- name: Get version
  id: get_version
  run: |
    app_version=$(cat version.py | sed -ne "s/APP_VERSION\s=\s'v\(.*\)'/\1/gp")
    echo "APP_VERSION=${app_version}" >> $GITHUB_OUTPUT
```

### 使用版本号

```yaml
# Docker 镜像标签
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    tags: |
      ghcr.io/${{ github.repository }}:${{ steps.get_version.outputs.APP_VERSION }}
      ghcr.io/${{ github.repository }}:latest

# 创建 Release
- name: Create Release
  uses: softprops/action-gh-release@v1
  with:
    tag_name: v${{ steps.get_version.outputs.APP_VERSION }}
    name: v${{ steps.get_version.outputs.APP_VERSION }}
```

## 完整工作流示例

```yaml
name: Build

on:
  workflow_dispatch:
  push:
    branches:
      - main
    paths:
      - 'version.py'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Get version
        id: get_version
        run: |
          app_version=$(cat version.py | sed -ne "s/APP_VERSION\s=\s'v\(.*\)'/\1/gp")
          echo "APP_VERSION=${app_version}" >> $GITHUB_OUTPUT

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          platforms: linux/amd64,linux/arm64
          tags: |
            ghcr.io/${{ github.repository }}:${{ steps.get_version.outputs.APP_VERSION }}
            ghcr.io/${{ github.repository }}:latest

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          tag_name: v${{ steps.get_version.outputs.APP_VERSION }}
          name: v${{ steps.get_version.outputs.APP_VERSION }}
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 发版流程

```
1. 修改 version.py: APP_VERSION = 'v1.9.20'
2. git add version.py
3. git commit -m "release: v1.9.20"
4. git push origin main
5. GitHub Actions 自动:
   - 检测 version.py 变化
   - 读取版本号 1.9.20
   - 构建 Docker 镜像 (tag: 1.9.20, latest)
   - 创建 GitHub Release (tag: v1.9.20)
```

## sed 命令解析

```bash
cat version.py | sed -ne "s/APP_VERSION\s=\s'v\(.*\)'/\1/gp"
```

- `-n`: 不自动打印
- `-e`: 执行脚本
- `s/pattern/replacement/gp`: 替换并打印
- `\s`: 匹配空白字符
- `\(.*\)`: 捕获组，匹配版本号
- `\1`: 引用捕获组

输入: `APP_VERSION = 'v1.9.19'`
输出: `1.9.19`
