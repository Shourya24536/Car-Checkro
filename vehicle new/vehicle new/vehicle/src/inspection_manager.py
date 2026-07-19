# Central coordinator for the inspection lifecycle (Orchestrator)
import os
import traceback
from typing import Dict, Any
from .message_models import InspectionMessage
from .database import JSONFileStorage
from .report_generator import ReportGenerator
from .defect_tracker import DefectTracker
from .http_receiver import sse_manager
from .logger import log_info, log_error, log_warn
from .config import REPORTS_DIR, DIGITAL_TWINS_DIR

class InspectionManager:
    """
    Orchestrates the processing pipeline of parsed inspection messages.
    Invokes database persistence, defect tracker data fusion, digital twin rendering,
    and report generation inside a fault-tolerant, event-driven model.
    """
    def __init__(self):
        log_info("Initializing InspectionManager...")
        self.database = JSONFileStorage()
        self.report_generator = ReportGenerator()
        self.defect_tracker = DefectTracker()

    def handle_new_inspection(self, msg: InspectionMessage) -> bool:
        """
        Processes a newly parsed InspectionMessage.
        Tracks execution statuses for all downstream components and reports them.
        """
        log_info(f"[InspectionManager] Starting orchestration pipeline for request {msg.request_id}...")

        # Operation status flags
        db_saved = False
        tracker_fused = False
        twin_gen = False
        report_gen = False

        # 1. Transform immutable message model to database dictionary payload
        scratches_dict = [
            {
                "id": s.id, "length_mm": s.length_mm, "width_mm": s.width_mm,
                "area_mm2": s.area_mm2, "angle": s.angle, "confidence": s.confidence,
                "camera_id": s.camera_id, "height": s.height, "crop_path": s.crop_filename
            } for s in msg.scratches
        ]
        
        dents_dict = [
            {
                "id": d.id, "diameter_mm": d.diameter_mm, "depth_mm": d.depth_mm,
                "area_mm2": d.area_mm2, "angle": d.angle, "confidence": d.confidence,
                "camera_id": d.camera_id, "height": d.height, "severity": d.severity,
                "crop_path": d.crop_filename
            } for d in msg.dents
        ]

        payload_dict = {
            "request_id": msg.request_id,
            "inspection_id": msg.inspection_id,
            "timestamp": msg.timestamp,
            "version": msg.version,
            "status": msg.status,
            "confidence": msg.confidence,
            "processing_time": msg.processing_time,
            "scratches": scratches_dict,
            "dents": dents_dict,
            "camera_1_frame": msg.camera_1_frame,
            "camera_2_frame": msg.camera_2_frame
        }

        # 2. Database Persistence
        try:
            db_saved = self.database.save_inspection(payload_dict)
            if db_saved:
                log_info(f"[InspectionManager] Saved inspection {msg.inspection_id} to database.")
        except Exception as db_err:
            log_error(f"[InspectionManager] Database write error for inspection {msg.inspection_id}: {db_err}")

        # 3. Data Fusion / Defect Tracker
        fused_scratches = scratches_dict
        fused_dents = dents_dict
        try:
            # Let tracker perform observation merging (merges duplicate coordinates from multiple cams)
            fused_scratches, fused_dents = self.defect_tracker.fuse_observations(scratches_dict, dents_dict)
            tracker_fused = True
            log_info(f"[InspectionManager] Defect spatial data fusion complete. Scratches: {len(fused_scratches)}, Dents: {len(fused_dents)}")
        except Exception as fuse_err:
            log_error(f"[InspectionManager] Defect tracker spatial fusion failed: {fuse_err}")

        # Re-update database with fused defects if database write succeeded
        if db_saved and tracker_fused:
            try:
                payload_dict["scratches"] = fused_scratches
                payload_dict["dents"] = fused_dents
                # Update history (simply overwrite with latest containing fused elements)
                history = self.database.get_history(limit=1000)
                # Reverse history to original order for rewriting
                original_order = list(reversed(history))
                for idx, entry in enumerate(original_order):
                    if entry.get("request_id") == msg.request_id:
                        original_order[idx] = payload_dict
                        break
                # Clear and rewrite
                self.database.clear()
                for entry in original_order:
                    self.database.save_inspection(entry)
            except Exception as update_err:
                log_warn(f"[InspectionManager] Failed to update fused records in database: {update_err}")

        # Define file naming conventions matching target folders
        html_path = os.path.join(DIGITAL_TWINS_DIR, f"{msg.inspection_id}_report.html")
        pdf_path = os.path.join(REPORTS_DIR, f"{msg.inspection_id}_report.pdf")

        # 4. Generate Interactive 3D Digital Twin HTML
        try:
            summary = {
                "inspection_id": msg.inspection_id,
                "date": msg.timestamp.split(" ")[0] if " " in msg.timestamp else msg.timestamp,
                "time": msg.timestamp.split(" ")[1] if " " in msg.timestamp else "",
                "result": msg.status,
                "recommendation": "Can REJECTED - critical defects detected." if msg.status == "FAIL" else "Can PASSED - acceptable quality.",
                "processing_time": msg.processing_time
            }
            
            # Write HTML report
            self.report_generator.generate_html_report(
                summary=summary,
                scratches=fused_scratches,
                dents=fused_dents,
                html_path=html_path,
                annotated_1=msg.camera_1_frame,
                annotated_2=msg.camera_2_frame
            )
            twin_gen = True
            log_info(f"[InspectionManager] Generated HTML 3D digital twin report at {html_path}")
        except Exception as html_err:
            log_error(f"[InspectionManager] 3D digital twin HTML generation failed: {html_err}")
            traceback.print_exc()

        # 5. Generate PDF Report
        try:
            self.report_generator.generate_pdf(
                summary=summary,
                scratches=fused_scratches,
                dents=fused_dents,
                filepath=pdf_path,
                html_path=html_path,
                annotated_1=msg.camera_1_frame,
                annotated_2=msg.camera_2_frame
            )
            report_gen = True
            log_info(f"[InspectionManager] Generated PDF report at {pdf_path}")
        except Exception as pdf_err:
            log_error(f"[InspectionManager] PDF report generation failed: {pdf_err}")
            traceback.print_exc()

        # 6. Copy PDF and HTML to a sequential output directory: out{N}
        if twin_gen and report_gen:
            try:
                import shutil
                output_dir = os.path.dirname(REPORTS_DIR)
                
                # List existing directories in output
                existing_nums = []
                for entry in os.listdir(output_dir):
                    if entry.startswith("out") and os.path.isdir(os.path.join(output_dir, entry)):
                        num_part = entry[3:]
                        if num_part.isdigit():
                            existing_nums.append(int(num_part))
                
                next_num = max(existing_nums) + 1 if existing_nums else 1
                out_folder_name = f"out{next_num}"
                out_folder_path = os.path.join(output_dir, out_folder_name)
                os.makedirs(out_folder_path, exist_ok=True)
                
                # Copy reports
                shutil.copy2(pdf_path, os.path.join(out_folder_path, f"{msg.inspection_id}_report.pdf"))
                shutil.copy2(html_path, os.path.join(out_folder_path, f"{msg.inspection_id}_report.html"))
                
                log_info(f"[InspectionManager] Saved PDF and HTML reports to sequential folder: {out_folder_path}")
            except Exception as copy_err:
                log_error(f"[InspectionManager] Failed to save reports to outnumber folder: {copy_err}")

        # 7. Broadcast updates to active Dashboard clients via Server-Sent Events (SSE)
        try:
            event_data = {
                "request_id": msg.request_id,
                "inspection_id": msg.inspection_id,
                "timestamp": msg.timestamp,
                "status": msg.status,
                "confidence": msg.confidence,
                "processing_time": msg.processing_time,
                "num_scratches": len(fused_scratches),
                "num_dents": len(fused_dents),
                "db_saved": db_saved,
                "twin_generated": twin_gen,
                "report_generated": report_gen,
                "pdf_filename": f"{msg.inspection_id}_report.pdf",
                "html_filename": f"{msg.inspection_id}_report.html"
            }
            sse_manager.broadcast("inspection_event", event_data)
            log_info(f"[InspectionManager] Dispatched SSE broadcast for inspection {msg.inspection_id}")
        except Exception as sse_err:
            log_error(f"[InspectionManager] Failed to dispatch SSE broadcast: {sse_err}")

        # Return True if core data pipeline processed successfully
        return db_saved
