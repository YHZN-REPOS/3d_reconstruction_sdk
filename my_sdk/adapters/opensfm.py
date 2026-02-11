import subprocess
from pathlib import Path
from my_sdk.core.interfaces import SfMStrategy, ReconstructionContext
from my_sdk.utils.docker_runner import DockerRunner
from my_sdk.utils.opensfm_exporter import convert_opensfm_to_nerf

class OpenSfMAdapter(SfMStrategy):
    """
    Adapter for OpenSfM via OpenDroneMap (ODM).
    Uses ODM's Docker image which includes OpenSfM.
    
    ODM Project Structure:
    {project_root}/
    ├── images/          # Input images
    ├── opensfm/         # OpenSfM working directory (auto-created)
    │   ├── config.yaml
    │   ├── reconstruction.json
    │   └── undistorted/ # Undistorted images for downstream
    └── odm_report/      # Processing reports
    """
    
    def run(self, context: ReconstructionContext) -> bool:
        # 1. Prepare ODM Project Structure
        # ODM expects images in {project}/images/
        # Use run_dir for outputs, symlink images from working_dir
        odm_project = context.run_dir
        
        # Check if already done (Resume capability)
        reconstruction_json = odm_project / "opensfm" / "reconstruction.json"
        
        # Initialize Docker runner with logging
        runner = DockerRunner()
        
        # If resuming and output exists, skip SfM
        if reconstruction_json.exists():
             print(f"[ODM/OpenSfM] Found existing reconstruction at {reconstruction_json}.")
             
             # --- Auto-generate missing transforms.json on resume ---
             transforms_json = context.run_dir / "transforms.json"
             if not transforms_json.exists():
                 print(f"[ODM/OpenSfM] transforms.json is missing, regenerating from existing results...")
                 try:
                     convert_opensfm_to_nerf(reconstruction_json, transforms_json, images_relative_path="../../images")
                 except Exception as e:
                     print(f"[ODM/OpenSfM] Warning: Failed to regenerate transforms.json on resume: {e}")
             
             print(f"[ODM/OpenSfM] Skipping SfM step.")
             return True

        images_src = Path(context.config.input_images_dir)
        images_dest = odm_project / "images"
        
        # Create symlink to images directory (avoiding copy)
        if not images_dest.exists():
            images_dest.symlink_to(images_src)
            print(f"[ODM/OpenSfM] Linked images: {images_src} -> {images_dest}")
        
        
        print(f"[ODM/OpenSfM] Using ODM project at {odm_project}")
        print(f"[ODM/OpenSfM] Images directory: {images_src}")
        
        # 2. Build OpenSfM Config
        camera_cfg = context.config.camera
        sfm_config = {
            "feature_type": context.config.feature_type.upper(),  # ODM uses uppercase: SIFT, HAHOG
            "matcher_type": "FLANN",
            "matching_gps_neighbors": 8 if context.config.use_gps else 0,
            "camera_projection_type": camera_cfg.model,  # perspective, brown, fisheye, etc.
        }
        
        # Camera intrinsics (ODM/OpenSfM style)
        if camera_cfg.focal_length_mm is not None:
            # OpenSfM uses focal ratio (focal_length / max(width, height))
            # If sensor size known, we can compute. Otherwise pass as prior.
            sfm_config["flann_algorithm"] = "KDTREE"  # Better for known cameras
        
        # Distortion parameters
        if camera_cfg.distortion_k1 is not None:
            sfm_config["radial_distortion_k1"] = camera_cfg.distortion_k1
        if camera_cfg.distortion_k2 is not None:
            sfm_config["radial_distortion_k2"] = camera_cfg.distortion_k2
        if camera_cfg.distortion_p1 is not None:
            sfm_config["tangential_distortion_p1"] = camera_cfg.distortion_p1
        if camera_cfg.distortion_p2 is not None:
            sfm_config["tangential_distortion_p2"] = camera_cfg.distortion_p2
        
        # Quality presets
        quality_map = {
            "high": {"feature_process_size": 2048, "feature_min_frames": 8000},
            "medium": {"feature_process_size": 1600, "feature_min_frames": 4000},
            "low": {"feature_process_size": 1024, "feature_min_frames": 2000},
        }
        sfm_config.update(quality_map.get(context.config.quality_preset, quality_map["medium"]))
        
        # User overrides (highest priority)
        user_overrides = context.config.params.get("opensfm", {})
        sfm_config.update(user_overrides)
        
        # Write config to OpenSfM directory
        opensfm_dir = odm_project / "opensfm"
        opensfm_dir.mkdir(exist_ok=True)
        self._write_opensfm_config(opensfm_dir, sfm_config)
        
        # 3. Construct Docker Command for ODM
        docker_image = context.config.algorithms.sfm_docker_image  # e.g., "opendronemap/odm:latest"
        
        # Check GPU availability
        use_gpu = DockerRunner.check_gpu_support()
        
        is_gpu_image = ":gpu" in docker_image
        if not use_gpu:
            if is_gpu_image:
                 print("\n" + "!" * 60)
                 print("[ODM/OpenSfM] ERROR: You are using a GPU image, but Docker GPU support is NOT detected.")
                 print("[ODM/OpenSfM] This will cause library errors (libcuda.so.1 not found) if we continue.")
                 print("[ODM/OpenSfM] ACTION REQUIRED: Please install nvidia-container-toolkit on your host.")
                 print("[ODM/OpenSfM] COMMAND TO TEST: docker run --rm --gpus all alpine nvidia-smi")
                 print("!" * 60 + "\n")
                 return False # Fail early to avoid strange errors inside container
            else:
                 print("[ODM/OpenSfM] INFO: GPU not detected. Using CPU mode with standard image.")
        
        # DooD Path Construction:
        # We need to reconstruct the HOST path equivalent to context.run_dir
        # context.run_dir is inside container (e.g., /project/runs/timestamp)
        # HOST_DATA_DIR is passed via env (e.g., /home/user/data)
        
        import os
        host_data_dir = os.environ.get("HOST_DATA_DIR")
        if not host_data_dir:
             raise ValueError("HOST_DATA_DIR environment variable is missing. Required for DooD.")
             
        # Reconstruct host paths relative to working_dir
        rel_run_path = context.run_dir.relative_to(context.config.working_dir)
        rel_images_path = images_src.relative_to(context.config.working_dir)
        
        host_run_dir = Path(host_data_dir) / rel_run_path
        host_images_dir = Path(host_data_dir) / rel_images_path

        # ODM container paths:
        # - Mount host_run_dir to /datasets/project (for outputs)
        # - Mount host_images_dir to /datasets/project/images (for input images)
        
        command = [
            "docker", "run", "--rm",
            "-v", "/etc/localtime:/etc/localtime:ro",
            "-v", f"{host_run_dir}:/datasets/project",
            "-v", f"{host_images_dir}:/datasets/project/images:ro",
            "-e", "NVIDIA_VISIBLE_DEVICES=all",
            "-e", "NVIDIA_DRIVER_CAPABILITIES=all",
            docker_image,
            "--project-path", "/datasets",
            "--ignore-gsd",             # Don't auto-resize based on GSD
            "project"
        ]

        if use_gpu:
            command.insert(2, "--gpus")
            command.insert(3, "all")
        
        # Control mesh generation
        if context.config.run_mesh:
            # Run full pipeline including mesh
            pass  # ODM generates mesh by default
        else:
            # Skip mesh, only do SfM
            command.insert(-1, "--end-with")
            command.insert(-1, "opensfm")
        
        # Add feature type if not default
        if context.config.feature_type.upper() != "SIFT":
            command.extend(["--feature-type", context.config.feature_type.upper()])
        
        # 4. Execute using DockerRunner
        success = runner.run(command, step_name="ODM/OpenSfM")
        
        # 5. Extract Metrics if successful
        if success:
            print("[ODM/OpenSfM] Reconstruction finished.")
            
            # --- Default Extra Export: NeRF format (transforms.json) ---
            # This is used by 3DGS-to-PC and other downstream tools
            try:
                reconstruction_json = context.run_dir / "opensfm" / "reconstruction.json"
                transforms_json = context.run_dir / "transforms.json"
                
                print(f"[ODM/OpenSfM] Exporting NeRF transforms.json to {transforms_json}...")
                convert_opensfm_to_nerf(reconstruction_json, transforms_json, images_relative_path="../../images")
            except Exception as e:
                print(f"[ODM/OpenSfM] Warning: Failed to export NeRF transforms: {e}")
            
            self._extract_metrics(context)
        
        return success
    
    def _extract_metrics(self, context: ReconstructionContext):
        """Extract and store SfM metrics from ODM output files."""
        import json
        import re
        odm_project = context.run_dir
        reconstruction_json = odm_project / "opensfm" / "reconstruction.json"
        stats_json = odm_project / "odm_report" / "stats.json"
        opensfm_stats_json = odm_project / "opensfm" / "stats.json"  # Fallback path 1
        opensfm_nested_stats_json = odm_project / "opensfm" / "stats" / "stats.json"  # Fallback path 2 (user requested)
        
        metrics = {
            "stage": "SfM",
            "registered_images": 0,
            "total_images": 0,
            "registration_rate": 0.0,
            "sparse_points": 0,
            "reprojection_error": None,
            "status": "Failed"
        }
        
        # 1. Image counts and registration
        images_dir = odm_project / "images"
        if images_dir.exists():
            metrics["total_images"] = len(list(images_dir.glob("*")))
            
        if reconstruction_json.exists():
            try:
                with open(reconstruction_json, "r") as f:
                    data = json.load(f)
                    if data and isinstance(data, list):
                        recon = data[0]
                        metrics["registered_images"] = len(recon.get("shots", {}))
                        metrics["sparse_points"] = len(recon.get("points", {}))
                        metrics["status"] = "Success"
                        
                        if metrics["total_images"] > 0:
                             metrics["registration_rate"] = metrics["registered_images"] / metrics["total_images"]
            except Exception as e:
                print(f"[ODM/OpenSfM] Warning: Could not parse reconstruction.json for metrics: {e}")
        
        # 2. Extract RMSE from stats.json (try multiple paths)
        rmse_extracted = False
        for stats_path in [stats_json, opensfm_stats_json, opensfm_nested_stats_json]:
            if stats_path.exists() and not rmse_extracted:
                try:
                    with open(stats_path, "r") as f:
                        stats = json.load(f)
                        # Support both top-level and nested 'opensfm' stats
                        sfm_stats = stats.get("opensfm", stats)
                        if sfm_stats.get("reprojection_error_rmse") is not None:
                            metrics["reprojection_error"] = sfm_stats.get("reprojection_error_rmse")
                            rmse_extracted = True
                        # Also try alternative key names
                        elif sfm_stats.get("reprojection_error") is not None:
                            metrics["reprojection_error"] = sfm_stats.get("reprojection_error")
                            rmse_extracted = True
                except Exception as e:
                    print(f"[ODM/OpenSfM] Warning: Could not parse {stats_path.name}: {e}")
        
        # 3. Identify visualization assets (images)
        report_assets_dir = odm_project / "odm_report"
        if report_assets_dir.exists():
            visualizations = {}
            # Common ODM report assets
            asset_map = {
                "overlap": ["overlap.png", "overlap.jpg"],
                "residuals": ["residuals.png", "residuals.jpg"],
                "gps_error": ["gps_error.png", "gps_error.jpg"],
                "camera_errors": ["camera_errors.png", "camera_errors.jpg"]
            }
            
            for key, filenames in asset_map.items():
                for filename in filenames:
                    asset_path = report_assets_dir / filename
                    if asset_path.exists():
                        # Store relative path for Markdown embedding
                        visualizations[key] = str(asset_path.relative_to(odm_project))
                        break
            
            metrics["visualizations"] = visualizations
        
        # 4. Extract Mesh Metrics if enabled
        if context.config.run_mesh:
            mesh_metrics = {"status": "Pending"}
            mesh_ply = odm_project / "odm_meshing" / "odm_mesh.ply"
            
            # Try to get from stats.json first
            if stats_json.exists():
                try:
                    with open(stats_json, "r") as f:
                        stats = json.load(f)
                        if "mesh" in stats:
                            mesh_metrics.update({
                                "vertices": stats["mesh"].get("vertices"),
                                "faces": stats["mesh"].get("faces"),
                                "status": "Success"
                            })
                except:
                    pass
            
            # Fallback: Parse PLY header if file exists and stats missing
            if mesh_metrics.get("status") != "Success" and mesh_ply.exists():
                try:
                    with open(mesh_ply, "rb") as f:
                        header = f.read(1024).decode(errors='ignore')
                        v_match = re.search(r"element vertex (\d+)", header)
                        f_match = re.search(r"element face (\d+)", header)
                        if v_match and f_match:
                            mesh_metrics.update({
                                "vertices": int(v_match.group(1)),
                                "faces": int(f_match.group(1)),
                                "status": "Success"
                            })
                except Exception as e:
                    print(f"[ODM/OpenSfM] Warning: Could not parse mesh PLY header: {e}")
            
            metrics["mesh"] = mesh_metrics
                
        context.metrics["sfm"] = metrics

    def _check_gpu_support(self, docker_image: str) -> bool:
        """
        Check if docker supports --gpus all by running a minimal command.
        """
        try:
            print(f"[ODM/OpenSfM] Probing GPU support with {docker_image}...")
            # Use a very fast command to probe
            probe_cmd = ["docker", "run", "--rm", "--gpus", "all", docker_image, "true"]
            result = subprocess.run(
                probe_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=15
            )
            return result.returncode == 0
        except Exception:
            return False
    

    
    def _write_opensfm_config(self, opensfm_dir: Path, params: dict):
        """Write OpenSfM config.yaml file."""
        if not params:
            return
        
        config_path = opensfm_dir / "config.yaml"
        with open(config_path, "w") as f:
            for k, v in params.items():
                # Handle different value types
                if isinstance(v, bool):
                    f.write(f"{k}: {'true' if v else 'false'}\n")
                elif isinstance(v, str):
                    f.write(f'{k}: "{v}"\n')
                else:
                    f.write(f"{k}: {v}\n")
