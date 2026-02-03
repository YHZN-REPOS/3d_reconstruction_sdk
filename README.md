# 三维重建项目 (3D Reconstruction Project)

本项目专注于三维重建工作流，特别是利用 **MipMap Engine SDK** 进行开发。

## 文档说明

`docs/` 目录下提供了完善的技术文档体系：

### 核心文档（推荐阅读）

*   **[用户使用手册](docs/user_guide.md)** ⭐
    *   快速开始、配置说明、运行方式及常见问题排查指南。
*   **[开发者指南](docs/developer_guide.md)**
    *   SDK 核心代码逻辑、接口设计、流程调度与适配器开发规范。
*   **[发布工作流](docs/release_workflow.md)** 🆕
    *   算法迭代后的镜像打包、版本管理（SemVer）与 Git 提交同步流程。
*   **[架构设计说明书](docs/architecture_design.md)**
    *   系统层面的模块化架构、DooD 调度机制与跨容器数据流向。

### 研究与参考

*   **[SDK 竞品分析](docs/sdk_comparison.md)**：对比本 SDK 与 Pix4D、ContextCapture 等商业软件。
*   **[MipMap SDK 集成指南](docs/mipmap_sdk_integration_examples.md)**：底层 CLI 工具与 JSON 参数的详细参考。
*   **[MipMap SDK 研究报告](docs/mipmap_sdk_research_report.md)**：算法能力、性能指标与格式支持评估报告。

### 规划与执行报告

*   **[项目进度报告](docs/project_status_report.md)**：各阶段开发进度、已完成功能与待办事项记录。
*   **[产品推广路线图](docs/promotion_roadmap.md)**：本 SDK 的商业化路径与未来技术演进规划。
*   **[ODM 示例报告 (PDF)](docs/odm_demo_report.pdf)**：OpenDroneMap 产生的原始质量报告示例。

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
