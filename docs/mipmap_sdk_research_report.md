# MipMap Engine SDK Research Report

**Date:** 2026-01-23
**Subject:** Capabilities and Technical Overview of MipMap Engine SDK
**Source:** [MipMap 3D Documentation](https://docs.mipmap3d.com/engine/zh-Hans/)

---

## 1. Executive Summary
The MipMap Engine SDK is a professional-grade, cross-platform 3D reconstruction engine designed for developers. It enables the automated conversion of aerial imagery and LiDAR data into high-precision 3D models and geospatial products. Operating as a Command Line Interface (CLI) tool, it allows for seamless integration into backend systems across various programming languages.

## 2. Core Capabilities

### 2.1 Photogrammetry Pipeline
The SDK provides a complete end-to-end pipeline for image-based reconstruction:
- **Aerial Triangulation (AT)**: Automatically solves camera poses and sparse point clouds. Supports GPS/POS data and Ground Control Points (GCPs) for high georeferencing accuracy (`OptimizeAT`).
- **Dense Matching**: Generates high-density point clouds from stereo image pairs.
- **Mesh Reconstruction**: Builds detailed triangular meshes from point clouds.
- **Texture Mapping**: Applies high-resolution textures to meshes for photorealistic visualization.

### 2.2 Advanced Reconstruction Features
- **LiDAR Support**: Native capability to process laser scanning point clouds into surfaces.
- **Gaussian Splatting**: Support for the latest Neural Rendering techniques to generate 3D Gaussian Splatting models for next-gen real-time rendering.
- **Large-Scale Processing**:
    - **DivideTiles**: Automatically segments large datasets into manageable tiles for parallel processing.
    - **LOD Generation**: Creates Level of Detail hierarchies for efficient streaming and rendering of massive scenes.
- **Real-Time Reconstruction**: Stream-based processing for immediate visualization (e.g., emergency response).

## 3. Technical Specifications

### 3.1 Supported Input Data
| Data Type | Description |
| :--- | :--- |
| **Imagery** | JPEG/TIFF from multi-lens slants, orthographic cameras, or consumer drones. Reads EXIF/XMP for sensor data. |
| **LiDAR** | Standard point cloud formats for geometry input. |
| **Control** | Ground Control Points (GCPs) for geodetic correction. |

### 3.2 Output Formats
The SDK covers the full spectrum of industry-standard formats:

| Category | Formats | Use Case |
| :--- | :--- | :--- |
| **3D Mesh** | `.obj`, `.ply` | General 3D editing (Blender, Maya, MeshLab) |
| **GIS / Survey** | `.osgb` (Smart3D) | Professional GIS software, supporting LOD and paging |
| **Web / VR** | `3D Tiles`, `.pnts` | WebGL streaming (CesiumJS, Unreal Engine) |
| **Point Cloud** | `.las`, `.ply`, `.osgb` | Analysis, classification |
| **2D Map Products** | `GeoTIFF` (DOM/DSM) | Orthophotos and Digital Surface Models for mapping |
| **Neural/NeRF** | `.ply`, `.sog` | Gaussian Splatting viewers |

### 3.3 System Integration
- **Interface**: Command Line Interface (CLI).
- **Execution**: Can be invoked via `subprocess` (Python), `exec` (Node.js), `system` (C++), etc.
- **OS Support**: Windows x64, Linux.
- **Automation**: Features a `reconstruct_full_engine` executable that supports full pipeline automation via the `--reconstruct_type 0` argument.

## 4. Integration Workflow Example
A typical integration pattern for a backend service:

1.  **Ingest**: User uploads images to server storage.
2.  **Trigger**: Backend service constructs a CLI command:
    ```bash
    # Example pseudo-command
    reconstruct_full_engine --reconstruct_type 0 --task_json /data/mission_01/config.json
    ```
3.  **Process**: SDK runs in the background (optionally reporting progress via stdout/logs).
4.  **Deliver**: Generated `.osgb` or `3D Tiles` are served to the frontend.

## 5. Conclusion
MipMap Engine SDK effectively abstracts the complex mathematics of photogrammetry into a set of engineering tools using `Structure from Motion (SfM)` and Multi-View Stereo (MVS)`and other technologies. It is suitable for building custom cloud photogrammetry platforms, automated mapping pipelines, or embedding reconstruction capabilities into local desktop software.
