import json
from pathlib import Path
from my_sdk.core.interfaces import ReconstructionContext

class ReportEngine:
    """
    Engine for translating reconstruction metrics into human-readable Chinese reports.
    Supports extensible metrics from multiple stages.
    """
    
    def __init__(self, context: ReconstructionContext):
        self.context = context
        self.metrics = context.metrics
        self.report_path = context.run_dir / "quality_report_zh.md"
        self.data_path = context.run_dir / "metrics.json"

    def generate(self):
        """Generate the unified Chinese quality report."""
        # 1. Save raw data for programatic use
        try:
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ReportEngine] Warning: Could not save metrics.json: {e}")

        # 2. Build Markdown content
        from datetime import datetime
        md_lines = [
            "# 三维重建质量评估报告",
            f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**任务 ID:** `{self.context.run_dir.name}`",
            "",
            "---",
            ""
        ]
        
        # 3. Add Task Summary (Timings, Photos, etc.)
        md_lines.extend(self._build_summary_section())
        md_lines.append("\n---\n")

        # 4. Add SfM (Sparse) Metrics
        if "sfm" in self.metrics:
            md_lines.extend(self._build_sfm_section(self.metrics["sfm"]))
            
        # 4. Add Mesh Metrics (if enabled)
        if "sfm" in self.metrics and "mesh" in self.metrics["sfm"]:
            md_lines.extend(self._build_mesh_section(self.metrics["sfm"]["mesh"]))
            
        # 5. Add Reconstruction (Dense/Gaussian) Metrics
        if "reconstruction" in self.metrics:
            md_lines.extend(self._build_splat_section(self.metrics["reconstruction"]))

        # 6. Add GS to Point Cloud Metrics
        if "gs_to_pc" in self.metrics:
            md_lines.extend(self._build_gs_to_pc_section(self.metrics["gs_to_pc"]))

        # 7. Add Conclusion/Advice
        md_lines.extend(self._build_conclusion())

        # 6. Save to file
        try:
            with open(self.report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))
            print(f"[ReportEngine] Quality report generated: {self.report_path}")
        except Exception as e:
            print(f"[ReportEngine] Error: Could not write report file: {e}")

    def _build_summary_section(self) -> list:
        def format_duration(seconds: float) -> str:
            if seconds is None: return "N/A"
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            parts = []
            if h > 0: parts.append(f"{h}小时")
            if m > 0: parts.append(f"{m}分")
            parts.append(f"{s}秒")
            return "".join(parts)

        start_str = self.context.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.context.start_time else "N/A"
        end_str = self.context.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.context.end_time else "N/A"
        
        section = [
            "## 任务概览 (Task Summary)",
            f"- **开始时间**: {start_str}",
            f"- **完成时间**: {end_str}",
            f"- **总耗时**: {format_duration(self.context.total_duration)}",
            f"- **输入照片总数**: {self.context.photo_count} 张",
            "",
        ]
        
        # Detailed stage timings
        section.append("### 各阶段耗时详情")
        if "sfm" in self.metrics:
            d = self.metrics["sfm"].get("duration_seconds")
            section.append(f"- **稀疏重建 (SfM)**: {format_duration(d)}")
            
        if "reconstruction" in self.metrics:
            d = self.metrics["reconstruction"].get("duration_seconds")
            section.append(f"- **稠密重建 (GS)**: {format_duration(d)}")

        if "gs_to_pc" in self.metrics:
            d = self.metrics["gs_to_pc"].get("duration_seconds")
            section.append(f"- **高斯转点云 (GS2PC)**: {format_duration(d)}")
            
        return section

    def _build_sfm_section(self, data: dict) -> list:
        status_zh = "成功" if data.get("status") == "Success" else "失败/部分完成"
        
        registered = data.get('registered_images')
        total = data.get('total_images')
        sparse_pts = data.get('sparse_points')
        error = data.get("reprojection_error")
        
        # Calculate rate safely
        if registered is not None and total is not None and total > 0:
            rate = (registered / total) * 100
            rate_str = f"{rate:.1f}%"
            align_str = f"{registered} / {total} ({rate_str})"
        else:
            align_str = "N/A"
        
        # Format sparse points safely
        sparse_str = f"{sparse_pts:,}" if sparse_pts is not None else "N/A"
        
        section = [
            "## 1. 稀疏重建精度 (SfM)",
            f"- **执行状态**: {status_zh}",
            f"- **图像对齐率**: {align_str}",
            f"- **稀疏点云密度**: {sparse_str} 个空间点",
        ]
        
        if error is not None:
            section.append(f"- **重投影误差 (RMSE)**: {error:.4f} 像素")
        else:
            section.append("- **重投影误差 (RMSE)**: 无法提取 (可能步骤未完成)")
            
        # Add Visualizations (Images from ODM)
        visuals = data.get("visualizations", {})
        if visuals:
            section.append("\n### 质量可视化图表")
            
            # Map keys to Chinese titles
            titles = {
                "overlap": "图像重叠度地图 (Overlap Map)",
                "residuals": "相机残差分布图 (Residuals)",
                "gps_error": "GPS 精度分析图 (GPS Errors)",
                "camera_errors": "相机参数误差图 (Camera Errors)"
            }
            
            for key, rel_path in visuals.items():
                title = titles.get(key, key.capitalize())
                section.append(f"#### {title}")
                # Embed as Markdown image (path relative to the .md file which is in run_dir)
                section.append(f"![{title}]({rel_path})")
                section.append("")

        # Warning for low registration
        if registered is not None and total is not None and total > 0:
            rate = (registered / total) * 100
            if rate < 80:
                section.append(f"\n> ⚠️ **建议**: 图像对齐率较低 ({rate:.1f}%)。请检查输入照片的重叠度（建议 70% 以上）或光照条件。")
        
        section.append("")
        return section

    def _build_mesh_section(self, data: dict) -> list:
        vertices = data.get("vertices")
        faces = data.get("faces")
        
        # Check actual file existence for status
        mesh_ply = self.context.run_dir / "odm_meshing" / "odm_mesh.ply"
        orthophoto = self.context.run_dir / "odm_orthophoto" / "odm_orthophoto.tif"
        dense_cloud = self.context.run_dir / "odm_georeferencing" / "odm_georeferenced_model.laz"
        
        if mesh_ply.exists() or orthophoto.exists() or dense_cloud.exists():
            status_zh = "成功"
        elif data.get("status") == "Success":
            status_zh = "成功"
        else:
            status_zh = "进行中/未生成"
        
        section = [
            "## 2. 三维网格/稠密点云/正射投影 (ODM Products)",
            f"- **执行状态**: {status_zh}"
        ]
        
        if vertices is not None:
            section.append(f"- **网格顶点数 (Vertices)**: {vertices:,}")
        if faces is not None:
            section.append(f"- **网格面片数 (Faces)**: {faces:,}")
        
        # Check and report orthophoto
        if orthophoto.exists():
            section.append(f"- **正射投影**: 已生成")
        
        # Check and report dense point cloud
        if dense_cloud.exists():
            section.append(f"- **稠密点云**: 已生成 (LAZ格式)")
            
        section.append("")
        return section

    def _build_splat_section(self, data: dict) -> list:
        loss = data.get("final_loss")
        count = data.get("gaussian_count")
        
        loss_str = f"{loss:.6f}" if (loss is not None) else "N/A"
        count_str = f"{count:,}" if (count is not None) else "N/A"
        
        section = [
            "## 3. 高斯泼溅质量 (Gaussian Splatting)",
            f"- **训练集 Loss**: {loss_str}",
            f"- **高斯体总数**: {count_str} 个点"
        ]
        
        if loss and loss > 0.1:
            section.append(f"\n> ⚠️ **注意**: 训练 Loss 较高 ({loss:.4f})。如果重建结果模糊，请尝试增加训练迭代次数。")
            
        section.append("")
        return section

    def _build_gs_to_pc_section(self, data: dict) -> list:
        count = data.get("point_count")
        
        count_str = f"{count:,}" if (count is not None) else "N/A"
        
        section = [
            "## 3.5 高斯模型转稠密点云 (GS to Point Cloud)",
            f"- **执行状态**: 成功",
            f"- **点云顶点数**: {count_str} 个点"
        ]
        
        section.append("")
        return section

    def _build_conclusion(self) -> list:
        conclusion = ["## 4. 产出物说明"]
        
        # Sparse outputs
        if self.context.config.run_sparse:
            conclusion.append(f"- **稀疏点云 (JSON)**: `opensfm/reconstruction.json`")
            
        # ODM outputs (mesh, orthophoto, dense cloud)
        if self.context.config.run_mesh:
            conclusion.append(f"- **三维网格 (PLY)**: `odm_meshing/odm_mesh.ply`")
            conclusion.append(f"- **正射投影 (GeoTIFF)**: `odm_orthophoto/odm_orthophoto.tif`")
            conclusion.append(f"- **稠密点云 (LAZ)**: `odm_georeferencing/odm_georeferenced_model.laz`")
            conclusion.append(f"- **稠密点云 (PLY)**: `odm_georeferencing/odm_georeferenced_model.ply`")
            
        # GS outputs
        if self.context.config.run_gaussian:
            conclusion.append(f"- **高斯泼溅模型 (PLY)**: `3d_gsl/splat.ply`")

        # GS to PC outputs
        if self.context.config.run_gs_to_pc:
            conclusion.append(f"- **稠密点云 (PLY, via GS)**: `3d_gsl/dense_pc.ply`")
            
        conclusion.extend([
            f"- **完整统计数据**: `metrics.json` (JSON 格式)",
            "",
            "---",
            "*本报告由 3D Reconstruction SDK 自动生成*"
        ])
        return conclusion
