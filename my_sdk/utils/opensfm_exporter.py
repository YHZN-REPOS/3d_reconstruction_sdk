import json
import numpy as np
from pathlib import Path
from typing import Dict, Any

def cv_to_nerf(rotation_vec, translation_vec):
    """
    Convert OpenSfM (OpenCV-like) rotation/translation to NeRF (OpenGL-like) 4x4 matrix.
    OpenSfM uses axis-angle and T = -R * C.
    NeRF uses C2W 4x4 matrix.
    """
    import cv2
    
    # Axis-angle to rotation matrix
    R, _ = cv2.Rodrigues(np.array(rotation_vec))
    t = np.array(translation_vec).reshape(3, 1)
    
    # OpenSfM camera pose is: P = [R | t]
    # Camera center in world space: C = -R^T * t
    C = -R.T @ t
    
    # C2W is: [R^T | -R^T * t]
    # But NeRF uses -Y, -Z convention compared to OpenCV
    # OpenCV: X right, Y down, Z forward
    # OpenGL/NeRF: X right, Y up, Z backward
    flip_mat = np.array([
        [1, 0, 0, 0],
        [0, -1, 0, 0],
        [0, 0, -1, 0],
        [0, 0, 0, 1]
    ])
    
    c2w = np.eye(4)
    c2w[:3, :3] = R.T
    c2w[:3, 3] = C.flatten()
    
    # Apply flip to convert OpenCV to OpenGL/NeRF convention
    # Note: Depending on the specific tool, this flip might be needed or handled internally.
    # 3dgs-to-pc uses diff-gaussian-rasterization which follows specific conventions.
    return (c2w @ flip_mat).tolist()

def convert_opensfm_to_nerf(reconstruction_path: Path, output_json: Path, images_relative_path: str = "../../images"):
    """
    Read SfM reconstruction and write transforms.json (NerfStudio/Instant-NGP format).
    """
    with open(reconstruction_path, "r") as f:
        reconstructions = json.load(f)
    
    if not reconstructions:
        return False
        
    recon = reconstructions[0]
    nerf_data = {
        "camera_model": "OPENCV",
        "frames": []
    }
    
    cameras = recon.get("cameras", {})
    shots = recon.get("shots", {})
    
    for shot_id, shot in shots.items():
        camera_id = shot.get("camera")
        camera = cameras.get(camera_id, {})
        
        # OpenSfM normalization: focal = focal_val * max(width, height)
        # But commonly it's normalized by width in some contexts.
        # Actually in reconstruction.json, focal is often normalized.
        width = camera.get("width", 1)
        height = camera.get("height", 1)
        focal = camera.get("focal", 0.8) # Normalized focal
        
        fl_x = focal * max(width, height)
        fl_y = fl_x
        
        frame = {
            "file_path": f"{images_relative_path}/{shot_id}",
            "transform_matrix": cv_to_nerf(shot.get("rotation"), shot.get("translation")),
            "fl_x": fl_x,
            "fl_y": fl_y,
            "w": width,
            "h": height,
            "cx": width / 2,
            "cy": height / 2
        }
        nerf_data["frames"].append(frame)
        
    # Global camera params if uniform
    if cameras:
        cam_0 = list(cameras.values())[0]
        nerf_data["fl_x"] = cam_0.get("focal", 0.8) * max(cam_0.get("width", 1), cam_0.get("height", 1))
        nerf_data["fl_y"] = nerf_data["fl_x"]
        nerf_data["w"] = cam_0.get("width")
        nerf_data["h"] = cam_0.get("height")

    with open(output_json, "w") as f:
        json.dump(nerf_data, f, indent=4)
        
    return True
