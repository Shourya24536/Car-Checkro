"""
Configuration file for the 3D Diet Coke can digital twin.
All physical measurements are in meters.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

# Physical Dimensions of a 330 mL Can
CAN_HEIGHT: float = 0.1222       # 122.2 mm
CAN_DIAMETER: float = 0.0662     # 66.2 mm
CAN_BODY_RADIUS: float = CAN_DIAMETER / 2.0  # 33.1 mm

# Detailed geometry dimensions (in meters)
BOTTOM_RIM_RADIUS: float = 0.0240  # 24.0 mm
BOTTOM_DOME_DEPTH: float = 0.0100  # 10.0 mm
TOP_NECK_RADIUS: float = 0.0260    # 26.0 mm
TOP_RIM_RADIUS: float = 0.0285     # 28.5 mm
TOP_LID_RADIUS: float = 0.0240     # 24.0 mm

# Mesh resolution
DEFAULT_ANGULAR_RESOLUTION: int = 128  # Number of steps around Z axis
DEFAULT_VERTICAL_RESOLUTION: int = 200 # Number of steps along profile height

# Materials config
ALUMINUM_BASE_COLOR: Tuple[float, float, float] = (0.85, 0.85, 0.85)  # Silver aluminum
ALUMINUM_METALLIC: float = 0.9
ALUMINUM_ROUGHNESS: float = 0.25

# Red brand accent color (e.g. for markers / lines)
DIET_COKE_RED: Tuple[float, float, float] = (0.80, 0.05, 0.10)
DIET_COKE_GRAY: Tuple[float, float, float] = (0.50, 0.50, 0.50)

# Camera configuration (Multi-camera inspection rig)
@dataclass
class CameraPreset:
    name: str
    position: Tuple[float, float, float]
    lookat: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    up: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    fov: float = 45.0  # Field of View in degrees

CAMERA_PRESETS: List[CameraPreset] = field(default_factory=lambda: [
    CameraPreset(name="Front", position=(0.0, -0.25, 0.0), up=(0.0, 0.0, 1.0)),
    CameraPreset(name="Back", position=(0.0, 0.25, 0.0), up=(0.0, 0.0, 1.0)),
    CameraPreset(name="Left", position=(-0.25, 0.0, 0.0), up=(0.0, 0.0, 1.0)),
    CameraPreset(name="Right", position=(0.25, 0.0, 0.0), up=(0.0, 0.0, 1.0)),
    CameraPreset(name="Top", position=(0.0, 0.0, 0.25), up=(0.0, 1.0, 0.0)),
    CameraPreset(name="Bottom", position=(0.0, 0.0, -0.25), up=(0.0, -1.0, 0.0)),
])
