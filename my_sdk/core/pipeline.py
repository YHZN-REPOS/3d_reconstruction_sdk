from typing import Dict, Type
from my_sdk.core.interfaces import SfMStrategy, ReconstructionStrategy, ReconstructionContext
from my_sdk.core.config import TaskConfig

# Adapter Registry
from my_sdk.adapters.opensfm import OpenSfMAdapter
from my_sdk.adapters.opensplat import OpenSplatAdapter

class PipelineFactory:
    _sfm_registry: Dict[str, Type[SfMStrategy]] = {
        "opensfm": OpenSfMAdapter
    }
    _recon_registry: Dict[str, Type[ReconstructionStrategy]] = {
        "opensplat": OpenSplatAdapter
    }
    
    @classmethod
    def create_sfm(cls, name: str) -> SfMStrategy:
        if name not in cls._sfm_registry:
             raise ValueError(f"Unknown SfM algorithm: {name}")
        return cls._sfm_registry[name]()

    @classmethod
    def create_reconstruction(cls, name: str) -> ReconstructionStrategy:
        if name not in cls._recon_registry:
             raise ValueError(f"Unknown Reconstruction algorithm: {name}")
        return cls._recon_registry[name]()

class ReconstructionPipeline:
    # Step type constants for stages API
    STEP_SFM = "sfm"
    STEP_MESH = "mesh"
    STEP_RECONSTRUCTION = "reconstruction"
    
    def __init__(self, config: TaskConfig, config_file_path: str = None):
        self.config = config
        self.context = ReconstructionContext(config, config_file_path)
        self.steps = {}  # Changed to dict for named access
        
        # --- Dependency Validation ---
        self._validate_dependencies()
        
        # --- Build the Pipeline Chain ---
        # The order here defines the execution order.
        # This structure allows easy insertion of new steps (e.g. PreProcessStep)
        
        # 1. SfM Step (also handles mesh if run_mesh is true)
        if config.run_sparse or config.run_mesh:
            self.steps[self.STEP_SFM] = PipelineFactory.create_sfm(config.algorithms.sfm)
            
        # Note: Mesh generation is handled by ODM when run_mesh=true
        # No separate step needed
        
        # 3. Gaussian Step
        if config.run_gaussian:
            self.steps[self.STEP_RECONSTRUCTION] = PipelineFactory.create_reconstruction(config.algorithms.reconstruction)
    
    def _validate_dependencies(self):
        """
        Validate step dependencies before building the pipeline.
        Raises ValueError if dependencies are not satisfied.
        """
        config = self.config
        
        # Gaussian Splatting requires SfM/Sparse reconstruction
        if config.run_gaussian and not (config.run_sparse):
            raise ValueError(
                "Gaussian Splatting requires sparse reconstruction. "
                "Please set 'run_sparse' to true."
            )
        
        # Mesh reconstruction typically requires sparse reconstruction too
        if config.run_mesh and not (config.run_sparse):
            raise ValueError(
                "Mesh reconstruction requires sparse reconstruction. "
                "Please set 'run_sparse' to true."
            )
            
    def run(self, stages: list = None):
        """
        Run the reconstruction pipeline chain.
        
        Args:
            stages: Optional list of stage names to run (e.g., ["sfm", "reconstruction"]).
                   If None, runs all configured steps in order.
        
        Returns:
            bool: True if all requested stages completed successfully.
        """
        # Determine which steps to run
        if stages is None:
            steps_to_run = list(self.steps.items())
        else:
            steps_to_run = []
            for stage_name in stages:
                if stage_name not in self.steps:
                    if stage_name in [self.STEP_SFM, self.STEP_MESH, self.STEP_RECONSTRUCTION]:
                        print(f"Warning: Stage '{stage_name}' not configured, skipping.")
                    else:
                        raise ValueError(f"Unknown stage: {stage_name}")
                else:
                    steps_to_run.append((stage_name, self.steps[stage_name]))
        
        if not steps_to_run:
            print("Warning: No stages to run.")
            return True
        
        print("=== Starting 3D Reconstruction Pipeline ===")
        print(f"Plan: {[step.name for _, step in steps_to_run]}")
        
        for stage_name, step in steps_to_run:
            print(f"--- Stage: {step.name} ---")
            if not step.run(self.context):
                print(f"Pipeline aborted at step: {step.name}")
                return False
            
        print("=== Pipeline Completed Successfully ===")
        return True
