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
            "sh-degree": context.config.sh_degree
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
        rel_run_path = context.run_dir.relative_to(context.config.working_dir)
        host_run_dir = Path(host_data_dir) / rel_run_path
        host_images_dir = Path(host_data_dir) / "images"
        
        docker_image = context.config.algorithms.reconstruction_docker_image
        
        # Check GPU availability
        use_gpu = DockerRunner.check_gpu_support(docker_image)
        if not use_gpu:
            print("[OpenSplat] WARNING: GPU not available or nvidia-docker not configured. Attempting CPU-only reconstruction.")
            print("[OpenSplat] TIP: Gaussian Splatting is extremely slow on CPU. For better performance, please use an NVIDIA GPU.")
        
        # Container paths
        container_project = "/project"
        container_images = "/images"
        container_output = f"{container_project}/3d_gsl/splat.ply"
        
        # Build Docker command
        # Structure:
        #   -v {host_run_dir}:/project     -> SfM results (opensfm/ directory)
        #   -v {host_images_dir}:/images   -> Input images (read-only)
        command = [
            "docker", "run", "--rm",
            "-v", f"{host_run_dir}:{container_project}",
            "-v", f"{host_images_dir}:{container_images}:ro",
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
            if len(k) == 1:
                command.extend([f"-{k}", str(v)])   # Short option: -n, -s
            else:
                command.extend([f"--{k}", str(v)])  # Long option: --sh-degree

        # 4. Execute using DockerRunner
        success = runner.run(command, step_name="OpenSplat")
        
        if success:
            print(f"[OpenSplat] Reconstruction finished. Result at {output_ply}")
        
        return success
