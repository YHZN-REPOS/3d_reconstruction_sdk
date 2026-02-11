import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CoordinateSystem(BaseModel):
    type: int = 2
    label: str = "WGS 84"
    epsg_code: int = 4326

class CameraConfig(BaseModel):
    """
    Camera intrinsic parameters configuration.
    If not provided, parameters will be extracted from EXIF or estimated.
    """
    # Camera model type
    model: str = Field(default="perspective", description="Models: perspective, fisheye, equirectangular, brown, pinhole")
    
    # Basic intrinsics (optional - will use EXIF if not specified)
    focal_length_mm: Optional[float] = Field(default=None, description="Focal length in millimeters")
    sensor_width_mm: Optional[float] = Field(default=None, description="Sensor width in millimeters")
    sensor_height_mm: Optional[float] = Field(default=None, description="Sensor height in millimeters")
    
    # Principal point offset (from image center, in pixels)
    principal_point_x: Optional[float] = Field(default=None, description="Principal point X offset")
    principal_point_y: Optional[float] = Field(default=None, description="Principal point Y offset")
    
    # Distortion coefficients (for brown/fisheye models)
    # k1, k2, k3: radial distortion; p1, p2: tangential distortion
    distortion_k1: Optional[float] = Field(default=None)
    distortion_k2: Optional[float] = Field(default=None)
    distortion_k3: Optional[float] = Field(default=None)
    distortion_p1: Optional[float] = Field(default=None)
    distortion_p2: Optional[float] = Field(default=None)

class AlgorithmConfig(BaseModel):
    sfm: str = "opensfm"
    reconstruction: str = "opensplat"
    # Docker Configuration
    sfm_docker_image: str = "opendronemap/odm:latest"  # ODM includes OpenSfM
    reconstruction_docker_image: str = "opensplat:latest"
    gs_to_pc_docker_image: str = "gs2pc-tool:latest"

class TaskConfig(BaseModel):
    # Core Paths - working_dir contains all project data
    # Structure: working_dir/images/ for input, working_dir/sparse/, working_dir/result/ for output
    # If not specified, will be inferred from config file location
    working_dir: Optional[str] = Field(default=None, description="Project directory. If not set, uses config file's directory")
    
    # Algorithm Selection
    algorithms: AlgorithmConfig = Field(default_factory=AlgorithmConfig)
    
    # High-level Flags
    run_sparse: bool = True          # Sparse Reconstruction (SfM)
    run_mesh: bool = False           # 3D Mesh (via ODM)
    run_gaussian: bool = True        # Gaussian Splatting
    run_gs_to_pc: bool = False       # 3DGS to Point Cloud conversion
    
    # High-level Business Parameters
    camera: CameraConfig = Field(default_factory=CameraConfig, description="Camera intrinsic parameters")
    use_gps: bool = Field(default=True, description="Use GPS data from images if available")
    quality_preset: str = Field(default="medium", description="Presets: high, medium, low")
    
    # Core Algorithm Tunables (Exposed for easy access)
    feature_type: str = Field(default="sift", description="SfM Feature Type: sift, akaze, etc")
    sh_degree: int = Field(default=3, description="Gaussian Splatting SH Degree (1-3)")
    
    # Generic params passed to sub-processes
    # Key = algorithm name (e.g. "opensfm", "colmap"), Value = param dict
    # Optional for "Ordinary Users" (Merged with presets)
    params: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    @property
    def input_images_dir(self) -> str:
        """Input images directory - always working_dir/images"""
        return str(Path(self.working_dir) / "images")
    
    def validate_paths(self):
        if self.working_dir is None:
            raise ValueError("working_dir is not set. Use from_file() to auto-infer from config path.")
        images_path = Path(self.input_images_dir)
        if not images_path.exists():
            raise FileNotFoundError(
                f"Input images directory not found: {images_path}\n"
                f"Please place your images in {self.working_dir}/images/"
            )
        
    @classmethod
    def from_json(cls, json_path: str) -> 'TaskConfig':
        """Load config from JSON file. Infers working_dir from file location if not set."""
        json_path = str(Path(json_path).resolve())
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        
        # Priority 1: DATA_DIR environment variable (Override)
        env_data_dir = os.environ.get("DATA_DIR")
        if env_data_dir:
             data['working_dir'] = str(Path(env_data_dir).resolve())
             print(f"[Config] working_dir set from DATA_DIR env: {data['working_dir']}")
        
        # Priority 2: Config file explicit setting
        # Priority 3: Auto-infer (Fallback)
        elif data.get('working_dir') is None:
            data['working_dir'] = str(Path(json_path).parent)
            print(f"[Config] working_dir auto-inferred: {data['working_dir']}")
            
        config = cls(**data)
        config.validate_paths()
        return config
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'TaskConfig':
        """Load config from YAML file. Infers working_dir from file location if not set."""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML config files. Install with: pip install pyyaml")
        
        yaml_path = str(Path(yaml_path).resolve())
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        
        # Priority 1: DATA_DIR environment variable (Override)
        env_data_dir = os.environ.get("DATA_DIR")
        if env_data_dir:
             data['working_dir'] = str(Path(env_data_dir).resolve())
             print(f"[Config] working_dir set from DATA_DIR env: {data['working_dir']}")

        # Priority 2: Config file explicit setting
        # Priority 3: Auto-infer (Fallback)
        elif data.get('working_dir') is None:
            data['working_dir'] = str(Path(yaml_path).parent)
            print(f"[Config] working_dir auto-inferred: {data['working_dir']}")
        
        config = cls(**data)
        config.validate_paths()
        return config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'TaskConfig':
        """Load config from file, auto-detecting format by extension."""
        config_path_lower = config_path.lower()
        if config_path_lower.endswith('.yaml') or config_path_lower.endswith('.yml'):
            return cls.from_yaml(config_path)
        else:
            return cls.from_json(config_path)
