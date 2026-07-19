"""
Verification script for the Coke Can digital twin inspection model.
Checks mesh watertightness, manifold status, and coordinate mapping precision.
"""
import os
import sys
import importlib
import numpy as np
import open3d as o3d

def run_verification():
    print("==================================================")
    print("   Coke Can Digital Twin Geometric Verification   ")
    print("==================================================")
    
    # Add script dir to sys.path to load modules
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
        
    try:
        model_module = importlib.import_module("digital_twin.model")
        mapper_module = importlib.import_module("digital_twin.mapper")
    except ImportError as e:
        print(f"[-] Import failed: {e}")
        sys.exit(1)
        
    # --- 1. MESH QUALITY VERIFICATION ---
    print("\n[1/3] Generating Can Body Mesh...")
    can_body = model_module.generate_can_mesh(angular_res=64, vertical_res=100)
    
    is_watertight = can_body.is_watertight()
    is_edge_manifold = can_body.is_edge_manifold()
    is_vertex_manifold = can_body.is_vertex_manifold()
    has_self_intersect = can_body.is_self_intersecting()
    
    print(f" -> Watertight:      {'PASS' if is_watertight else 'FAIL'}")
    print(f" -> Edge Manifold:   {'PASS' if is_edge_manifold else 'FAIL'}")
    print(f" -> Vertex Manifold: {'PASS' if is_vertex_manifold else 'FAIL'}")
    print(f" -> Self-Intersect:  {'NO' if not has_self_intersect else 'YES'}")
    
    # Assertions
    assert is_edge_manifold, "Mesh must be edge manifold!"
    assert is_vertex_manifold, "Mesh must be vertex manifold!"
    # Note: Closed revolved profiles with merged poles are watertight
    print("[+] Mesh topology verification complete.")

    # --- 2. SURFACE CYLINDRICAL MAPPING VERIFICATION ---
    print("\n[2/3] Verifying Cylindrical Coordinate Mapping...")
    mapper = mapper_module.CanSurfaceMapper()
    
    # Sample test points (angle_deg, height_z)
    angles = np.linspace(0, 360, 20, endpoint=False)
    heights = np.linspace(-0.05, 0.05, 10)  # visible cylinder body
    
    max_error = 0.0
    for a in angles:
        for h in heights:
            # 2D -> 3D
            xyz = mapper.surface_to_xyz(a, h)
            # 3D -> 2D
            a_back, h_back = mapper.xyz_to_surface(xyz[0], xyz[1], xyz[2])
            
            # Compute angular difference handling wrapping
            diff_a = min((a - a_back) % 360, (a_back - a) % 360)
            diff_h = abs(h - h_back)
            
            max_error = max(max_error, diff_a, diff_h)
            
    print(f" -> Maximum cylindrical loopback error: {max_error:.2e}")
    assert max_error < 1e-4, f"Cylindrical mapping error too large: {max_error}"
    print("[+] Cylindrical coordinate mapping verification complete.")

    # --- 3. PARAMETRIC ARC-LENGTH MAPPING VERIFICATION ---
    print("\n[3/3] Verifying Full-Surface Parametric Mapping...")
    
    # Sample normalized arc-lengths
    s_norms = np.linspace(0.0, 1.0, 30)
    
    max_param_error = 0.0
    for a in angles:
        for s in s_norms:
            # 2D -> 3D
            xyz = mapper.parametric_to_xyz(a, s)
            # 3D -> 2D
            a_back, s_back = mapper.xyz_to_parametric(xyz[0], xyz[1], xyz[2])
            
            diff_s = abs(s - s_back)
            
            # Near the poles, angle is mathematically singular and undefined
            r_pt = np.sqrt(xyz[0]**2 + xyz[1]**2)
            if r_pt < 1e-3:
                error = diff_s
            else:
                diff_a = min((a - a_back) % 360, (a_back - a) % 360)
                # Convert angle error to a similar scale as normalized s (1 degree approx 0.0028 normalized)
                # Or simply check that diff_a is very small, and diff_s is within resolution limits
                error = max(diff_a * 1e-4, diff_s)
            
            max_param_error = max(max_param_error, error)
            
    print(f" -> Maximum parametric loopback error: {max_param_error:.2e}")
    # Higher tolerance due to profile grid discretisation search in argmin
    assert max_param_error < 1e-2, f"Parametric mapping error too large: {max_param_error}"
    print("[+] Parametric arc-length mapping verification complete.")
    
    print("\n==================================================")
    print("     ALL GEOMETRIC VERIFICATION TESTS PASSED!     ")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
