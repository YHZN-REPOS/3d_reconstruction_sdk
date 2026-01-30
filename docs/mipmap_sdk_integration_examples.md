# MipMap Engine SDK 集成指南 (CLI & JSON)

本文档说明如何通过命令行调用 MipMap Engine 执行全自动三维重建任务。

**官方文档：** [https://docs.mipmap3d.com/engine/zh-Hans/](https://docs.mipmap3d.com/engine/zh-Hans/)

---

## 1. 快速开始

官方提供了一个**交互式 JSON 配置生成器**，可拖入图像自动生成配置文件：
👉 [点击打开交互式页面](https://mipmap3d.com/tasks_generator/#/)

生成 JSON 文件后，通过以下命令启动重建：

```bash
reconstruct_full_engine --reconstruct_type 0 --task_json config_task.json
```

> **Linux Docker 部署**：`reconstruct_full_engine` 可执行程序存放在容器的 `mipmap_engine` 目录下。

---

## 2. 命令行参数说明

| 参数 | 说明 |
| :--- | :--- |
| `--reconstruct_type <N>` | 接口类型。**0 = 全流程重建（推荐）** |
| `--task_json <Path>` | JSON 配置文件的绝对路径 |

---

## 3. JSON 配置文件详解

### 3.1 必需参数

| 参数名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `working_dir` | String | **工程输出目录**。所有中间文件和最终成果保存位置。 |
| `gdal_folder` | String | **SDK 数据目录**。指向 SDK 安装包内的 `data` 或 `gdal_data` 目录（必须为英文路径）。 |
| `image_meta_data` | Array | 输入图像列表。每个元素包含 `id` (唯一索引) 和 `path` (绝对路径)。 |
| `input_image_type` | Int | 影像类型：`1` = 航拍/多镜头, `2` = 环视/全景, `3` = 其他 |
| `resolution_level` | Int | 重建质量：`1` = 高, `2` = 中, `3` = 低 |
| `coordinate_system` | Object | 输出坐标系定义（见下文） |

### 3.2 成果输出控制

**必须至少设置其中一个成果为 `true`：**

| 参数名 | 对应格式 | 说明 |
| :--- | :--- | :--- |
| `generate_osgb` | OSGB | 实景三维 (Smart3D 兼容)，支持 LOD |
| `generate_3d_tiles` | 3D Tiles | WebGL 加载 (CesiumJS, Unreal) |
| `generate_obj` | OBJ | 通用三维模型 |
| `generate_ply` | PLY | 通用模型/点云 |
| `generate_las` | LAS | 标准点云 |
| `generate_pc_ply` | PLY | 纯点云 (无网格) |
| `generate_pc_osgb` | OSGB | 点云分块 |
| `generate_pc_pnts` | PNTS | 点云 3D Tiles |
| `generate_gs_ply` | PLY | **高斯泼溅** (需高斯插件*) |
| `generate_gs_sog` | SOG | 高斯泼溅专用格式 |
| `generate_geotiff` | GeoTIFF | 正射影像 (DOM) + 数字表面模型 (DSM) |
| `generate_tile_2D` | PNG/JPG | 二维瓦片 |

> **[重要] Windows 生成高斯泼溅**：需下载 [高斯插件](https://asset.mipmap3d.com/plugins/gs_dlls_v2.7.1.0.zip)，解压后将所有 `.dll` 文件放入 `reconstruct_full_engine` 同级目录。

### 3.3 坐标系 (`coordinate_system`)

```json
"coordinate_system": {
  "type": 2,          // 2 = 投影坐标系
  "label": "WGS 84",  // 描述性标签
  "epsg_code": 4326   // EPSG 代码
}
```

常用 EPSG：
- `4326` - WGS 84 (全球通用)
- `3857` - Web 墨卡托
- `4547` - CGCS2000 / 3-degree Gauss-Kruger CM 117E (中国)

---

## 4. 完整配置示例

### 最简配置

```json
{
  "working_dir": "C:/Projects/QuickStart",
  "gdal_folder": "C:/MipMap/SDK/data",
  "input_image_type": 1,
  "resolution_level": 2,
  "coordinate_system": {
    "type": 2,
    "label": "WGS 84",
    "epsg_code": 4326
  },
  "image_meta_data": [
    {"id": 1, "path": "C:/Images/DJI_0001.JPG"},
    {"id": 2, "path": "C:/Images/DJI_0002.JPG"},
    {"id": 3, "path": "C:/Images/DJI_0003.JPG"}
  ],
  "generate_osgb": true,
  "generate_3d_tiles": true,
  "generate_geotiff": true
}
```

### 多相机组配置

```json
{
  "working_dir": "D:/Projects/MultiCamera",
  "gdal_folder": "D:/MipMap/SDK/data",
  "input_image_type": 1,
  "resolution_level": 1,
  "coordinate_system": {
    "type": 2,
    "label": "WGS 84",
    "epsg_code": 4326
  },
  "image_meta_data": [
    {"id": 1, "path": "nadir/IMG_001.jpg", "group": "nadir"},
    {"id": 2, "path": "nadir/IMG_002.jpg", "group": "nadir"},
    {"id": 3, "path": "forward/IMG_001.jpg", "group": "oblique_f"},
    {"id": 4, "path": "forward/IMG_002.jpg", "group": "oblique_f"}
  ],
  "generate_osgb": true,
  "generate_3d_tiles": true
}
```

---

## 5. 延伸阅读

- [ReconstructFull 接口详解](https://docs.mipmap3d.com/engine/zh-Hans/api-reference/reconstruct-full)
- [高级参数配置](https://docs.mipmap3d.com/engine/zh-Hans/api-reference/advanced-config)
- [实时重建 API](https://docs.mipmap3d.com/engine/zh-Hans/api-reference/realtime)
- [激光雷达重建 API](https://docs.mipmap3d.com/engine/zh-Hans/api-reference/lidar)
