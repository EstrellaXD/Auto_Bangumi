#!/bin/bash

# Auto_Bangumi 前端构建脚本
# 编译 Vue.js 前端并移动到后端的 dist 目录

set -e  # 遇到错误立即退出

echo "🚀 开始构建 Auto_Bangumi 前端..."

# 检查是否在项目根目录
if [ ! -d "webui" ] || [ ! -d "backend" ]; then
    echo "❌ 错误: 请在 Auto_Bangumi 项目根目录运行此脚本"
    exit 1
fi

# 进入前端目录
cd webui

echo "📦 安装依赖..."
# 检查是否有 pnpm
if command -v pnpm &> /dev/null; then
    pnpm install
elif command -v npm &> /dev/null; then
    npm install
else
    echo "❌ 错误: 未找到 npm 或 pnpm"
    exit 1
fi

echo "🔧 类型检查..."
# 检查 TypeScript 类型
if command -v pnpm &> /dev/null; then
    pnpm run test:build
else
    npm run test:build
fi

echo "🏗️  构建前端..."
# 构建生产版本
if command -v pnpm &> /dev/null; then
    pnpm run build
else
    npm run build
fi

# 检查构建是否成功
if [ ! -d "dist" ]; then
    echo "❌ 错误: 前端构建失败，未找到 dist 目录"
    exit 1
fi

echo "📂 移动构建文件到后端目录..."
# 返回项目根目录
cd ..

# 备份现有的 dist 目录（如果存在）
if [ -d "backend/src/dist" ]; then
    echo "📋 备份现有 dist 目录..."
    mv backend/src/dist backend/src/dist.backup.$(date +%Y%m%d_%H%M%S)
fi

# 移动新构建的文件
mv webui/dist backend/src/dist

echo "✅ 前端构建完成！"
echo "📍 构建文件已移动到: backend/src/dist"
echo ""
echo "🚀 现在可以启动后端服务:"
echo "   cd backend/src && python main.py"