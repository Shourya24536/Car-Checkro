"""
Marker module for generating 3D defect geometries (scratches, dents)
and heat maps on the digital twin.
"""
from dataclasses import dataclass
import numpy as np
import open3d as o3d
from typing import Tuple, List, Optional
from .mapper import CanSurfaceMapper
from .config import CAN_BODY_RADIUS

@dataclass
class DefectMarker:
    id: str
    type: str  # "scratch", "dent", "heatmap"
    angle: float  # Angle in degrees [0, 360)
    height: float  # Z height in meters [-H/2, H/2]
    color: Tuple[float, float, float]
    radius: float = 0.003  # Size in meters
    confidence: float = 0.95
    label: str = "Defect"
    description: str = "Unspecified defect"
    
    # Animation properties
    pulse_frequency: float = 5.0  # Hz
    pulse_amplitude: float = 0.25 # Scale multiplier variance

    def get_pulse_scale(self, time_sec: float) -> float:
        """Calculates the animated scale multiplier for pulsing effect."""
        return 1.0 + self.pulse_amplitude * np.sin(2.0 * np.pi * self.pulse_frequency * time_sec)


def generate_sphere_marker(
    pos_3d: np.ndarray,
    radius: float,
    color: Tuple[float, float, float]
) -> o3d.geometry.TriangleMesh:
    """Creates a basic sphere mesh to mark a defect."""
    sphere = o3d.geometry.TriangleMesh.create_sphere(radius=radius, resolution=10)
    sphere.translate(pos_3d)
    
    # Paint vertex colors
    colors = np.full((len(sphere.vertices), 3), color)
    sphere.vertex_colors = o3d.utility.Vector3dVector(colors)
    sphere.compute_vertex_normals()
    return sphere


def generate_scratch_geometry(
    mapper: CanSurfaceMapper,
    center_angle: float,
    center_height: float,
    length: float,
    angle_deg: float,  # orientation relative to horizontal
    thickness: float,
    color: Tuple[float, float, float]
) -> o3d.geometry.TriangleMesh:
    """
    Generates a curved 3D tube mesh on the surface of the can representing a scratch.
    """
    pts_3d = []
    num_segments = 12
    t_vals = np.linspace(-length / 2.0, length / 2.0, num_segments)
    
    # Calculate radius of can body
    r_body = CAN_BODY_RADIUS
    
    for t in t_vals:
        # Offset along the scratch path (in meters)
        dx = t * np.cos(np.radians(angle_deg))
        dy = t * np.sin(np.radians(angle_deg))
        
        # Convert physical tangent offsets to surface angle and height offsets
        # ds = r_body * dtheta => dtheta = ds / r_body
        dtheta_deg = np.degrees(dx / r_body)
        dheight = dy
        
        pt_angle = (center_angle + dtheta_deg) % 360.0
        pt_height = center_height + dheight
        
        # Map back to 3D on the actual curved can wall
        xyz = mapper.surface_to_xyz(pt_angle, pt_height)
        pts_3d.append(xyz)
        
    # Generate tube by sweeping spheres along path (extremely robust)
    scratch_mesh = o3d.geometry.TriangleMesh()
    for pt in pts_3d:
        node = o3d.geometry.TriangleMesh.create_sphere(radius=thickness, resolution=8)
        node.translate(pt)
        scratch_mesh += node
        
    colors = np.full((len(scratch_mesh.vertices), 3), color)
    scratch_mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    scratch_mesh.compute_vertex_normals()
    
    return scratch_mesh


