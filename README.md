# 三维重建项目 (3D Reconstruction Project)

本项目专注于三维重建工作流，特别是利用 **MipMap Engine SDK** 进行开发。

## 文档说明

`docs/` 目录下提供了完善的技术文档体系：

### 核心文档（推荐阅读）

*   **[用户使用手册](docs/user_guide.md)** ⭐
    *   **快速开始**：从安装依赖、准备数据到运行重建的完整步骤。
    *   **配置说明**：基础参数与进阶参数的详细解读。
    *   **运行方式**：命令行、Python 代码、Docker 容器等多种执行方式。
    *   **常见问题**：GPU 配置、内存不足等问题的排查指南。

*   **[架构设计说明书](docs/architecture_design.md)**
    *   SDK 的模块化架构、DooD 调度机制与数据流向。

### 参考文档

*   **[MipMap SDK 集成指南](docs/mipmap_sdk_integration_examples.md)** - CLI 与 JSON 配置参考
*   **[MipMap SDK 研究报告](docs/mipmap_sdk_research_report.md)** - 能力概览与格式支持

## 架构与路线图 (Architecture & Roadmap)

### 当前架构 (v1.0) - 指挥官-工兵模式 (DooD)
本 SDK 采用 **DooD (Docker-outside-of-Docker)** 机制进行跨容器调度。

详细的技术架构、组件交互和路径映射逻辑请参考：
👉 **[架构设计说明书](docs/architecture_design.md)**

### 未来路线图 - Windows 原生 (Native Windows)
尽管当前版本完美支持 Windows (Docker Desktop)，我们计划在未来版本支持 **Windows 原生执行**，以对齐桌面端软件标准（如 MipMap .exe）。

**原生化路径:**
1.  **重构 Adapters**: 实现 `OpenSfMWindowsAdapter` 以调用 `.exe` 而非 `docker run`。
2.  **交叉编译**: 在 Windows 上使用 MSVC/Ninja 源码编译 OpenSfM 和 OpenSplat。
3.  **打包发布**: 使用 PyInstaller 将 Python SDK 打包为 `.exe`。

## 快速开始

参考 `docs/user_guide.md` 运行重建任务：

1. 准备项目目录及 `images/` 子目录。
2. 配置 `config.yaml`。
3. 运行：
    ```bash
    python -m my_sdk.main --config config.yaml
    ```
