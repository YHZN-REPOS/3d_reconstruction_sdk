from my_sdk.core.config import TaskConfig
from my_sdk.core.pipeline import ReconstructionPipeline

# ==========================================
# For Algorithm Engineers: Python-First Usage
# ==========================================

def run_experiment():
    # 1. Define Config programmatically (No JSON needed)
    # Generic 'params' dict allows for infinite extensibility
    config = TaskConfig(
        working_dir="/tmp/experiment_002",
        input_images_dir="/path/to/dataset/images",
        
        # Pass algorithm-specific parameters via nested dicts
        params={
            "opensfm": {
                "matching_gps_neighbors": 0,
                "feature_type": "SIFT",  
                "feature_root": 1        
            },
            "opensplat": {
                "iterations": 7000,
                "sh_degree": 2
            },
            # Future algorithms work out-of-the-box:
            # "colmap": { "quality": "high" } 
        }
    )
    
    # 2. Initialize Pipeline
    pipeline = ReconstructionPipeline(config)
    
    # 3. Interactive / Step-by-Step Execution
    
    # Step A: Run SfM only to check sparse point cloud
    print(">>> Running Sparse Reconstruction...")
    if not pipeline.run(stages=["sfm"]):
        print("SfM Failed!")
        return
        
    # [Optional] Here you could load the point cloud, visualize it, 
    # or prune outlier points before proceeding.
    print(">>> (You can inspect /tmp/experiment_002/sparse now)")
    
    # Step B: Run Splatting if satisfied
    print(">>> Running Gaussian Splatting...")
    pipeline.run(stages=["reconstruction"])
    
if __name__ == "__main__":
    run_experiment()
