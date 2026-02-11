# 3D Reconstruction SDK 版本发布指南

为了保持算法迭代的可追溯性，本项目采用 **“代码版本 = 镜像版本 = Git 标签”** 的同步管理机制。

## 核心流程

每当你完成了一项算法改进或 Bug 修复，请按以下步骤发布新版本：

### 1. 更新版本号
修改项目根目录下的 `.env` 文件中的 `VERSION` 变量。
建议遵循 [语义化版本 (SemVer)](https://semver.org/lang/zh-CN/) 规范：
*   **主版本号 (Major)**: 做了不兼容的 API 修改。
*   **次版本号 (Minor)**: 做了向下兼容的功能性新增。
*   **修订号 (Patch)**: 做了向下兼容的问题修正（如刚才的质量报告修复）。

```text
# .env 示例
VERSION=1.0.1
```

### 2. 执行打包脚本
在终端运行提供的自动化脚本。它会自动执行 Docker 构建、打标签以及 Git 提交。

```bash
chmod +x publish_image.sh
./publish_image.sh
```

该脚本会自动完成：
*   `docker compose build sdk` (生成 `recon3d-sdk:1.0.1`)
*   `docker tag ... latest` (更新本地最新标签)
*   `git commit` & `git tag v1.0.1`

### 3. 发布前 Submodule 检查
如果本次版本涉及 `3DGS-to-PC`，发布前先执行以下检查：

```bash
git submodule status
git -C 3DGS-to-PC log --oneline -n 1
```

要求：
* `3DGS-to-PC` 对应 commit 已经推送到远端 `git@github.com:YHZN-REPOS/3DGS-to-PC.git`
* 父仓库提交中已包含最新 submodule 指针（`git add 3DGS-to-PC` 后提交）

### 4. 推送到远程
脚本执行完成后，按提示手动推送：

```bash
git push origin main
git push origin --tags
```

---

## 为什么这样做？

1.  **可回滚**: 如果 `1.0.2` 版本在某种场景下崩了，你可以立刻通过 `VERSION=1.0.1 docker compose run ...` 换回旧版本测试。
2.  **环境一致性**: 镜像版本号与 Git 标签绑定，你可以随时查到某一个镜像是由哪份代码构建出来的。
3.  **开发友好**: 配合 `.env` 管理，不需要在 `docker-compose.yml` 中硬编码任何版本信息。

## 常见问题

**Q: 我只想在本地测试，不想更新版本号怎么办？**
A: 直接使用 `docker compose build` 即可，它会默认使用 `latest` 标签（如果你没改 `.env`），或者直接使用 `sdk-dev` 服务进行热更新开发。

**Q: 标签打错了能改吗？**
A: 可以，但建议通过递增版本号（如 `1.0.2`）来解决，而不是覆盖旧标签，以保持历史记录的完整性。

**Q: 发布机构建失败，提示缺少 `3DGS-to-PC` 文件怎么办？**
A: 通常是拉取代码时没有初始化 submodule。请使用 `git clone --recurse-submodules`，或在已有仓库执行 `git submodule update --init --recursive`。
