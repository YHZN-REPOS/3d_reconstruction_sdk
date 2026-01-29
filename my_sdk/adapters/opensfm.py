import subprocess
from pathlib import Path
from my_sdk.core.interfaces import SfMStrategy, ReconstructionContext
from my_sdk.utils.docker_runner import DockerRunner

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
        runner = DockerRunner(log_dir=context.log_path)
        
        # If resuming and output exists, skip SfM
        if reconstruction_json.exists():
             print(f"[ODM/OpenSfM] Found existing reconstruction at {reconstruction_json}. Skipping SfM step.")
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
        use_gpu = DockerRunner.check_gpu_support(docker_image)
        if not use_gpu:
            print("[ODM/OpenSfM] WARNING: GPU not available or nvidia-docker not configured. Falling back to CPU mode.")
            print("[ODM/OpenSfM] TIP: To enable GPU acceleration, install nvidia-container-toolkit and ensure your GPU drivers are working correctly.")
        
        # DooD Path Construction:
        # We need to reconstruct the HOST path equivalent to context.run_dir
        # context.run_dir is inside container (e.g., /project/runs/timestamp)
        # HOST_DATA_DIR is passed via env (e.g., /home/user/data)
        
        import os
        host_data_dir = os.environ.get("HOST_DATA_DIR")
        if not host_data_dir:
             raise ValueError("HOST_DATA_DIR environment variable is missing. Required for DooD.")
             
        # run_dir is typically {working_dir}/runs/{timestamp}
        # relative path from working_dir
        rel_run_path = context.run_dir.relative_to(context.config.working_dir)
        host_run_dir = Path(host_data_dir) / rel_run_path
        host_images_dir = Path(host_data_dir) / "images"

        # ODM container paths:
        # - Mount host_run_dir to /datasets/project (for outputs)
        # - Mount host_images_dir to /datasets/project/images (for input images)
        
        command = [
            "docker", "run", "--rm",
            "-v", "/etc/localtime:/etc/localtime:ro",
            "-v", f"{host_run_dir}:/datasets/project",
            "-v", f"{host_images_dir}:/datasets/project/images:ro",
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
        return runner.run(command, step_name="ODM/OpenSfM")
    
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
