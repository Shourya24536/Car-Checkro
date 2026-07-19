# Pure function data fusion utility to merge duplicate camera observations
import math
import numpy as np
from typing import List, Tuple, Dict, Any

# Can cylinder constants
CAN_HEIGHT = 0.115
CAN_BODY_RADIUS = 0.033

class DefectTracker:
    """
    Performs data fusion on scratch and dent observations.
    Merges duplicate detections that are spatially close on the 3D cylinder surface.
    """
    def __init__(self, match_threshold_m: float = 0.015):
        self.match_threshold_m = match_threshold_m

    def compute_surface_distance(self, angle1: float, height1: float, angle2: float, height2: float) -> float:
        """
        Computes geodesic/Euclidean distance on the surface of the cylinder.
        """
        d_angle = min(abs(angle1 - angle2), 360.0 - abs(angle1 - angle2))
        d_angle_m = CAN_BODY_RADIUS * math.radians(d_angle)
        d_height_m = abs(height1 - height2)
        return float(math.sqrt(d_angle_m**2 + d_height_m**2))

    def fuse_observations(self, scratches: List[Dict[str, Any]], dents: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fuses duplicate scratches and dents based on 3D spatial proximity.
        Returns a tuple of (fused_scratches, fused_dents).
        """
        fused_scratches = self._fuse_type(scratches, "scratch")
        fused_dents = self._fuse_type(dents, "dent")
        return fused_scratches, fused_dents

    def _fuse_type(self, defects: List[Dict[str, Any]], defect_type: str) -> List[Dict[str, Any]]:
        if not defects:
            return []

        merged = []
        visited = [False] * len(defects)

        for i in range(len(defects)):
            if visited[i]:
                continue

            # Start a cluster
            cluster = [defects[i]]
            visited[i] = True

            for j in range(i + 1, len(defects)):
                if visited[j]:
                    continue

                # Check proximity
                dist = self.compute_surface_distance(
                    defects[i]["angle"], defects[i]["height"],
                    defects[j]["angle"], defects[j]["height"]
                )

                if dist < self.match_threshold_m:
                    cluster.append(defects[j])
                    visited[j] = True

            # Merge the cluster into a single defect record
            if len(cluster) == 1:
                merged.append(cluster[0])
            else:
                merged.append(self._merge_cluster(cluster, defect_type))

        return merged

    def _merge_cluster(self, cluster: List[Dict[str, Any]], defect_type: str) -> Dict[str, Any]:
        """
        Combines multiple duplicate observations into a single representative defect.
        """
        # Average coordinates
        angles = [d["angle"] for d in cluster]
        heights = [d["height"] for d in cluster]
        
        # Handle angular wrap-around mean
        sin_sum = sum(math.sin(math.radians(a)) for a in angles)
        cos_sum = sum(math.cos(math.radians(a)) for a in angles)
        avg_angle = math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0
        avg_height = sum(heights) / len(heights)

        # Take max confidence
        max_conf = max(d.get("confidence", 0.0) for d in cluster)

        # Merge camera sources
        cams = []
        for d in cluster:
            cam = d.get("camera_id", "N/A")
            if cam not in cams:
                cams.append(cam)
        merged_cams = " + ".join(cams)

        # Keep crop path of the highest confidence detection
        best_crop = None
        highest_conf = -1.0
        for d in cluster:
            conf = d.get("confidence", 0.0)
            if conf > highest_conf:
                highest_conf = conf
                best_crop = d.get("crop_path")

        # Base merged dictionary
        merged_defect = {
            "id": cluster[0]["id"], # Keep original ID of the first observer
            "type": defect_type,
            "angle": float(round(avg_angle, 1)),
            "height": float(round(avg_height, 4)),
            "confidence": float(round(max_conf, 2)),
            "camera_id": merged_cams,
            "crop_path": best_crop
        }

        # Merge physical dimensions
        if defect_type == "dent":
            merged_defect["diameter_mm"] = max(d.get("diameter_mm", 0.0) for d in cluster)
            merged_defect["depth_mm"] = max(d.get("depth_mm", 0.0) for d in cluster)
            merged_defect["area_mm2"] = max(d.get("area_mm2", 0.0) for d in cluster)
            
            # Severity (take worst-case)
            severities = [d.get("severity", "Minor") for d in cluster]
            if "Critical" in severities:
                merged_defect["severity"] = "Critical"
            elif "Major" in severities:
                merged_defect["severity"] = "Major"
            else:
                merged_defect["severity"] = "Minor"
        else:
            merged_defect["length_mm"] = max(d.get("length_mm", 0.0) for d in cluster)
            merged_defect["width_mm"] = max(d.get("width_mm", 0.0) for d in cluster)
            merged_defect["area_mm2"] = max(d.get("area_mm2", 0.0) for d in cluster)

        return merged_defect
