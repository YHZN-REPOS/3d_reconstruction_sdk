#!/bin/bash
# =============================================================================
# SDK 镜像打包与版本发布脚本
# =============================================================================

# 1. 自动从 .env 文件读取版本号
if [ -f .env ]; then
    VERSION=$(grep "^VERSION=" .env | cut -d '=' -f2)
else
    echo "错误: 未找到 .env 文件"
    exit 1
fi

if [ -z "$VERSION" ]; then
    echo "错误: .env 文件中未定义 VERSION"
    exit 1
fi

echo "--- 开始发布版本: v$VERSION ---"

# 2. 调用 Docker Compose 构建 SDK 镜像
# 这会自动使用 .env 中的 VERSION 变量作为标签
echo "[1/4] 正在构建 Docker 镜像 (recon3d-sdk:$VERSION)..."
docker compose build sdk

if [ $? -ne 0 ]; then
    echo "错误: 镜像构建失败"
    exit 1
fi

# 3. 为当前版本打上 latest 标签以便日常使用
echo "[2/4] 更新 latest 标签..."
docker tag recon3d-sdk:$VERSION recon3d-sdk:latest

# 4. 提交代码并打 Git Tag
echo "[3/4] 正在提交代码变更..."
git add .
# 允许无变更提交（用于仅重新打标签的情况，虽然不推荐）
git commit -m "chore: release version $VERSION" || echo "提醒: 无代码变更需要提交"

echo "[4/4] 正在检查并创建 Git 标签 (v$VERSION)..."
# 修正后的逻辑：如果标签已存在，报错并退出，保护版本唯一性
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo ""
    echo "================================================================="
    echo "❌ 错误: 标签 v$VERSION 已存在！"
    echo "-----------------------------------------------------------------"
    echo "为了防止版本回溯和代码混乱，不允许覆盖已发布的版本标签。"
    echo "建议操作："
    echo "  1. 修改 .env 中的 VERSION 递增版本号 (如 1.0.1 -> 1.0.2)"
    echo "  2. 如果您确信要覆盖本地标签且尚未推送，请手动运行:"
    echo "     git tag -d v$VERSION"
    echo "================================================================="
    exit 1
fi

git tag -a "v$VERSION" -m "Release version $VERSION"

echo "================================================================="
echo "✅ 本地发布流程完成!"
echo "版本号: $VERSION"
echo "-----------------------------------------------------------------"
echo "请手动执行以下命令推送到远程仓库:"
echo "  git push origin $(git rev-parse --abbrev-ref HEAD)"
echo "  git push origin v$VERSION"
echo "================================================================="
