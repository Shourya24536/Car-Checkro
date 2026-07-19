# Mock Simulation client to test AI PC HTTP Receiver Node
import os
import json
import requests
import numpy as np
import cv2

# Port from config
PORT = 8000
URL = f"http://127.0.0.1:{PORT}/api/v1/inspection"

def create_dummy_image(text: str, size: tuple = (640, 480), color: tuple = (50, 50, 50)) -> str:
    """Generates a dummy JPG frame with a text banner and returns its filepath."""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    # Fill background color
    img[:] = color
    # Add text banner
    cv2.putText(img, text, (int(size[0]*0.1), int(size[1]*0.5)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    filename = f"temp_dummy_{text.lower().replace(' ', '_')}.jpg"
    cv2.imwrite(filename, img)
    return filename

def run_simulation():
    print("==================================================")
    print("      UNO Q Edge Simulation POST Request          ")
    print("==================================================")
    
    # 1. Create dummy files
    print("Creating dummy camera frames and defect crops...")
    cam1_file = create_dummy_image("Camera 1 (Top-Right View) - Sim Can", (640, 480), (60, 40, 40))
    cam2_file = create_dummy_image("Camera 2 (Top-Left View) - Sim Can", (640, 480), (40, 60, 40))
    crop_scr = create_dummy_image("SCR_001 Crop", (128, 128), (0, 118, 255))
    crop_dent1 = create_dummy_image("DENT_001 Crop", (128, 128), (221, 11, 18))
    crop_dent2 = create_dummy_image("DENT_002 Crop (Duplicate)", (128, 128), (221, 11, 18))

    # 2. Define payload JSON metadata matching version 1.0 schema
    # DENT_001 and DENT_002 are spatially close (angles 120 and 122, height 0.030 and 0.031)
    # and should be fused by the DefectTracker.
    metadata = {
        "version": "1.0",
        "request_id": "req_sim_hackathon_99",
        "inspection_id": "INSPECT_20260719_SIMULATED",
        "timestamp": "2026-07-19 04:35:12",
        "status": "FAIL",
        "confidence": 0.94,
        "processing_time": 0.42,
        "scratches": [
            {
                "id": "SCR_001",
                "length_mm": 15.4,
                "width_mm": 0.65,
                "area_mm2": 10.0,
                "angle": 45.0,
                "confidence": 0.91,
                "camera_id": "Camera_1",
                "height": -0.02
            }
        ],
        "dents": [
            {
                "id": "DENT_001",
                "diameter_mm": 7.8,
                "depth_mm": 1.62,
                "area_mm2": 47.8,
                "angle": 120.0,
                "confidence": 0.95,
                "camera_id": "Camera_1",
                "height": 0.030,
                "severity": "Major"
            },
            {
                "id": "DENT_002",
                "diameter_mm": 8.2,
                "depth_mm": 1.74,
                "area_mm2": 52.8,
                "angle": 122.0,
                "confidence": 0.89,
                "camera_id": "Camera_2",
                "height": 0.031,
                "severity": "Major"
            }
        ]
    }

    # 3. Compile multipart form data
    form_data = {
        "metadata": json.dumps(metadata)
    }

    files = {
        "camera_1_frame": (os.path.basename(cam1_file), open(cam1_file, "rb"), "image/jpeg"),
        "camera_2_frame": (os.path.basename(cam2_file), open(cam2_file, "rb"), "image/jpeg"),
        "crop_SCR_001": (os.path.basename(crop_scr), open(crop_scr, "rb"), "image/jpeg"),
        "crop_DENT_001": (os.path.basename(crop_dent1), open(crop_dent1, "rb"), "image/jpeg"),
        "crop_DENT_002": (os.path.basename(crop_dent2), open(crop_dent2, "rb"), "image/jpeg")
    }

    print(f"Sending POST request to {URL}...")
    try:
        res = requests.post(URL, data=form_data, files=files)
        print(f"Response status: {res.status_code}")
        print("Response JSON:")
        print(json.dumps(res.json(), indent=4))
    except Exception as e:
        print(f"Connection failure: {e}")
    finally:
        # Close open file descriptors
        for f in files.values():
            f[1].close()
        
        # 4. Clean up temporary local files
        print("Cleaning up temporary local files...")
        for temp_f in [cam1_file, cam2_file, crop_scr, crop_dent1, crop_dent2]:
            if os.path.exists(temp_f):
                os.remove(temp_f)
    print("Simulation complete.")

if __name__ == "__main__":
    run_simulation()
