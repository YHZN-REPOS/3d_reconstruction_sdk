# 三维重建项目 (3D Reconstruction Project)

本项目专注于三维重建工作流，特别是利用 **MipMap Engine SDK** 进行开发。

## 文档说明

关于 MipMap SDK 集成和研究的详细文档请见 `docs/` 目录：111

*   **[集成指南 (CLI & JSON)](docs/mipmap_sdk_integration_examples.md)**
    *   详细说明如何通过命令行 (`reconstruct_full_engine`) 调用 MipMap 引擎。
    *   包含 `task_json` 配置文件的完整参考，包括所有支持参数的列表和一个有效的 JSON 示例。
    
*   **[研究报告](docs/mipmap_sdk_research_report.md)**
    *   MipMap SDK 能力的高层概览。
    *   总结支持的输入数据（航拍影像、激光雷达）和输出格式（OSGB, 3D Tiles, OBJ 等）。

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
