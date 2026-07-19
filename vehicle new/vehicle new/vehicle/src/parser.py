# Parser for incoming edge payloads (JSON and multipart attachments)
import json
import uuid
import os
from typing import Dict, Any, Tuple
from werkzeug.utils import secure_filename
from .message_models import InspectionMessage, DentDetail, ScratchDetail
from .config import INSPECTIONS_DIR, CROPS_DIR
from .logger import log_info, log_error, log_warn

def parse_multipart_request(metadata_str: str, files_dict: Dict[str, Any]) -> InspectionMessage:
    """
    Parses multipart request data (JSON metadata string and file attachments).
    Saves uploaded files and returns a populated, immutable InspectionMessage.
    """
    # 1. Parse JSON metadata
    try:
        data = json.loads(metadata_str)
    except Exception as e:
        log_error(f"Failed to parse metadata JSON: {e}")
        raise ValueError("Invalid metadata JSON format.") from e

    # 2. Extract core payload variables and version
    version = data.get("version", "1.0")
    request_id = data.get("request_id", str(uuid.uuid4()))
    inspection_id = data.get("inspection_id", f"INSPECT_{uuid.uuid4().hex[:8]}")
    timestamp = data.get("timestamp", "")
    status = data.get("status", "PASS")
    confidence = float(data.get("confidence", 1.0))
    processing_time = float(data.get("processing_time", 0.0))

    log_info(f"Parsing incoming inspection request: {request_id} (Inspection: {inspection_id}, Version: {version})")

    # 3. Handle file uploads (Camera frames and crop images)
    c1_filename = None
    c2_filename = None

    # Handle full camera frames if uploaded
    if "camera_1_frame" in files_dict:
        file1 = files_dict["camera_1_frame"]
        if file1 and file1.filename != "":
            ext = os.path.splitext(file1.filename)[1]
            safe_name = f"{inspection_id}_camera_1_annotated{ext}"
            filepath = os.path.join(INSPECTIONS_DIR, safe_name)
            file1.save(filepath)
            c1_filename = filepath
            log_info(f"Saved Camera 1 frame to {filepath}")

    if "camera_2_frame" in files_dict:
        file2 = files_dict["camera_2_frame"]
        if file2 and file2.filename != "":
            ext = os.path.splitext(file2.filename)[1]
            safe_name = f"{inspection_id}_camera_2_annotated{ext}"
            filepath = os.path.join(INSPECTIONS_DIR, safe_name)
            file2.save(filepath)
            c2_filename = filepath
            log_info(f"Saved Camera 2 frame to {filepath}")

    # 4. Parse Scratch Detections list
    scratches_list = []
    scratches_raw = data.get("scratches", [])
    for idx, s in enumerate(scratches_raw):
        s_id = s.get("id", f"SCR_{idx}")
        # Look for matching crop file upload in request files
        crop_field = f"crop_{s_id}"
        saved_crop_path = None
        
        if crop_field in files_dict:
            file_crop = files_dict[crop_field]
            if file_crop and file_crop.filename != "":
                c_ext = os.path.splitext(file_crop.filename)[1]
                crop_name = f"crop_{s_id}{c_ext}"
                crop_path = os.path.join(CROPS_DIR, crop_name)
                file_crop.save(crop_path)
                saved_crop_path = crop_path
                log_info(f"Saved crop image for scratch {s_id} to {crop_path}")

        scratch_obj = ScratchDetail(
            id=s_id,
            length_mm=float(s.get("length_mm", 0.0)),
            width_mm=float(s.get("width_mm", 0.0)),
            area_mm2=float(s.get("area_mm2", 0.0)),
            angle=float(s.get("angle", 0.0)),
            confidence=float(s.get("confidence", 0.0)),
            camera_id=s.get("camera_id", "N/A"),
            height=float(s.get("height", 0.0)),
            crop_filename=saved_crop_path
        )
        scratches_list.append(scratch_obj)

    # 5. Parse Dent Detections list
    dents_list = []
    dents_raw = data.get("dents", [])
    for idx, d in enumerate(dents_raw):
        d_id = d.get("id", f"DENT_{idx}")
        # Look for matching crop file upload in request files
        crop_field = f"crop_{d_id}"
        saved_crop_path = None
        
        if crop_field in files_dict:
            file_crop = files_dict[crop_field]
            if file_crop and file_crop.filename != "":
                c_ext = os.path.splitext(file_crop.filename)[1]
                crop_name = f"crop_{d_id}{c_ext}"
                crop_path = os.path.join(CROPS_DIR, crop_name)
                file_crop.save(crop_path)
                saved_crop_path = crop_path
                log_info(f"Saved crop image for dent {d_id} to {crop_path}")

        dent_obj = DentDetail(
            id=d_id,
            diameter_mm=float(d.get("diameter_mm", 0.0)),
            depth_mm=float(d.get("depth_mm", 0.0)),
            area_mm2=float(d.get("area_mm2", 0.0)),
            angle=float(d.get("angle", 0.0)),
            confidence=float(d.get("confidence", 0.0)),
            camera_id=d.get("camera_id", "N/A"),
            height=float(d.get("height", 0.0)),
            severity=d.get("severity", "Minor"),
            crop_filename=saved_crop_path
        )
        dents_list.append(dent_obj)

    # 6. Return populated message
    return InspectionMessage(
        request_id=request_id,
        inspection_id=inspection_id,
        timestamp=timestamp,
        version=version,
        status=status,
        confidence=confidence,
        processing_time=processing_time,
        scratches=scratches_list,
        dents=dents_list,
        camera_1_frame=c1_filename,
        camera_2_frame=c2_filename
    )
