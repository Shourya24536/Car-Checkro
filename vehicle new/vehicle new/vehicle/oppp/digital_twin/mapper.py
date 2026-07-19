"""
Coordinate mapping module for mapping inspection defects between 2D (angle, height)
and 3D (x, y, z) digital twin space.
"""
import numpy as np
from typing import Tuple
from .config import (
    CAN_HEIGHT, CAN_BODY_RADIUS, BOTTOM_RIM_RADIUS,
    TOP_NECK_RADIUS, TOP_RIM_RADIUS
)
from .model import generate_can_profile

class CanSurfaceMapper:
    """
    Handles coordinate mappings between:
    - 2D Cylindrical coordinates: (angle in degrees [0, 360), height_z in meters [-H/2, H/2])
    - 3D Cartesian coordinates: (x, y, z) in meters
    - Parametric Profile coordinates: (angle in degrees [0, 360), s_norm in [0, 1])
    """
    def __init__(self):
        # Generate and cache the 2D profile curve for parametric mapping
        self.raw_profile = generate_can_profile()
        
        # Calculate profile arc-lengths
        diffs = np.diff(self.raw_profile, axis=0)
        lens = np.sqrt(np.sum(diffs**2, axis=1))
        self.s_profile = np.concatenate(([0.0], np.cumsum(lens)))
        self.s_max = self.s_profile[-1]
        self.s_norm_profile = self.s_profile / self.s_max

    def get_outer_radius_at_z(self, z: float) -> float:
        """
        Calculates the outer radius of the can at a given Z height.
        This represents the visible outer profile of the can cylinder and shoulders.
        """
        h2 = CAN_HEIGHT / 2.0
        z_clamped = np.clip(z, -h2, h2)
        
        # Bottom taper region (starts at z = -h2, ends at z = -h2 + 0.015)
        if z_clamped < -h2 + 0.015:
            t = (z_clamped - (-h2)) / 0.015
            t_smooth = 3 * t**2 - 2 * t**3  # smoothstep interpolation
            return BOTTOM_RIM_RADIUS + (CAN_BODY_RADIUS - BOTTOM_RIM_RADIUS) * t_smooth
            
        # Main cylinder body (z = -h2 + 0.015 to z = h2 - 0.018)
        elif z_clamped <= h2 - 0.018:
            return CAN_BODY_RADIUS
            
        # Top shoulder taper (z = h2 - 0.018 to z = h2 - 0.006)
        elif z_clamped <= h2 - 0.006:
            t = (z_clamped - (h2 - 0.018)) / 0.012
            t_smooth = 3 * t**2 - 2 * t**3
            return CAN_BODY_RADIUS + (TOP_NECK_RADIUS - CAN_BODY_RADIUS) * t_smooth
            
        # Neck and rolled rim (z = h2 - 0.006 to z = h2)
        else:
            t = (z_clamped - (h2 - 0.006)) / 0.006
            t_smooth = 3 * t**2 - 2 * t**3
            return TOP_NECK_RADIUS + (TOP_RIM_RADIUS - TOP_NECK_RADIUS) * t_smooth

    def surface_to_xyz(self, angle_deg: float, height_z: float) -> np.ndarray:
        """
        Converts 2D surface inspection coordinates to 3D Cartesian coordinates.
        Uses Z-height projection on the outer can body.
        
        Args:
            angle_deg: Rotation angle around Z-axis in degrees [0, 360)
            height_z: Vertical coordinate in meters [-CAN_HEIGHT/2, CAN_HEIGHT/2]
            
        Returns:
            np.ndarray of shape (3,) representing (x, y, z)
        """
        theta = np.radians(angle_deg)
        r = self.get_outer_radius_at_z(height_z)
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        return np.array([x, y, height_z], dtype=np.float64)

    def xyz_to_surface(self, x: float, y: float, z: float) -> Tuple[float, float]:
        """
        Projects any 3D Cartesian coordinate onto the closest outer cylinder surface point.
        
        Args:
            x, y, z: 3D point coordinates in meters
            
        Returns:
            Tuple of (angle_deg, height_z)
        """
        angle_deg = np.degrees(np.arctan2(y, x)) % 360.0
        # Clamp Z to physical can height
        h2 = CAN_HEIGHT / 2.0
        height_z = np.clip(z, -h2, h2)
        return float(angle_deg), float(height_z)

    def parametric_to_xyz(self, angle_deg: float, s_norm: float) -> np.ndarray:
        """
        Full-can bijection mapping using normalized profile arc-length.
        Covers bottom dome, grooves, lid and rim without multi-value ambiguity.
        
        Args:
            angle_deg: Rotation angle around Z-axis in degrees [0, 360)
            s_norm: Normalized distance along profile [0.0 (bottom-center) to 1.0 (top-center)]
            
        Returns:
            np.ndarray of shape (3,) representing (x, y, z)
        """
        s_norm = np.clip(s_norm, 0.0, 1.0)
        theta = np.radians(angle_deg)
        
        # Interpolate profile R and z
        R = np.interp(s_norm, self.s_norm_profile, self.raw_profile[:, 0])
        z = np.interp(s_norm, self.s_norm_profile, self.raw_profile[:, 1])
        
        x = R * np.cos(theta)
        y = R * np.sin(theta)
        return np.array([x, y, z], dtype=np.float64)

    def xyz_to_parametric(self, x: float, y: float, z: float) -> Tuple[float, float]:
        """
        Converts 3D Cartesian coordinates to full-can parametric coordinates (angle, s_norm)
        by finding the closest point on the complete 2D profile curve.
        """
        angle_deg = np.degrees(np.arctan2(y, x)) % 360.0
        r_pt = np.sqrt(x**2 + y**2)
        
        # Find closest point on 2D profile
        dists = (self.raw_profile[:, 0] - r_pt)**2 + (self.raw_profile[:, 1] - z)**2
        idx_min = np.argmin(dists)
        s_norm = float(self.s_norm_profile[idx_min])
        
        return angle_deg, s_norm
