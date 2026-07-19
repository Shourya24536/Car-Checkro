"""
Procedural model generation for the 3D Diet Coke can digital twin.
Generates watertight meshes for the can body and the pull tab.
"""
import numpy as np
import open3d as o3d
from typing import Tuple
from .config import (
    CAN_HEIGHT, CAN_BODY_RADIUS, BOTTOM_RIM_RADIUS, BOTTOM_DOME_DEPTH,
    TOP_NECK_RADIUS, TOP_RIM_RADIUS, TOP_LID_RADIUS,
    DEFAULT_ANGULAR_RESOLUTION, DEFAULT_VERTICAL_RESOLUTION,
    ALUMINUM_BASE_COLOR
)
from .utils import evaluate_bezier_2d

def generate_can_profile() -> np.ndarray:
    """
    Generates the complete 2D profile curve of the Coke can in the (R, z) plane.
    Starts at bottom center (0, z_bottom) and ends at top center (0, z_top).
    
    Returns:
        np.ndarray of shape (N, 2) containing R and z coordinates.
    """
    h2 = CAN_HEIGHT / 2.0  # 0.0611 m
    
    # --- 1. Bottom Dome (Apex at R=0, z=-h2 + dome_depth) ---
    # Inverted parabola going down to the inner rim
    p_dome = evaluate_bezier_2d(
        p0=(0.0, -h2 + BOTTOM_DOME_DEPTH),
        p1=(0.008, -h2 + BOTTOM_DOME_DEPTH),
        p2=(0.022, -h2 + 0.002),
        p3=(0.022, -h2),
        num_points=25
    )
    
    # --- 2. Bottom Rim (Resting face) ---
    # Curves around the bottom contact circle
    p_rim_bottom = evaluate_bezier_2d(
        p0=(0.022, -h2),
        p1=(0.022, -h2 - 0.0005),
        p2=(0.0242, -h2 - 0.0005),
        p3=(0.0245, -h2 + 0.001),
        num_points=15
    )
    
    # --- 3. Bottom Taper ---
    # Smooth S-curve transition to the main body cylinder
    p_bottom_taper = evaluate_bezier_2d(
        p0=(0.0245, -h2 + 0.001),
        p1=(0.0250, -h2 + 0.005),
        p2=(CAN_BODY_RADIUS, -h2 + 0.008),
        p3=(CAN_BODY_RADIUS, -h2 + 0.015),
        num_points=20
    )
    
    # --- 4. Main Cylinder Body ---
    # Vertical wall of the can
    z_start = -h2 + 0.015
    z_end = h2 - 0.018
    num_body = 50
    z_body = np.linspace(z_start, z_end, num_body)
    r_body = np.full_like(z_body, CAN_BODY_RADIUS)
    p_body = np.column_stack((r_body, z_body))
    
    # --- 5. Top Shoulder Taper ---
    # Smooth S-curve taper necking down to the top neck
    p_top_shoulder = evaluate_bezier_2d(
        p0=(CAN_BODY_RADIUS, h2 - 0.018),
        p1=(CAN_BODY_RADIUS, h2 - 0.012),
        p2=(TOP_NECK_RADIUS, h2 - 0.009),
        p3=(TOP_NECK_RADIUS, h2 - 0.006),
        num_points=30
    )
    
    # --- 6. Top Neck ---
    # Small vertical collar
    p_neck = np.array([
        [TOP_NECK_RADIUS, h2 - 0.006],
        [TOP_NECK_RADIUS, h2 - 0.004]
    ])
    
    # --- 7. Rolled Rim ---
    # Outer flaring rim (going up and out)
    p_rim_outer = evaluate_bezier_2d(
        p0=(TOP_NECK_RADIUS, h2 - 0.004),
        p1=(TOP_NECK_RADIUS, h2 - 0.001),
        p2=(TOP_RIM_RADIUS - 0.0005, h2),
        p3=(TOP_RIM_RADIUS - 0.0005, h2),
        num_points=15
    )
    
    # Inner rim lip (going down and in)
    p_rim_inner = evaluate_bezier_2d(
        p0=(TOP_RIM_RADIUS - 0.0005, h2),
        p1=(TOP_RIM_RADIUS - 0.0020, h2 - 0.0005),
        p2=(0.0265, h2 - 0.0015),
        p3=(0.0262, h2 - 0.0015),
        num_points=15
    )
    
    # --- 8. Lid Groove (Countersink) ---
    # U-shaped groove at outer edge of top lid
    p_groove = evaluate_bezier_2d(
        p0=(0.0262, h2 - 0.0015),
        p1=(0.0262, h2 - 0.0045),
        p2=(0.0240, h2 - 0.0045),
        p3=(TOP_LID_RADIUS - 0.0002, h2 - 0.0035),
        num_points=20
    )
    
    # --- 9. Recessed Top Lid ---
    # Shallow dome-like surface ending at the center R=0
    p_lid = evaluate_bezier_2d(
        p0=(TOP_LID_RADIUS - 0.0002, h2 - 0.0035),
        p1=(0.015, h2 - 0.0035),
        p2=(0.008, h2 - 0.0030),
        p3=(0.0, h2 - 0.0030),
        num_points=20
    )
    
    # Concatenate all profile segments (skipping duplicate joints)
    profile = np.concatenate([
        p_dome,
        p_rim_bottom[1:],
        p_bottom_taper[1:],
        p_body[1:],
        p_top_shoulder[1:],
        p_neck[1:],
        p_rim_outer[1:],
        p_rim_inner[1:],
        p_groove[1:],
        p_lid[1:]
    ], axis=0)
    
    return profile

