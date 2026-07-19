"""
Material specifications for the 3D Coke can digital twin.
Defines realistic aluminum PBR materials and marker shaders.
"""
import open3d as o3d
from typing import List, Tuple
from .config import ALUMINUM_BASE_COLOR, ALUMINUM_METALLIC, ALUMINUM_ROUGHNESS

def get_aluminum_material() -> o3d.visualization.rendering.MaterialRecord:
    """
    Creates a Physical Material Record representing polished aluminum.
    """
    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultLit"
    mat.base_color = [
        ALUMINUM_BASE_COLOR[0],
        ALUMINUM_BASE_COLOR[1],
        ALUMINUM_BASE_COLOR[2],
        1.0
    ]
    mat.base_metallic = ALUMINUM_METALLIC
    mat.base_roughness = ALUMINUM_ROUGHNESS
    mat.base_reflectance = 0.5
    mat.base_clearcoat = 0.05
    return mat

def get_marker_material(color: Tuple[float, float, float]) -> o3d.visualization.rendering.MaterialRecord:
    """
    Creates a material for defect markers (highly visible, glossy).
    """
    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultLit"
    mat.base_color = [color[0], color[1], color[2], 1.0]
    mat.base_metallic = 0.1
    mat.base_roughness = 0.1  # shiny
    mat.base_clearcoat = 0.8  # extra highlight
    return mat

def get_glow_material(color: Tuple[float, float, float]) -> o3d.visualization.rendering.MaterialRecord:
    """
    Creates a non-lit emissive/glowing material for overlays and labels.
    """
    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "defaultUnlit"
    mat.base_color = [color[0], color[1], color[2], 1.0]
    return mat
