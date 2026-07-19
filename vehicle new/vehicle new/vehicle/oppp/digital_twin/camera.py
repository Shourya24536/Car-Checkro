"""
Camera module simulating an inspection rig.
Provides projection matrices, 3D-to-2D point projection, camera frustum mesh,
and a pose estimation (PnP) solver with fallback.
"""
import numpy as np
import open3d as o3d
from typing import Tuple, List, Optional

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

class InspectionCamera:
    """
    Simulates a physical inspection camera positioned around the can.
    """
    def __init__(
        self,
        name: str,
        position: Tuple[float, float, float],
        lookat: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        up: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        fov: float = 45.0,
        width: int = 1920,
        height: int = 1080
    ):
        self.name = name
        self.position = np.array(position, dtype=np.float64)
        self.lookat = np.array(lookat, dtype=np.float64)
        self.up = np.array(up, dtype=np.float64)
        self.fov = fov
        self.width = width
        self.height = height
        
        # Cache matrices
        self.R, self.t = self._compute_extrinsic()
        self.K = self._compute_intrinsic()

    def _compute_extrinsic(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the rotation R (3x3) and translation t (3,) for the camera.
        Adheres to Computer Vision standards (Z-axis forward, X right, Y down).
        """
        z_c = self.lookat - self.position
        z_c = z_c / np.linalg.norm(z_c)
        
        # Right vector
        x_c = np.cross(z_c, self.up)
        x_c = x_c / np.linalg.norm(x_c)
        
        # Recomputed Orthogonal Up vector (points upwards)
        y_c_up = np.cross(x_c, z_c)
        
        # OpenCV convention: Y-axis points down
        y_c = -y_c_up
        
        # Rotation matrix (World to Camera coordinates)
        R = np.vstack([x_c, y_c, z_c])  # Shape (3, 3)
        t = -R @ self.position          # Shape (3,)
        
        return R, t

    def _compute_intrinsic(self) -> np.ndarray:
        """
        Computes the 3x3 camera intrinsic matrix K.
        """
        fov_rad = np.radians(self.fov)
        f_val = (self.height / 2.0) / np.tan(fov_rad / 2.0)
        
        cx = self.width / 2.0
        cy = self.height / 2.0
        
        K = np.array([
            [f_val, 0.0,   cx],
            [0.0,   f_val, cy],
            [0.0,   0.0,   1.0]
        ], dtype=np.float64)
        
        return K

    def project_point(self, pt_3d: np.ndarray) -> Optional[np.ndarray]:
        """
        Projects a 3D world space coordinate into 2D pixel coordinates.
        Returns None if the point lies behind the camera.
        """
        pt_cam = self.R @ pt_3d + self.t
        z_c = pt_cam[2]
        
        if z_c <= 1e-5:
            return None  # Point is behind camera
            
        pt_pixel_hom = self.K @ pt_cam
        u = pt_pixel_hom[0] / pt_pixel_hom[2]
        v = pt_pixel_hom[1] / pt_pixel_hom[2]
        
        # Check if coordinates are in image bounds
        if 0 <= u < self.width and 0 <= v < self.height:
            return np.array([u, v], dtype=np.float64)
        return None

    def solve_pnp(self, pts_3d: np.ndarray, pts_2d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Solves Perspective-n-Point (PnP) pose estimation.
        Finds rotation and translation vector mapping 3D to 2D correspondences.
        """
        if OPENCV_AVAILABLE:
            success, rvec, tvec = cv2.solvePnP(
                pts_3d.astype(np.float32),
                pts_2d.astype(np.float32),
                self.K.astype(np.float32),
                None,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
            if success:
                R_est, _ = cv2.Rodrigues(rvec)
                return R_est, tvec.flatten()
                
        # Pure NumPy Direct Linear Transform (DLT) fallback if OpenCV is missing
        # Requires at least 6 points
        n = len(pts_3d)
        if n < 6:
            # Fallback to current pose if points are insufficient
            return self.R, self.t
            
        A = []
        for i in range(n):
            X, Y, Z = pts_3d[i]
            u, v = pts_2d[i]
            
            # Normalize pixel coords with intrinsics inverse
            u_norm = (u - self.K[0, 2]) / self.K[0, 0]
            v_norm = (v - self.K[1, 2]) / self.K[1, 1]
            
            A.append([X, Y, Z, 1.0, 0.0, 0.0, 0.0, 0.0, -u_norm*X, -u_norm*Y, -u_norm*Z, -u_norm])
            A.append([0.0, 0.0, 0.0, 0.0, X, Y, Z, 1.0, -v_norm*X, -v_norm*Y, -v_norm*Z, -v_norm])
            
        A = np.array(A)
        _, _, Vh = np.linalg.svd(A)
        P_flat = Vh[-1]
        P = P_flat.reshape(3, 4)
        
        # Decompose P = [R | t] since we normalized pixel coordinates
        R_est = P[:, :3]
        t_est = P[:, 3]
        
        # Enforce orthogonality of R
        U_r, _, Vh_r = np.linalg.svd(R_est)
        R_ortho = U_r @ Vh_r
        
        # Ensure positive determinant
        if np.linalg.det(R_ortho) < 0:
            R_ortho = -R_ortho
            t_est = -t_est
            
        return R_ortho, t_est

    def generate_frustum_geometry(self, scale: float = 0.02) -> o3d.geometry.LineSet:
        """
        Generates a 3D visual line geometry representing the camera frustum.
        """
        # Define frustum corners in camera space
        # Near plane corners (z = scale)
        fov_rad = np.radians(self.fov)
        aspect = self.width / self.height
        h_near = scale * np.tan(fov_rad / 2.0)
        w_near = h_near * aspect
        
        # 5 points in camera space: center origin, and 4 corner points at near plane
        pts_cam = np.array([
            [0.0, 0.0, 0.0],          # 0: origin
            [-w_near, -h_near, scale], # 1: top-left
            [w_near, -h_near, scale],  # 2: top-right
            [w_near, h_near, scale],   # 3: bottom-right
            [-w_near, h_near, scale]   # 4: bottom-left
        ])
        
        # Transform points to world space: X_w = R^T * (X_c - t)
        R_T = self.R.T
        pts_world = []
        for pt in pts_cam:
            pt_w = R_T @ (pt - self.t)
            pts_world.append(pt_w)
            
        pts_world = np.array(pts_world)
        
        # Define frustum lines connecting corners
        lines = [
            [0, 1], [0, 2], [0, 3], [0, 4], # lines from camera origin to corners
            [1, 2], [2, 3], [3, 4], [4, 1]  # rectangular boundary
        ]
        
        line_set = o3d.geometry.LineSet()
        line_set.points = o3d.utility.Vector3dVector(pts_world)
        line_set.lines = o3d.utility.Vector2iVector(lines)
        
        # Color the lines green
        colors = [[0.0, 0.9, 0.1] for _ in range(len(lines))]
        line_set.colors = o3d.utility.Vector3dVector(colors)
        
        return line_set