def generate_can_mesh(
    angular_res: int = DEFAULT_ANGULAR_RESOLUTION,
    vertical_res: int = DEFAULT_VERTICAL_RESOLUTION
) -> o3d.geometry.TriangleMesh:
    """
    Generates a single continuous watertight mesh of the Coke can body by revolving
    the resampled profile curve.
    """
    raw_profile = generate_can_profile()
    
    # Calculate cumulative arc-length of the profile curve
    diffs = np.diff(raw_profile, axis=0)
    lens = np.sqrt(np.sum(diffs**2, axis=1))
    arc_length = np.concatenate(([0.0], np.cumsum(lens)))
    
    # Resample the profile uniformly along its arc length for smooth triangle layout
    s_new = np.linspace(0.0, arc_length[-1], vertical_res)
    r_resampled = np.interp(s_new, arc_length, raw_profile[:, 0])
    z_resampled = np.interp(s_new, arc_length, raw_profile[:, 1])
    profile = np.column_stack((r_resampled, z_resampled))
    
    vertices = []
    colors = []
    
    # Generate revolved vertices and vertex colors (procedurally textured)
    h2 = CAN_HEIGHT / 2.0
    for i in range(vertical_res):
        R, z = profile[i]
        
        # Determine Ambient Occlusion factor
        ao = 1.0
        if z < -h2 + 0.012 and R < 0.024:  # Inside bottom dome
            # Darker at the deepest center
            ao = 0.5 + 0.5 * (R / 0.024)
        elif z > h2 - 0.006 and R < 0.027:  # Lid and groove
            if R > 0.0245 and R < 0.0265:    # Deepest part of groove
                ao = 0.4
            else:
                ao = 0.75 + 0.25 * (R / TOP_LID_RADIUS)
        
        for j in range(angular_res):
            theta = j * (2 * np.pi / angular_res)
            x = R * np.cos(theta)
            y = R * np.sin(theta)
            
            # Procedural brushed aluminum texture: high-frequency circumferential variation
            brush = 0.025 * np.sin(200 * theta) + 0.012 * np.cos(450 * theta) + 0.005 * np.sin(900 * theta)
            
            # Aluminum base color
            col_r = clamp(ALUMINUM_BASE_COLOR[0] * ao + brush, 0.0, 1.0)
            col_g = clamp(ALUMINUM_BASE_COLOR[1] * ao + brush, 0.0, 1.0)
            col_b = clamp(ALUMINUM_BASE_COLOR[2] * ao + brush, 0.0, 1.0)
            
            # Make the very bottom rim slightly darker/brushed
            if z < -h2 + 0.001:
                col_r *= 0.85
                col_g *= 0.85
                col_b *= 0.85
                
            vertices.append([x, y, z])
            colors.append([col_r, col_g, col_b])
            
    vertices = np.array(vertices, dtype=np.float64)
    colors = np.array(colors, dtype=np.float64)
    
    # Generate Triangles
    triangles = []
    for i in range(vertical_res - 1):
        for j in range(angular_res):
            v00 = i * angular_res + j
            v01 = i * angular_res + (j + 1) % angular_res
            v10 = (i + 1) * angular_res + j
            v11 = (i + 1) * angular_res + (j + 1) % angular_res
            
            # Outer winding order
            triangles.append([v00, v01, v10])
            triangles.append([v10, v01, v11])
            
    triangles = np.array(triangles, dtype=np.int32)
    
    # Create Open3D mesh
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    
    # Clean up duplicate vertices at the poles (R=0) and fix geometry
    mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles()
    mesh.remove_degenerate_triangles()
    mesh.compute_vertex_normals()
    
    return mesh

