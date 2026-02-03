import subprocess
from pathlib import Path
from my_sdk.core.interfaces import ReconstructionStrategy, ReconstructionContext
from my_sdk.utils.docker_runner import DockerRunner

class OpenSplatAdapter(ReconstructionStrategy):
    """
    Adapter for OpenSplat (Gaussian Splatting).
    Wraps the 'opensplat' command.
    
    Uses OpenSfM output directly with --opensfm-image-path to specify
    the separate images directory.
    """
    
    def run(self, context: ReconstructionContext) -> bool:
        print("[OpenSplat] Starting Gaussian Splatting reconstruction...")
        
        # Initialize Docker runner with logging
        runner = DockerRunner(log_dir=context.log_path)
        
        # 1. Setup Output Directory
        # Use 3d_gsl/ subdirectory for Gaussian Splatting results
        gsl_output_dir = context.run_dir / "3d_gsl"
        gsl_output_dir.mkdir(parents=True, exist_ok=True)
        output_ply = gsl_output_dir / "splat.ply"
        
        # Check if output exists (Resume capability)
        if output_ply.exists():
            print(f"[OpenSplat] Found existing result at {output_ply}. Skipping reconstruction.")
            return True
        
        # 2. Build Splat Parameters
        splat_params = {
            "sh-degree": context.config.sh_degree,
            "keep-crs": True  # Maintain original point cloud scale and CRS
        }
        
        # Mapping quality logic
        if context.config.quality_preset == "high":
            splat_params["n"] = 30000  # iterations
            splat_params["s"] = 5000   # save every N iterations
        elif context.config.quality_preset == "low":
            splat_params["n"] = 7000
            splat_params["s"] = 1000
        else:  # medium
            splat_params["n"] = 15000
            splat_params["s"] = 2000
            
        # User overrides (highest priority)
        user_overrides = context.config.params.get("opensplat", {})
        # Map 'iterations' to 'n' for backward compatibility
        if "iterations" in user_overrides:
            user_overrides["n"] = user_overrides.pop("iterations")
        splat_params.update(user_overrides)

        # 3. Construct Docker Command with DooD (Docker-outside-of-Docker)
        import os
        host_data_dir = os.environ.get("HOST_DATA_DIR")
        if not host_data_dir:
            raise ValueError("HOST_DATA_DIR environment variable is missing. Required for DooD.")

        # Reconstruct host paths
        images_src = Path(context.config.input_images_dir)
        rel_run_path = context.run_dir.relative_to(context.config.working_dir)
        rel_images_path = images_src.relative_to(context.config.working_dir)
        
        host_run_dir = Path(host_data_dir) / rel_run_path
        host_images_dir = Path(host_data_dir) / rel_images_path
        
        docker_image = context.config.algorithms.reconstruction_docker_image
        
        # Check GPU availability
        use_gpu = DockerRunner.check_gpu_support()
        if not use_gpu:
            print("[OpenSplat] WARNING: GPU not available or nvidia-docker not configured. Attempting CPU-only reconstruction.")
            print("[OpenSplat] TIP: Gaussian Splatting is extremely slow on CPU. For better performance, please use an NVIDIA GPU.")
        
        # Container paths
        container_project = "/project"
        container_images = "/images"
        container_output = f"{container_project}/3d_gsl/splat.ply"
        
        # Build Docker command
        command = [
            "docker", "run", "--rm",
            "-v", f"{host_run_dir}:{container_project}",
            "-v", f"{host_images_dir}:{container_images}:ro",
            "-e", "NVIDIA_VISIBLE_DEVICES=all",
            "-e", "NVIDIA_DRIVER_CAPABILITIES=all",
            docker_image,
            "opensplat",
            container_project,                          # Input: OpenSfM project directory
            "-o", container_output,                     # Output: PLY file
            "--opensfm-image-path", container_images,   # Separate images path
        ]

        if use_gpu:
            command.insert(2, "--gpus")
            command.insert(3, "all")
        
        # Add splat parameters
        for k, v in splat_params.items():
            if isinstance(v, bool):
                if v:  # Only add boolean flags if True (e.g., --keep-crs)
                    if len(k) == 1:
                        command.append(f"-{k}")
                    else:
                        command.append(f"--{k}")
            else:
                if len(k) == 1:
                    command.extend([f"-{k}", str(v)])   # Short option: -n, -s
                else:
                    command.extend([f"--{k}", str(v)])  # Long option: --sh-degree

        # 4. Execute using DockerRunner
        success = runner.run(command, step_name="OpenSplat")
        
        if success:
            print(f"[OpenSplat] Reconstruction finished. Result at {output_ply}")
            self._extract_metrics(context)
        
        return success
    
    def _extract_metrics(self, context: ReconstructionContext):
        """Extract and store Gaussian Splatting metrics from training logs."""
        import re
        metrics = {
            "stage": "GaussianSplatting",
            "final_loss": None,
            "gaussian_count": None,
            "status": "Success"
        }
        
        # OpenSplat logs are stored in context.log_path / opensplat_*.log
        log_files = list(context.log_path.glob("opensplat_*.log"))
        if log_files:
            # Get the most recent log file
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            
            try:
                with open(latest_log, "r") as f:
                    log_content = f.read()
                    
                    # 1. Loss from OpenSplat format: "Step 2000: 0.103071 (100%)"
                    loss_matches = re.findall(r"Step\s+\d+:\s+([\d.]+)", log_content)
                    if loss_matches:
                        metrics["loss_history"] = [float(l) for l in loss_matches]
                        metrics["final_loss"] = float(loss_matches[-1])
                    
                    # 2. Gaussian Count: Try parsing from log "gaussians remaining" pattern
                    count_matches = re.findall(r"([\d,]+)\s*gaussians?\s*(?:remaining)?", log_content, re.IGNORECASE)
                    if count_matches:
                        # Remove commas and get last value
                        metrics["gaussian_count"] = int(count_matches[-1].replace(",", ""))
                        
            except Exception as e:
                print(f"[OpenSplat] Warning: Could not parse logs for metrics: {e}")
        
        # 3. Fallback: Get gaussian count from PLY file header
        if metrics["gaussian_count"] is None:
            splat_ply = context.run_dir / "3d_gsl" / "splat.ply"
            if splat_ply.exists():
                try:
                    with open(splat_ply, "rb") as f:
                        header = f.read(2048).decode(errors='ignore')
                        # PLY header: "element vertex 123456"
                        v_match = re.search(r"element vertex (\d+)", header)
                        if v_match:
                            metrics["gaussian_count"] = int(v_match.group(1))
                except Exception as e:
                    print(f"[OpenSplat] Warning: Could not parse PLY header: {e}")
                
        context.metrics["reconstruction"] = metrics

