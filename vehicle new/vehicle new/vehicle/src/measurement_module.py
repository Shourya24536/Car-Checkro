import cv2
import numpy as np
import os
from PIL import Image

class MeasurementModule:
    """
    Computes physical metric measurements (mm, mm², severity) for scratches and dents
    and extracts high-resolution zoomed crops for inspection reports.
    """
    def __init__(self, px_to_mm=0.2):
        """
        Args:
            px_to_mm: Calibration factor mapping 1 pixel to millimeters.
        """
        self.px_to_mm = px_to_mm
        
        # Temp folder inside workspace to save crops for PDF inclusion
        self.crops_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "crops")
        os.makedirs(self.crops_dir, exist_ok=True)

    def extract_crop(self, frame, bbox, defect_id, padding=15) -> str:
        """
        Crops a defect from the frame with padding.
        Saves it to the output folder and returns the file path.
        """
        h_img, w_img = frame.shape[:2]
        x1, y1, x2, y2 = [int(val) for val in bbox]
        
        # Add padding
        x1_pad = max(0, x1 - padding)
        y1_pad = max(0, y1 - padding)
        x2_pad = min(w_img, x2 + padding)
        y2_pad = min(h_img, y2 + padding)
        
        crop = frame[y1_pad:y2_pad, x1_pad:x2_pad]
        if crop.size == 0:
            crop = np.zeros((64, 64, 3), dtype=np.uint8)
            
        filename = f"crop_{defect_id}.jpg"
        filepath = os.path.join(self.crops_dir, filename)
        cv2.imwrite(filepath, crop)
        return filepath

    def measure_scratch(self, frame, mask_poly, bbox, defect_id) -> dict:
        """
        Measures scratch metrics: length (mm), width (mm), area (mm²), orientation, and centroid.
        """
        if not mask_poly:
            # Fallback to bbox if mask is unavailable
            x1, y1, x2, y2 = bbox
            length_px = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            width_px = 3.0 # assumed average width
            area_px = length_px * width_px
            angle = np.degrees(np.arctan2(y2-y1, x2-x1))
            centroid = [(x1+x2)/2, (y1+y2)/2]
        else:
            contour = np.array(mask_poly, dtype=np.int32)
            # Find minimum area rectangle
            rect = cv2.minAreaRect(contour)
            (cx, cy), (w_rect, h_rect), angle = rect
            
            length_px = max(w_rect, h_rect)
            width_px = min(w_rect, h_rect)
            if width_px == 0:
                width_px = 1.0 # avoid division by zero
                
            area_px = cv2.contourArea(contour)
            if area_px == 0:
                area_px = length_px * width_px
                
            centroid = [float(cx), float(cy)]

        # Convert to mm
        length_mm = length_px * self.px_to_mm
        width_mm = width_px * self.px_to_mm
        area_mm2 = area_px * (self.px_to_mm ** 2)
        
        # Save crop
        crop_path = self.extract_crop(frame, bbox, defect_id)

        return {
            "length_mm": float(round(length_mm, 2)),
            "width_mm": float(round(width_mm, 2)),
            "area_mm2": float(round(area_mm2, 2)),
            "orientation_deg": float(round(angle, 1)),
            "centroid": [float(val) for val in centroid],
            "crop_path": crop_path
        }

    def measure_dent(self, frame, bbox, defect_id) -> dict:
        """
        Measures dent metrics: diameter (mm), area (mm²), estimated depth (mm), and severity.
        """
        x1, y1, x2, y2 = [int(val) for val in bbox]
        w_px = x2 - x1
        h_px = y2 - y1
        
        # Diameter in pixels as average bbox size
        diameter_px = (w_px + h_px) / 2.0
        diameter_mm = diameter_px * self.px_to_mm
        
        # Area in mm² (approximated as circle)
        area_mm2 = np.pi * ((diameter_mm / 2.0) ** 2)
        
        # Estimate depth based on contrast std-dev inside crop
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        crop_gray = gray[y1:y2, x1:x2]
        if crop_gray.size > 0:
            contrast = crop_gray.std()
        else:
            contrast = 0.0
            
        # Shading contrast scales to physical depth in mm (e.g. 0.5 mm to 3 mm)
        depth_mm = contrast * 0.06
        if depth_mm < 0.2:
            depth_mm = 0.2 # minimum resolution
            
        # Determine Severity
        if depth_mm >= 2.0 or diameter_mm >= 10.0:
            severity = "Critical"
        elif depth_mm >= 1.0 or diameter_mm >= 5.0:
            severity = "Major"
        else:
            severity = "Minor"
            
        # Save crop
        crop_path = self.extract_crop(frame, bbox, defect_id)

        return {
            "diameter_mm": float(round(diameter_mm, 2)),
            "area_mm2": float(round(area_mm2, 2)),
            "depth_mm": float(round(depth_mm, 2)),
            "severity": severity,
            "crop_path": crop_path
        }
