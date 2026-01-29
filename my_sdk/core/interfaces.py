from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
import shutil
from .config import TaskConfig

class ReconstructionContext:
    """
    Context object passed between strategies.
    Holds configuration and paths to intermediate data.
    Each run creates a timestamped directory under runs/ to avoid conflicts.
    """
    def __init__(self, config: TaskConfig, config_file_path: str = None):
        import os
        self.config = config
        
        # Check for RESUME_ID environment variable
        resume_id = os.environ.get("RESUME_ID")
        
        if resume_id:
            # Use existing run directory
            self.run_dir = Path(config.working_dir) / "runs" / resume_id
            if not self.run_dir.exists():
                raise ValueError(f"Resume ID {resume_id} specified, but directory {self.run_dir} does not exist.")
            print(f"[Pipeline] Resuming from existing directory: {self.run_dir}")
        else:
            # Create timestamped run directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_dir: Path = Path(config.working_dir) / "runs" / timestamp
            print(f"[Pipeline] Creating new run directory: {self.run_dir}")
        
        # All outputs go under run_dir
        self.sparse_model_path: Path = self.run_dir / "sparse"
        self.dense_model_path: Path = self.run_dir / "dense"
        self.result_path: Path = self.run_dir / "result"
        self.log_path: Path = self.run_dir / "logs"
        
        # Create working directories (idempotent if they exist)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_model_path.mkdir(parents=True, exist_ok=True)
        self.dense_model_path.mkdir(parents=True, exist_ok=True)
        self.result_path.mkdir(parents=True, exist_ok=True)
        self.log_path.mkdir(parents=True, exist_ok=True)
        
        # Copy config file to run directory for reproducibility
        # Only copy if creating new or if explicit overwrite logic (here we always copy/overwrite to ensure latest config is used)
        if config_file_path:
            src_config = Path(config_file_path)
            if src_config.exists():
                dest_config = self.run_dir / src_config.name
                shutil.copy2(src_config, dest_config)
                print(f"[Pipeline] Config saved: {dest_config}")

class PipelineStep(ABC):
    """
    Generic interface for any step in the reconstruction pipeline.
    Examples: PreProcessing, SfM, MVS, Mesh, texturing, PostProcessing.
    """
    @abstractmethod
    def run(self, context: ReconstructionContext) -> bool:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this step for logging"""
        pass

class SfMStrategy(PipelineStep):
    """
    Interface for Sparse Reconstruction (Structure from Motion) algorithms.
    """
    @property
    def name(self) -> str:
        return "Process: Structure from Motion"

class ReconstructionStrategy(PipelineStep):
    """
    Interface for Dense Reconstruction or Neural Rendering algorithms.
    """
    @property
    def name(self) -> str:
        return "Process: Reconstruction / Splatting"