def deform_mesh_for_dent(
    mesh: o3d.geometry.TriangleMesh,
    mapper: CanSurfaceMapper,
    dent_angle: float,
    dent_height: float,
    dent_radius: float,
    dent_depth: float
) -> None:
    """
    Physically deforms the vertices of the can mesh inwards to simulate a real dent.
    Paints the dented area red.
    Modifies the mesh in-place.
    """
    dent_center = mapper.surface_to_xyz(dent_angle, dent_height)
    vertices = np.asarray(mesh.vertices)
    
    # Distance of all vertices to dent center
    dists = np.linalg.norm(vertices - dent_center, axis=1)
    
    # Find vertices inside dent sphere
    inside_mask = dists < dent_radius
    
    if np.any(inside_mask):
        # Direction to push: inwards towards the Z axis (radial direction)
        radial_dirs = vertices[inside_mask].copy()
        radial_dirs[:, 2] = 0.0  # project to XY plane
        norms = np.linalg.norm(radial_dirs, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1.0
        inward_vectors = -radial_dirs / norms
        
        # Displacement scale: parabolic profile (zero at boundary, max depth at center)
        dist_fraction = dists[inside_mask] / dent_radius
        displacement_scale = dent_depth * (1.0 - dist_fraction ** 2)
        
        # Apply deformation
        vertices[inside_mask] += inward_vectors * displacement_scale[:, np.newaxis]
        
        # Color the dent vertices red to highlight it directly on the surface
        colors = np.asarray(mesh.vertex_colors).copy()
        colors[inside_mask] = np.array([0.9, 0.05, 0.05]) # Red
        mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
        
        # Update mesh vertices
        mesh.vertices = o3d.utility.Vector3dVector(vertices)
        mesh.compute_vertex_normals()


def paint_scratch_on_mesh(
    mesh: o3d.geometry.TriangleMesh,
    mapper: CanSurfaceMapper,
    scratch_angle: float,
    scratch_height: float,
    length_mm: float,
    width_mm: float,
    orientation_deg: float,
    color: Tuple[float, float, float] = (0.05, 0.1, 0.9) # Blue
) -> None:
    """
    Paints a scratch-shaped patch (elongated ellipse/line) directly on the can surface vertices.
    Modifies the mesh in-place.
    """
    
    vertices = np.asarray(mesh.vertices)
    colors = np.asarray(mesh.vertex_colors).copy()
    
    # 1. Project vertices to surface coordinates
    angles = np.arctan2(vertices[:, 1], vertices[:, 0]) # range [-pi, pi]
    angles_deg = np.degrees(angles) % 360.0
    heights = vertices[:, 2]
    
    # 2. Delta surface coordinates relative to scratch center
    d_angles = (angles_deg - scratch_angle + 180.0) % 360.0 - 180.0
    d_angles_m = CAN_BODY_RADIUS * np.radians(d_angles)
    d_heights_m = heights - scratch_height
    
    # 3. Rotate delta coordinates by orientation to align with scratch line
    theta_orient = np.radians(orientation_deg)
    cos_o = np.cos(theta_orient)
    sin_o = np.sin(theta_orient)
    
    rotated_x = d_angles_m * cos_o + d_heights_m * sin_o
    rotated_y = -d_angles_m * sin_o + d_heights_m * cos_o
    
    # 4. Check if vertex lies inside the scratch dimensions (converted to meters)
    half_len = max(0.001, (length_mm / 1000.0) / 2.0)
    half_wid = max(0.0003, (width_mm / 1000.0) / 2.0)
    
    inside_mask = (rotated_x / half_len)**2 + (rotated_y / half_wid)**2 <= 1.0
    
    if np.any(inside_mask):
        colors[inside_mask] = np.array(color)
        mesh.vertex_colors = o3d.utility.Vector3dVector(colors)



def apply_heatmap_to_mesh(
    mesh: o3d.geometry.TriangleMesh,
    hotspots: List[Tuple[float, float, float]],  # List of (angle, height, intensity)
    mapper: CanSurfaceMapper,
    influence_radius: float = 0.015
) -> np.ndarray:
    """
    Applies a defect density heatmap directly to the can mesh by interpolating vertex colors.
    Returns the new vertex colors.
    """
    vertices = np.asarray(mesh.vertices)
    original_colors = np.asarray(mesh.vertex_colors).copy()
    new_colors = original_colors.copy()
    
    # Calculate 3D points for all hotspots
    hotspot_xyzs = []
    intensities = []
    for angle, height, intensity in hotspots:
        hotspot_xyzs.append(mapper.surface_to_xyz(angle, height))
        intensities.append(intensity)
        
    if not hotspot_xyzs:
        return new_colors
        
    hotspot_xyzs = np.array(hotspot_xyzs)
    
    # For each vertex, calculate influence
    for i, vert in enumerate(vertices):
        # Distance to all hotspots
        dists = np.linalg.norm(hotspot_xyzs - vert, axis=1)
        
        # Compute weights based on distance
        weights = np.maximum(0.0, 1.0 - (dists / influence_radius))
        total_heat = np.sum(weights * intensities)
        total_heat = np.clip(total_heat, 0.0, 1.0)
        
        if total_heat > 0.0:
            # Color mapping: interpolating from aluminum-gray to red
            # Red color for high heat
            heat_color = np.array([0.9, 0.1, 0.1])
            new_colors[i] = (1.0 - total_heat) * original_colors[i] + total_heat * heat_color
            
    mesh.vertex_colors = o3d.utility.Vector3dVector(new_colors)
    return new_colors
