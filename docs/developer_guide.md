# 3D Reconstruction SDK - 算法工程师开发指南

本文档面向需要**扩展或替换算法**的开发者，介绍 SDK 的架构设计和开发规范。

---

## 目录

1. [架构设计说明书 (推荐阅读)](architecture_design.md)
2. [开发者扩展指南](#开发者扩展指南)
3. [添加新算法](#添加新算法)
4. [配置参数透传](#配置参数透传)
5. [Docker 集成](#docker-集成)
6. [日志与调试](#日志与调试)
7. [打包发布](#打包发布)

---

## 开发者扩展指南

```
my_sdk/
├── core/
│   ├── config.py      # 配置模型 (Pydantic)
│   ├── interfaces.py  # 抽象接口定义
│   └── pipeline.py    # 流水线编排 + 工厂模式
├── adapters/
│   ├── opensfm.py     # OpenSfM/ODM 适配器
│   └── opensplat.py   # OpenSplat 适配器
├── utils/
│   └── docker_runner.py  # Docker 执行工具
└── main.py            # CLI 入口
```

### 核心设计模式

| 模式 | 用途 |
|------|------|
| **策略模式** | `SfMStrategy`, `ReconstructionStrategy` 抽象接口 |
| **工厂模式** | `PipelineFactory` 根据配置创建适配器实例 |
| **上下文模式** | `ReconstructionContext` 在步骤间传递状态 |

---

## 添加新算法

### 步骤 1: 实现适配器

```python
# my_sdk/adapters/colmap.py
from my_sdk.core.interfaces import SfMStrategy, ReconstructionContext
from my_sdk.utils.docker_runner import DockerRunner

class ColmapAdapter(SfMStrategy):
    """COLMAP SfM 适配器"""
    
    def run(self, context: ReconstructionContext) -> bool:
        runner = DockerRunner(log_dir=context.result_path / "logs")
        
        # 1. 准备输入数据
        # ...
        
        # 2. 构建 Docker 命令
        command = [
            "docker", "run", "--rm",
            "-v", f"{context.config.working_dir}:/data",
            "colmap:latest",
            "colmap", "automatic_reconstructor",
            "--workspace_path", "/data/sparse",
            "--image_path", "/data/images"
        ]
        
        # 3. 执行
        return runner.run(command, step_name="COLMAP")
```

### 步骤 2: 注册到工厂

```python
# my_sdk/core/pipeline.py

from my_sdk.adapters.colmap import ColmapAdapter

class PipelineFactory:
    _sfm_registry: Dict[str, Type[SfMStrategy]] = {
        "opensfm": OpenSfMAdapter,
        "colmap": ColmapAdapter,  # ← 添加这一行
    }
```

### 步骤 3: 添加默认 Docker 镜像

```python
# my_sdk/core/config.py

class AlgorithmConfig(BaseModel):
    sfm: str = "opensfm"
    sfm_docker_image: str = "opendronemap/odm:latest"
    
    # 添加 COLMAP 镜像映射 (可选)
    @property
    def sfm_image(self) -> str:
        defaults = {
            "opensfm": "opendronemap/odm:latest",
            "colmap": "colmap/colmap:latest",
        }
        return defaults.get(self.sfm, self.sfm_docker_image)
```

---

## 配置参数透传

SDK 支持两层参数：

### 高层参数 (面向用户)

```json
{
    "quality_preset": "high",
    "use_gps": true,
    "camera": {"model": "perspective"}
}
```

### 底层参数 (面向算法)

```json
{
    "params": {
        "opensfm": {
            "feature_type": "HAHOG",
            "matching_gps_neighbors": 12
        },
        "colmap": {
            "quality": "extreme",
            "single_camera": true
        }
    }
}
```

### 在适配器中读取参数

```python
def run(self, context: ReconstructionContext) -> bool:
    config = context.config
    
    # 高层参数
    quality = config.quality_preset
    
    # 底层参数覆盖
    overrides = config.params.get("colmap", {})
    
    # 合并
    final_params = {"quality": quality, **overrides}
```

---

## Docker 集成

### DockerRunner 使用

```python
from my_sdk.utils.docker_runner import DockerRunner

runner = DockerRunner(
    log_dir=Path("/tmp/logs"),           # 日志保存目录
    progress_callback=my_callback        # 进度回调
)

success = runner.run(
    command=["docker", "run", ...],
    step_name="MyAlgorithm",
    timeout=3600                         # 超时秒数
)
```

### 日志输出

日志自动保存到 `{log_dir}/{step_name}_{timestamp}.log`

```
# Log saved at 2026-01-26T12:00:00
# Exit code: 0
# ==================================================

[INFO] Starting reconstruction...
[INFO] Processing image 1/100 (1%)
...
```

---

## 日志与调试

### 全局日志配置

```python
from my_sdk.utils import setup_logging
import logging

# 开发模式：详细日志
setup_logging(level=logging.DEBUG)

# 生产模式：只记录到文件
setup_logging(
    level=logging.INFO,
    log_file=Path("sdk.log")
)
```

---

## 打包发布

### 项目结构

```
3d_reconstruction/
├── my_sdk/              # 源码
├── docs/                # 文档
├── tests/               # 测试
├── pyproject.toml       # 项目配置
├── setup.py             # 安装脚本
└── README.md
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "recon3d-sdk"
version = "0.1.0"
description = "3D Reconstruction SDK"
requires-python = ">=3.9"
dependencies = [
    "pydantic>=2.0",
]

[project.scripts]
recon3d = "my_sdk.main:main"

[tool.setuptools.packages.find]
include = ["my_sdk*"]
```

### 构建命令

```bash
# 开发模式安装
pip install -e .

# 构建发布包
pip install build
python -m build

# 输出在 dist/ 目录
# - recon3d_sdk-0.1.0-py3-none-any.whl
# - recon3d_sdk-0.1.0.tar.gz
```

### Docker 镜像打包 (可选)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install .

ENTRYPOINT ["recon3d"]
```

```bash
docker build -t recon3d-sdk:latest .
docker run -v /data:/data recon3d-sdk --config /data/config.yaml
```

