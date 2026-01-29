# 3D Reconstruction SDK - 用户使用手册

本 SDK 提供从多张照片生成 3D 重建结果的能力，支持空三重建、高斯溅射等多种输出。

---

## 目录

1. [快速开始](#快速开始)
2. [安装要求](#安装要求)
3. [配置说明](#配置说明)
4. [运行方式](#运行方式)
5. [输出结果](#输出结果)
6. [常见问题](#常见问题)

---

## 快速开始

### 1. 准备项目目录

创建工作目录，并将照片放入 `images/` 子目录：

```
/data/my_project/
└── images/
    ├── photo_001.jpg
    ├── photo_002.jpg
    └── ...
```

> 支持格式：JPG, JPEG, PNG, TIF, TIFF

### 2. 创建配置文件

将 `config.yaml` 放在项目目录下（与 `images/` 同级）：

```yaml
# config.yaml - working_dir 会自动从此文件位置推断
run_sparse: true
run_gaussian: true
```

### 3. 运行

```bash
python -m my_sdk.main --config config.yaml
```

### 4. 查看结果

输出位于带时间戳的 `runs/` 目录：

```
/home/user/my_project/
├── config.yaml
├── images/                      # 输入图片
└── runs/
    └── 20260127_143500/         # 每次运行自动创建
        ├── config.yaml          # 配置备份
        ├── opensfm/             # OpenSfM/ODM 运行目录
        │   └── reconstruction.json
        ├── 3d_gsl/              # 高斯溅射输出
        │   └── splat.ply        # 生成的模型
        └── logs/                # 实时执行日志

```

---

## 安装要求

| 依赖项 | 版本要求 |
|--------|----------|
| Python | >= 3.9 |
| Docker | >= 20.0 |
| GPU (可选) | NVIDIA GPU + nvidia-docker (高斯溅射需要) |

### 安装步骤

```bash
# 1. 安装 SDK
pip install -e .

# 2. 拉取 Docker 镜像
docker pull opendronemap/odm:latest
docker pull opensplat:latest
```

---

## 配置说明

SDK 的配置分为 **基础配置** (面向普通用户) 和 **进阶配置** (面向算法工程师) 两部分。

### 1. 基础配置 (Ordinary Users)

这些参数控制任务的大方向，普通用户建议仅修改这些选项。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `run_sparse` | bool | `true` | 是否运行稀疏重建 (SfM)。是后续步骤的必要基础。 |
| `run_gaussian` | bool | `true` | 是否运行高斯溅射模型生成。 |
| `run_mesh` | bool | `false` | 是否生成 3D 网格模型 (由 ODM 驱动)。 |
| `quality_preset` | string | `medium` | **重建质量预设**: `high`, `medium`, `low`。影响特征点密度和迭代次数。 |
| `use_gps` | bool | `true` | 是否利用照片 GPS。开启可显著加速空三匹配并实现地理对齐。 |
| `camera.model` | string | `perspective` | 相机模型。常用: `perspective` (透视), `fisheye` (鱼眼)。 |

---

### 2. 进阶配置 (Algorithm Engineers)

面向算法工程师，用于精细控制后端镜像版本、特征算法及深度透传参数。

#### 算法后端与系统
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `algorithms.sfm` | `opensfm` | 稀疏重建后端算法。 |
| `algorithms.sfm_docker_image` | `opendronemap/odm:latest` | 使用的 Docker 镜像版本。 |
| `feature_type` | `sift` | 关键点算法: `sift`, `akaze`, `hahog`。 |
| `thread_num` | `8` | 宿主机并行处理的线程数。 |

#### 深度参数透传 (`params`)
此部分允许算法工程师直接向底层 Docker 容器中的算法发送原始命令参数。其优先级最高，会覆盖 `quality_preset` 的默认映射。

```yaml
params:
  opensfm:
    feature_process_size: 2048   # 强制指定特征处理分辨率
  opensplat:
    iterations: 20000            # 指定高斯溅射训练迭代次数
```

---

## 运行方式

### 方式一：命令行

```bash
python -m my_sdk.main --config config.yaml
```

### 方式二：Python 代码

```python
from my_sdk.core.config import TaskConfig
from my_sdk.core.pipeline import ReconstructionPipeline

# 从配置文件加载 (working_dir 自动推断)
config = TaskConfig.from_file("/data/my_project/config.yaml")

# 或手动指定 working_dir
# config = TaskConfig(working_dir="/data/my_project", quality_preset="high")

# 运行
pipeline = ReconstructionPipeline(config)
success = pipeline.run()
```

### 方式三：分阶段执行

```python
pipeline = ReconstructionPipeline(config)

# 只运行 SfM
pipeline.run(stages=["sfm"])

# 检查结果后，再运行高斯溅射
pipeline.run(stages=["reconstruction"])
```

### 方式四：断点续跑 (Resume)

如果任务中断，可以通过设置环境变量 `RESUME_ID` 来恢复：

```bash
# 获取之前运行的目录名，例如 20260127_143500
export RESUME_ID=20260127_143500
python -m my_sdk.main --config config.yaml
```

SDK 会自动跳过已完成的步骤（如 SfM），直接从失败或未运行的项目继续。

### 方式四：Docker 容器化运行

项目提供 Dockerfile 和 docker-compose.yml，可将 SDK 容器化部署。

#### 使用 docker compose（推荐）

**构建镜像**

```bash
cd 3d_reconstruction_sdk
docker compose build
```

**运行**

```bash
# 设置环境变量
export DATA_DIR=/home/user/my_project
export CONFIG_FILE=/data/config.yaml

# 运行
docker compose run --rm sdk
```

或使用 `.env` 文件：

```bash
# .env 文件内容
DATA_DIR=/home/user/my_project
CONFIG_FILE=/data/config.yaml
```

```bash
docker compose run --rm sdk
```

**开发模式（代码修改后无需重新打包）**

```bash
docker compose --profile dev run --rm sdk-dev
```

#### 使用 docker run

```bash
# 构建镜像
docker build -t recon3d-sdk:latest .

# 或显式指定平台 (适用于 Apple Silicon Mac)
docker build --platform linux/amd64 -t recon3d-sdk:latest .

# 运行
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /home/user/my_project:/data \
  recon3d-sdk:latest \
  --config /data/config.yaml
```

> **重要**：必须挂载 Docker socket (`/var/run/docker.sock`)，因为 SDK 需要调用宿主机的 Docker 来运行算法容器。

#### 路径配置说明

SDK 使用以下逻辑确定 `working_dir`：

1. **优先使用环境变量 `DATA_DIR`**（推荐）
2. 如果未设置，且配置文件中指定了 `working_dir`，则使用配置文件中的值
3. 如果都未设置，则自动推断为 `config.yaml` 所在目录

**推荐做法**：使用 Docker Compose 并设置 `DATA_DIR` 环境变量。

```bash
# 假设项目结构：
# /home/user/my_project/
# ├── images/
# └── (config.yaml 可在任意位置)

# 运行
DATA_DIR=/home/user/my_project CONFIG_FILE=/path/to/any/config.yaml docker compose run --rm sdk
```

SDK 容器内部：
- `DATA_DIR` 始终映射为 `/project`
- `CONFIG_FILE` 始终映射为 `/tmp/config.yaml`
- 自动同步宿主机时区 (`/etc/localtime`)
- 日志实时输出到控制台及 `runs/<timestamp>/logs/` 目录

---

## 工作流详细说明

SDK 的执行过程分为以下几个阶段：

### 1. 初始化阶段 (Initialization)
- **参数解解析**: SDK 读取 `config.yaml` 或 Python 传入的配置。
- **目录准备**: 在 `runs/` 目录下创建以当前时间命名的子目录（如 `20260127_143500/`），作为本次任务的输出空间。
- **环境检查**: 检查宿主机 Docker 运行时及 GPU 可用性。

### 2. 空三重建阶段 (Structure from Motion - OpenSfM)
- **特征提取**: 从输入的原始图像中识别特征点（默认使用 SIFT 算法）。
- **特征匹配**: 在不同图像之间通过特征点进行几何关联。
- **稀疏重建**: 通过几何计算确定相机的内参、位置、姿态，并生成稀疏的点云（Tie Points）。
- **输出**: 生成包含相机位姿和稀疏点云的 `reconstruction.json` 及其相关中间文件。

### 3. 三维网格生成 (Mesh Generation - 可选)
- **密集匹配**: 在稀疏点云基础上计算稠密点云。
- **表面重建**: 使用泊松重建或类似算法将点云转换为连续的三角网格。
- **纹理贴图**: 将原始照片的纹理映射回网格模型。
- **说明**: 需配置 `run_mesh: true`，此阶段由 ODM 控制器完成。

### 4. 高斯溅射训练 (Gaussian Splatting - OpenSplat)
- **数据准备**: 读取 `opensfm` 阶段生成的相机位姿和稀疏点云。
- **模型学习**: 通过亚像素级的优化过程，学习每个高斯的几何属性（位置、缩放、旋转）和辐射属性（颜色、不透明度）。
- **优化迭代**: 根据 `quality_preset` 决定迭代次数，持续提升场景重建质量。
- **输出**: 生成代表场景的 `.ply` 格式高斯溅射模型。

---

## 输出结果

### 目录结构

每次运行会在 `runs/` 下创建带时间戳的目录：

```
{working_dir}/
├── config.yaml
├── images/                      # 输入图片（用户提供）
└── runs/
    └── 20260127_143500/         # 本次运行目录
        ├── config.yaml          # 本次运行所使用的配置备份
        ├── opensfm/             # OpenSfM 结果目录
        ├── 3d_gsl/              # 高斯溅射结果目录
        ├── odm_report/          # 质量报告目录
        └── logs/                # 详细调试日志
```

### 成果文件说明

| 文件/目录路径 | 类型 | 说明 | 主要用途 |
| :--- | :--- | :--- | :--- |
| `opensfm/reconstruction.json` | 核心数据 | 包含所有已恢复相机的位姿、内参以及稀疏点云。 | 外部程序调用位姿数据，或作为后续训练的基础。 |
| `3d_gsl/splat.ply` | 最终成果 | 生成的高斯溅射模型，包含场景的所有几何与色彩信息。 | **三维可视化**，支持在 CloudCompare 或专用渲染器中查看。 |
| `odm_report/report.pdf` | 质量报告 | 由 ODM 自动生成的 PDF，包含空三精度、重叠度热力图等。 | **质量验收**，直观判断重建是否成功。 |
| `logs/main.log` | 系统日志 | 记录了 SDK 调度算法容器的完整过程。 | **故障排查**，定位运行错误的原因。 |
| `opensfm/undistorted/` | 中间目录 | 经过校正、去除畸变后的图像集合。 | 用于高斯溅射训练的标准化输入。 |

### 结果查看

**1. 高斯溅射模型 (`.ply`)**
- 推荐使用 [SuperSplat](https://playcanvas.com/supersplat/) (推荐) 或 [CloudCompare](https://cloudcompare.org/) (4.0 及以上版本)。
- 也可以使用 SDK 配套的轻量级 Web 预览工具。

**2. 精度评估 (`report.pdf`)**
- 打开 `odm_report/report.pdf` 检查 "RMS Error" 和 "Percentage of aligned images"，理想情况下对齐率应接近 100%。

---

## 常见问题

### Q: Docker 找不到 GPU

确保安装了 nvidia-docker：

```bash
# 安装 nvidia-container-toolkit
sudo apt-get install nvidia-container-toolkit
sudo systemctl restart docker

# 测试
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

### Q: 重建质量差

1. 确保照片有足够重叠度（> 70%）
2. 避免运动模糊和过曝
3. 尝试 `quality_preset: "high"`

### Q: 内存不足

减少特征点数量：

```json
{
    "params": {
        "opensfm": {
            "feature_process_size": 1024
        }
    }
}
```

### Q: 高斯溅射失败

检查 SfM 是否成功完成。高斯溅射需要 SfM 的输出作为输入。

---

## 完整配置示例

```yaml
# config.yaml - 放在项目目录下，working_dir 自动推断
thread_num: 8

run_sparse: true
run_gaussian: true

quality_preset: medium
use_gps: true

camera:
  model: perspective

algorithms:
  sfm: opensfm
  sfm_docker_image: opendronemap/odm:latest
  reconstruction_docker_image: opensplat:latest
```


