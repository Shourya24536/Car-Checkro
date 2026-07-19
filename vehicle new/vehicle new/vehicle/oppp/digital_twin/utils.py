"""
Utility helpers for geometry generation and vector operations.
"""
import numpy as np
from typing import Tuple, List

def evaluate_bezier_2d(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    num_points: int
) -> np.ndarray:
    """
    Evaluates a cubic Bezier curve in 2D.
    
    Args:
        p0: Starting point (R, z)
        p1: Control point 1 (R, z)
        p2: Control point 2 (R, z)
        p3: Ending point (R, z)
        num_points: Number of points to sample
        
    Returns:
        np.ndarray of shape (num_points, 2) containing (R, z) points.
    """
    t = np.linspace(0.0, 1.0, num_points)[:, np.newaxis]
    
    p0 = np.array(p0)
    p1 = np.array(p1)
    p2 = np.array(p2)
    p3 = np.array(p3)
    
    # Bezier basis functions
    b0 = (1.0 - t) ** 3
    b1 = 3.0 * ((1.0 - t) ** 2) * t
    b2 = 3.0 * (1.0 - t) * (t ** 2)
    b3 = t ** 3
    
    curve = b0 * p0 + b1 * p1 + b2 * p2 + b3 * p3
    return curve

def get_rotation_matrix_x(angle_rad: float) -> np.ndarray:
    """Returns a 3D rotation matrix around X axis."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0, c, -s],
        [0.0, s, c]
    ])

def get_rotation_matrix_y(angle_rad: float) -> np.ndarray:
    """Returns a 3D rotation matrix around Y axis."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [c, 0.0, s],
        [0.0, 1.0, 0.0],
        [-s, 0.0, c]
    ])

def get_rotation_matrix_z(angle_rad: float) -> np.ndarray:
    """Returns a 3D rotation matrix around Z axis."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [c, -s, 0.0],
        [s, c, 0.0],
        [0.0, 0.0, 1.0]
    ])