def generate_pull_tab_mesh() -> o3d.geometry.TriangleMesh:
    """
    Procedurally generates a watertight 3D pull tab with a finger hole.
    Returns:
        o3d.geometry.TriangleMesh
    """
    K = 40  # Resolution of loops
    thickness = 0.0005  # 0.5 mm
    
    # Build 2D loops
    outer_pts = []
    inner_pts = []
    
    for k in range(K):
        t = k * (2 * np.pi / K)
        
        # Capsule outer boundary
        if -np.pi/2 <= t < np.pi/2:
            x_out = 0.009 + 0.0065 * np.cos(t)
            y_out = 0.0065 * np.sin(t)
        else:
            x_out = -0.005 + 0.0065 * np.cos(t)
            y_out = 0.0065 * np.sin(t)
            
        # Circular finger hole in the back portion
        x_in = 0.004 + 0.0038 * np.cos(t)
        y_in = 0.0038 * np.sin(t)
        
        outer_pts.append((x_out, y_out))
        inner_pts.append((x_in, y_in))
        
    outer_pts = np.array(outer_pts)
    inner_pts = np.array(inner_pts)
    
    vertices = []
    colors = []
    
    # Top and Bottom Z offsets
    z_top = thickness / 2.0
    z_bot = -thickness / 2.0
    
    # Layout order:
    # 0 -> K-1: Top Outer
    # K -> 2K-1: Top Inner
    # 2K -> 3K-1: Bottom Outer
    # 3K -> 4K-1: Bottom Inner
    
    for pt in outer_pts:
        vertices.append([pt[0], pt[1], z_top])
        colors.append([0.88, 0.88, 0.88])
    for pt in inner_pts:
        vertices.append([pt[0], pt[1], z_top])
        colors.append([0.88, 0.88, 0.88])
    for pt in outer_pts:
        vertices.append([pt[0], pt[1], z_bot])
        colors.append([0.80, 0.80, 0.80])  # slightly darker bottom
    for pt in inner_pts:
        vertices.append([pt[0], pt[1], z_bot])
        colors.append([0.80, 0.80, 0.80])
        
    vertices = np.array(vertices, dtype=np.float64)
    colors = np.array(colors, dtype=np.float64)
    
    triangles = []
    
    # Index functions
    def v_top_out(idx): return idx
    def v_top_in(idx): return K + idx
    def v_bot_out(idx): return 2 * K + idx
    def v_bot_in(idx): return 3 * K + idx
    
    # Triangulate top face (faces +Z)
    for k in range(K):
        k_next = (k + 1) % K
        triangles.append([v_top_out(k), v_top_out(k_next), v_top_in(k)])
        triangles.append([v_top_in(k), v_top_out(k_next), v_top_in(k_next)])
        
    # Triangulate bottom face (faces -Z)
    for k in range(K):
        k_next = (k + 1) % K
        triangles.append([v_bot_out(k), v_bot_in(k), v_bot_out(k_next)])
        triangles.append([v_bot_in(k), v_bot_in(k_next), v_bot_out(k_next)])
        
    # Triangulate outer wall (faces outwards)
    for k in range(K):
        k_next = (k + 1) % K
        triangles.append([v_top_out(k), v_bot_out(k), v_top_out(k_next)])
        triangles.append([v_top_out(k_next), v_bot_out(k), v_bot_out(k_next)])
        
    # Triangulate inner wall (faces inwards)
    for k in range(K):
        k_next = (k + 1) % K
        triangles.append([v_top_in(k), v_top_in(k_next), v_bot_in(k)])
        triangles.append([v_top_in(k_next), v_bot_in(k_next), v_bot_in(k)])
        
    triangles = np.array(triangles, dtype=np.int32)
    
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    
    mesh.compute_vertex_normals()
    
    # Create the center attachment rivet
    # Rivet sits at the solid front part: x = -0.005
    rivet = o3d.geometry.TriangleMesh.create_cylinder(radius=0.0012, height=thickness * 2.0)
    rivet.translate([-0.005, 0.0, 0.0])
    
    # Give the rivet the same color
    rivet_colors = np.full((len(rivet.vertices), 3), 0.85)
    rivet.vertex_colors = o3d.utility.Vector3dVector(rivet_colors)
    
    # Merge tab and rivet
    pull_tab = mesh + rivet
    pull_tab.compute_vertex_normals()
    
    # Position the pull tab on the lid:
    # Lid recessed flat area is at z = CAN_HEIGHT / 2 - 0.003
    z_lid = (CAN_HEIGHT / 2.0) - 0.003
    pull_tab.translate([0.0, 0.0, z_lid])
    
    return pull_tab

def generate_digital_twin() -> o3d.geometry.TriangleMesh:
    """
    Generates and combines the can body and the pull tab into a single
    complete digital twin mesh.
    """
    can_body = generate_can_mesh()
    pull_tab = generate_pull_tab_mesh()
    
    # Combine meshes
    digital_twin = can_body + pull_tab
    digital_twin.compute_vertex_normals()
    return digital_twin

def clamp(val: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(val, max_val))
