# MipMap Engine SDK 集成指南 (CLI & JSON)

本文档说明如何通过命令行直接调用 MipMap Engine 执行全自动三维重建任务。

所有的高级参数配置（如输入输出路径、质量控制、坐标系等）均通过一个 JSON 配置文件来传递。

---

## 1. 命令行调用方式

核心可执行文件为 `reconstruct_full_engine` (Windows 下为 `.exe`)。

### 基本命令格式
```bash
reconstruct_full_engine --reconstruct_type 0 --task_json "C:/path/to/your_task_config.json"
```

### 参数说明
*   **`--reconstruct_type 0`**  
    必选参数。指定任务类型为**全自动重建 (ReconstructFull)**。其他数值对应单步操作（如仅空三或仅网格化），但在全流程集成中通常只用 0。

*   **`--task_json <Path>`**  
    必选参数。指定任务配置文件的绝对路径。所有具体的任务信息都在此文件中定义。

---

## 2. JSON 配置文件详解

`task_json` 是控制引擎行为的核心。以下是标准的 JSON 结构说明及参数详解。

### 完整配置示例

```json
{
  "working_dir": "D:/Projects/Mission_01_Result",
  "gdal_folder": "C:/MipMap_SDK/data",
  "input_image_type": 1,
  "resolution_level": 1,
  "fast_mode": false,
  
  "coordinate_system": {
    "type": 2,
    "label": "WGS 84",
    "epsg_code": 4326
  },
  
  "image_meta_data": [
    { "id": 1, "path": "D:/Source_Images/DSC001.JPG" },
    { "id": 2, "path": "D:/Source_Images/DSC002.JPG" },
    { "id": 3, "path": "D:/Source_Images/DSC003.JPG" }
  ],
  
  "generate_osgb": true,
  "generate_3d_tiles": true,
  "generate_obj": false,
  "generate_ply": false,
  "generate_las": false,
  "generate_dom": true,
  "generate_dsm": true
}
```

### 参数详细定义

#### 基础路径参数
| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| **`working_dir`** | String | **是** | **工程根目录**。所有的中间文件和最终的重建成果都会保存在这个文件夹下。 |
| **`gdal_folder`** | String | **是** | **SDK 数据目录**。指向 SDK 安装包内的 `data` 目录（包含坐标系定义等必要资源）。 |

#### 输入数据参数
| 参数名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| **`image_meta_data`** | Array | **是** | 输入图像列表。每个元素包含 `id` (int, 唯一索引) 和 `path` (string, 绝对路径)。 |
| **`input_image_type`** | Int | 否 | 输入影像类型。`1`: 普通航拍/多镜头; `0`: 环视/全景。默认为 1。 |
| **`coordinate_system`**| Object | 否 | 输出坐标系定义（见下文）。如果不填，默认使用图像自带坐标系（通常为 WGS84）。 |

#### 质量与性能以数
| 参数名 | 类型 | 默认 | 说明 |
| :--- | :--- | :--- | :--- |
| **`resolution_level`**| Int | 1 | 重建质量/分辨率等级。<br>`1`: 高 (原始分辨率)<br>`2`: 中 (降采样)<br>`3`: 低 |
| **`fast_mode`** | Bool | false | 是否开启快速模式。`true` 会显著加快速度，但可能降低细节精度。 |
| **`num_features`** | Int | 20000 | (可选) 每张图像提取的特征点数量上限。 |

#### 成果输出控制 (Output Formats)
以下参数均为 Boolean 类型，设置为 `true` 即生成对应格式：

| 参数名 | 对应格式 | 典型用途 |
| :--- | :--- | :--- |
| **`generate_osgb`** | OSGB | 行业标准实景三维格式 (Smart3D兼容)，支持 LOD。 |
| **`generate_3d_tiles`**| 3D Tiles | WebGL 前端加载 (CesiumJS, Unreal Engine)。 |
| **`generate_obj`** | OBJ | 通用模型格式，适用于 Blender/Max 编辑。 |
| **`generate_ply`** | PLY | 通用模型/点云格式。 |
| **`generate_las`** | LAS | 标准点云格式。 |
| **`generate_dom`** | GeoTIFF | 数字正射影像 (2D 地图)。 |
| **`generate_dsm`** | GeoTIFF | 数字表面模型 (高程数据)。 |

---

### 坐标系对象 (`coordinate_system`) 详解
通常只需指定 EPSG 代码即可。

```json
"coordinate_system": {
  "type": 2,          // 2 表示投影坐标系
  "label": "WGS 84",  // 描述性标签
  "epsg_code": 4326   // EPSG 代码 (例如 4326 为 WGS84, 3857 为伪墨卡托)
}
```
