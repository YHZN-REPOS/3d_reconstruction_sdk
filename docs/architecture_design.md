# SDK 架构设计

本文档详细介绍了 3D Reconstruction SDK 的底层架构设计。

## 1. 设计哲学：指挥官-工兵模式 (Commander-Worker)

本 SDK 并没有试图在一个复杂的单一环境中运行所有三维重建算法（这通常需要配置复杂的 CUDA、PyTorch 和各种 C++ 编译环境），而是采用了**轻量级调度器 + 容器化算法**的设计。

- **指挥官 (SDK Core/Python)**: 负责配置文件读取、目录创建、算法编排、断点续跑逻辑和日志记录。它是一个极轻量级的容器。
- **工兵 (Algorithm Containers)**: 每个算法（如 OpenSfM, OpenSplat）都封装在自己的 Docker 镜像中。它们只负责执行具体的计算任务，完成后即销毁。

## 2. 核心架构图

SDK 采用 **DooD (Docker-outside-of-Docker)** 机制，允许 SDK 容器动态启动算法容器。

```mermaid
graph TD
    User([用户]) -->|运行| SDK[SDK Core 容器]
    
    subgraph "宿主机 (Docker Host)"
        Socket[/var/run/docker.sock]
        DataDir[(项目数据目录)]
    end

    SDK -->|1. 挂载| Socket
    SDK -->|2. 挂载| DataDir
    
    SDK -->|3. 指令| DockerAPI[Docker Engine API]
    DockerAPI -->|4. 启动| OpenSfM[OpenSfM/ODM 容器]
    DockerAPI -->|5. 启动| OpenSplat[OpenSplat 容器]
    
    OpenSfM <-->|读写数据| DataDir
    OpenSplat <-->|读写数据| DataDir
```

## 3. 核心组件

### 3.1 ReconstructionContext (上下文)
这是 SDK 的“状态机”。它持有：
- 当前运行的所有路径（`run_dir`, `sparse_model_path` 等）。
- 用户的任务配置。
- **宿主机路径映射**：这是 DooD 模式的关键，它知道当前容器目录在宿主机上的实际路径，从而告诉 Docker Engine 如何为子容器进行挂载。

### 3.2 Adapters (适配器)
适配器实现了 `SfMStrategy` 或 `ReconstructionStrategy` 接口。它们的职责是：
1. 从 `Context` 中提取参数。
2. 构造适合特定算法镜像的 `docker run` 命令。
3. 通过 `DockerRunner` 执行并捕获结果。

### 3.3 DockerRunner (执行器)
封装了具体的 subprocess 调用逻辑，并提供：
- **实时日志流推送**。
- **进度百分比提取**。
- **资源限制控制**（如 GPU/CPU 分配）。

## 4. 关键机制：DooD & 路径一致性

为了让容器内的 SDK 能够调度同一台宿主机上的其他容器，需要满足：

1. **套接字挂载**: `docker run -v /var/run/docker.sock:/var/run/docker.sock ...`
2. **路径虚拟化**:
   - SDK 容器本身可能挂载在 `/project`。
   - 算法容器也挂载在 `/project`。
   - 这确保了算法容器生成的绝对路径，SDK 核心也能直接访问。

## 5. 详细数据流向与中间件

SDK 通过 `ReconstructionContext` 对象在不同算法容器之间传递状态。以下是核心数据流向的详细分解：

### 5.1 输入 (Input)
- **原始图像**: 位于 `images/`。
- **任务配置**: `config.yaml` 被解析为 `TaskConfig` 对象。

### 5.2 阶段一：空三重建 (SfM Stage)
- **容器环境**: `opendronemap/odm:latest`
- **挂载**: 
  - 宿主机项目工作目录 -> 容器 `/datasets/project`
  - 宿主机图片目录 -> 容器 `/datasets/project/images`
- **关键输出**:
  - `opensfm/reconstruction.json`: 存储相机内参、外参和稀疏点集合。
  - `opensfm/undistorted/`: 包含根据估计的相机参数去畸变后的图像，这是下游高斯溅射训练的**核心输入**。
  - `odm_report/`: 包含重建后的统计指标。

### 5.3 阶段二：高斯溅射 (Reconstruction Stage)
- **容器环境**: `opensplat:latest`
- **驱动逻辑**: SDK 通过适配器检测到 `opensfm/reconstruction.json` 已存在。
- **挂载**:
  - 宿主机本次运行目录 (Run Dir) -> 容器 `/project`
  - 宿主机图片目录 -> 容器 `/images`
- **数据流**:
  - **输入**: 读取 `/project/opensfm/reconstruction.json` 获取位姿，读取 `/images` (或校正后的 `/project/opensfm/undistorted/`) 获取像素信息。
  - **输出**: 训练完成后，将训练好的模型写入 `/project/3d_gsl/splat.ply`。

### 5.4 阶段三：清理与归档 (Finalization)
- **日志聚合**: 收集分布式各容器的 stdout/stderr 到 `logs/`。
- **配置备份**: 将执行时使用的 `config.yaml` 复制到运行目录，确保实验的可追溯性。
