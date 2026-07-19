#!/usr/bin/env python3
"""
UNO-Q → AI PC Bridge
====================

Watches the dent_detector output file (../data/inspection.json) for changes,
translates the pixel-based C++ output into the mm-based schema the AI PC
Flask receiver expects, and POSTs the translated inspection result to:

    http://<AI_PC_HOST>:<AI_PC_PORT>/api/v1/inspection

This script runs continuously on the UNO-Q (or any host that has access to
the dent_detector's output directory). Start it after launching dent_detector:

    python3 bridge.py
    python3 bridge.py --host 192.168.1.50 --port 8000 --watch ../data/inspection.json

Dependencies (pip install):
    requests watchdog pillow

Architecture:
    UNO-Q C++ dent_detector
          │
          │  writes  ../data/inspection.json  (pixel measurements)
          ▼
    bridge.py (this script)
          │
          │  translates pixels → mm, builds AI-PC schema, POSTs with images
          ▼
    AI PC Flask receiver  POST /api/v1/inspection
          │
          ├─ 3D Digital Twin
          ├─ PDF Report
          └─ Live Dashboard
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("uno_bridge")

# ---------------------------------------------------------------------------
# Pixel → Physical unit conversion
# ---------------------------------------------------------------------------

# Calibration constant: how many pixels correspond to 1 mm on the inspection
# surface.  Adjust to match your actual camera setup and field-of-view.
#
# Formula:
#   sensor_width_mm / (image_width_px * mm_per_pixel) = px_per_mm
#
# Typical value for a 640×480 stream viewing a ~120mm can section: ~5.3 px/mm
PIXELS_PER_MM: float = 5.3


def px_to_mm(pixels: float) -> float:
    """Convert a pixel measurement to millimetres."""
    return round(pixels / PIXELS_PER_MM, 2)


def px2_to_mm2(pixels_sq: float) -> float:
    """Convert a pixel-area measurement to mm²."""
    return round(pixels_sq / (PIXELS_PER_MM ** 2), 2)


# ---------------------------------------------------------------------------
# Schema translation
# ---------------------------------------------------------------------------

def translate_inspection(raw: dict, image_dir: Path) -> dict:
    """
    Translate the C++ dent_detector JSON output into the schema expected by
    the AI PC Flask receiver's parser.py.

    C++ schema (pixel-based)
    ────────────────────────
    {
        "dent": bool,
        "dents_count": int,
        "rmse": float,
        "avg_deviation": float,
        "max_deviation": float,
        "noise_level": float,
        "alignment_dx": float,
        "alignment_dy": float,
        "alignment_slope": float,
        "completeness_pct": float,
        "processing_time_ms": float,
        "dents": [
            {
                "id": int,
                "start": int,       ← pixel column
                "end": int,         ← pixel column
                "center": int,      ← pixel column
                "width": int,       ← pixels
                "depth": float,     ← pixels
                "severity": str,    ← "Minor" | "Moderate" | "Major"
                "confidence": float ← 0–100
            }
        ]
    }

    AI PC schema (mm-based)
    ───────────────────────
    {
        "version": "1.0",
        "request_id": str,
        "inspection_id": str,
        "timestamp": str,
        "status": "PASS" | "FAIL",
        "confidence": float,       ← 0.0–1.0
        "processing_time": float,  ← seconds
        "scratches": [],
        "dents": [
            {
                "id": str,
                "diameter_mm": float,
                "depth_mm": float,
                "area_mm2": float,
                "angle": float,
                "confidence": float,
                "camera_id": str,
                "height": float,
                "severity": str
            }
        ]
    }
    """
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    inspection_id = f"INSPECT_{now.strftime('%Y%m%d_%H%M%S')}_UNOQ"
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    dents_raw = raw.get("dents", [])
    dents_mm = []
    for d in dents_raw:
        width_px = float(d.get("width", 0))
        depth_px = float(d.get("depth", 0))
        dent_id = f"DENT_{d.get('id', len(dents_mm) + 1):03d}"

        # Approximate area: treat dent as an ellipse with semi-axes = width/2, depth/2
        area_px2 = 3.14159 * (width_px / 2.0) * (depth_px / 2.0)

        dents_mm.append({
            "id": dent_id,
            "diameter_mm": px_to_mm(width_px),
            "depth_mm": px_to_mm(depth_px),
            "area_mm2": px2_to_mm2(area_px2),
            "angle": 0.0,              # LED profile gives horizontal profile only
            "confidence": round(d.get("confidence", 0.0) / 100.0, 3),
            "camera_id": "camera_1",   # Single camera on UNO-Q
            "height": px_to_mm(float(d.get("center", 0))),
            "severity": d.get("severity", "Unknown"),
        })

    has_dent = raw.get("dent", False)
    avg_confidence_raw = (
        sum(d["confidence"] for d in dents_mm) / len(dents_mm)
        if dents_mm else (0.0 if has_dent else 1.0)
    )

    return {
        "version": "1.0",
        "request_id": request_id,
        "inspection_id": inspection_id,
        "timestamp": timestamp_str,
        "status": "FAIL" if has_dent else "PASS",
        "confidence": round(avg_confidence_raw, 3),
        "processing_time": round(raw.get("processing_time_ms", 0.0) / 1000.0, 4),
        "scratches": [],   # C++ detector does not detect scratches
        "dents": dents_mm,
        # Extra diagnostic fields (ignored by parser but useful for debugging)
        "_bridge_meta": {
            "rmse": raw.get("rmse", 0.0),
            "avg_deviation": raw.get("avg_deviation", 0.0),
            "max_deviation": raw.get("max_deviation", 0.0),
            "noise_level": raw.get("noise_level", 0.0),
            "completeness_pct": raw.get("completeness_pct", 0.0),
            "alignment_dx": raw.get("alignment_dx", 0.0),
            "alignment_dy": raw.get("alignment_dy", 0.0),
            "alignment_slope": raw.get("alignment_slope", 0.0),
            "pixels_per_mm": PIXELS_PER_MM,
        },
    }


# ---------------------------------------------------------------------------
# Multipart image builder
# ---------------------------------------------------------------------------

def build_multipart_files(image_dir: Path) -> list:
    """
    Build the multipart file list to attach to the POST request.

    The AI PC parser expects these named image parts:
        camera_1_frame    — full resolution camera frame
        camera_2_frame    — (optional) second camera; omitted here
        crop_DENT_001     — (optional) cropped defect patch

    We attach whatever images the dent_detector has written to ../data/.
    """
    files = []

    cam_frame = image_dir / "detection.jpg"
    if cam_frame.exists():
        files.append(
            ("camera_1_frame", (cam_frame.name, cam_frame.read_bytes(), "image/jpeg"))
        )
        log.debug("Attached camera_1_frame: %s", cam_frame)

    # Attach cropped ROI image as a generic crop
    cropped = image_dir / "cropped.jpg"
    if cropped.exists():
        files.append(
            ("crop_ROI", (cropped.name, cropped.read_bytes(), "image/jpeg"))
        )
        log.debug("Attached crop_ROI: %s", cropped)

    return files


# ---------------------------------------------------------------------------
# HTTP sender
# ---------------------------------------------------------------------------

def send_to_ai_pc(payload: dict, files: list, ai_pc_url: str, timeout: int = 15) -> bool:
    """
    POST the translated inspection result to the AI PC receiver.

    Returns True on success, False on failure.
    """
    metadata_json = json.dumps(payload)

    form_data = {"metadata": (None, metadata_json, "application/json")}
    all_parts = list(form_data.items()) + files

    try:
        log.info("POSTing inspection %s → %s", payload["inspection_id"], ai_pc_url)
        resp = requests.post(
            ai_pc_url,
            files=all_parts,
            timeout=timeout,
        )
        if resp.status_code == 200:
            body = resp.json() if resp.content else {}
            log.info("✅ AI PC accepted: %s", body.get("message", "OK"))
            return True
        else:
            log.error("❌ AI PC returned HTTP %d: %s", resp.status_code, resp.text[:200])
            return False
    except requests.exceptions.ConnectionError:
        log.error("❌ Cannot reach AI PC at %s — is the Flask server running?", ai_pc_url)
        return False
    except requests.exceptions.Timeout:
        log.error("❌ Request timed out after %ds", timeout)
        return False
    except Exception as exc:  # noqa: BLE001
        log.exception("❌ Unexpected error during POST: %s", exc)
        return False


# ---------------------------------------------------------------------------
# File watcher
# ---------------------------------------------------------------------------

class InspectionJsonHandler(FileSystemEventHandler):
    """
    Watchdog event handler: fires when inspection.json is written.
    Debounces rapid successive writes (C++ may write multiple times per frame).
    """

    DEBOUNCE_SECONDS = 1.0  # Wait this long after last write before processing

    def __init__(self, watch_path: Path, ai_pc_url: str, image_dir: Path):
        self.watch_path = watch_path.resolve()
        self.ai_pc_url = ai_pc_url
        self.image_dir = image_dir
        self._last_event_time = 0.0
        self._last_mtime = 0.0

    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).resolve() != self.watch_path:
            return
        self._last_event_time = time.monotonic()

    def on_created(self, event):
        self.on_modified(event)

    def process_if_ready(self):
        """Called from the main poll loop to handle debounced events."""
        if self._last_event_time == 0.0:
            return
        if (time.monotonic() - self._last_event_time) < self.DEBOUNCE_SECONDS:
            return

        # Check file mtime to avoid re-processing unchanged files
        try:
            mtime = self.watch_path.stat().st_mtime
        except FileNotFoundError:
            return

        if mtime == self._last_mtime:
            self._last_event_time = 0.0
            return

        self._last_mtime = mtime
        self._last_event_time = 0.0
        self._handle_new_inspection()

    def _handle_new_inspection(self):
        log.info("New inspection.json detected — processing…")
        try:
            raw_text = self.watch_path.read_text(encoding="utf-8")
            raw = json.loads(raw_text)
        except (OSError, json.JSONDecodeError) as exc:
            log.error("Failed to read/parse inspection.json: %s", exc)
            return

        translated = translate_inspection(raw, self.image_dir)
        files = build_multipart_files(self.image_dir)
        send_to_ai_pc(translated, files, self.ai_pc_url)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="UNO-Q → AI PC Bridge: watches inspection.json and forwards results."
    )
    p.add_argument(
        "--host",
        default="192.168.1.50",
        help="IP address of the AI PC running the Flask receiver (default: 192.168.1.50)",
    )
    p.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port of the AI PC Flask receiver (default: 8000)",
    )
    p.add_argument(
        "--watch",
        default="../data/inspection.json",
        help="Path to the dent_detector output JSON (default: ../data/inspection.json)",
    )
    p.add_argument(
        "--pixels-per-mm",
        type=float,
        default=PIXELS_PER_MM,
        help=f"Calibration constant: pixels per millimetre (default: {PIXELS_PER_MM})",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    global PIXELS_PER_MM
    PIXELS_PER_MM = args.pixels_per_mm

    watch_path = Path(args.watch).resolve()
    image_dir = watch_path.parent
    ai_pc_url = f"http://{args.host}:{args.port}/api/v1/inspection"

    log.info("=" * 60)
    log.info("UNO-Q → AI PC Bridge starting")
    log.info("  Watching : %s", watch_path)
    log.info("  AI PC URL: %s", ai_pc_url)
    log.info("  px/mm    : %.2f  (change via --pixels-per-mm)", PIXELS_PER_MM)
    log.info("=" * 60)

    if not image_dir.exists():
        log.error("Data directory does not exist: %s", image_dir)
        sys.exit(1)

    handler = InspectionJsonHandler(watch_path, ai_pc_url, image_dir)
    observer = Observer()
    observer.schedule(handler, str(image_dir), recursive=False)
    observer.start()
    log.info("Watchdog observer started — waiting for dent_detector output…")

    try:
        while True:
            handler.process_if_ready()
            time.sleep(0.25)
    except KeyboardInterrupt:
        log.info("Interrupted by user — shutting down.")
    finally:
        observer.stop()
        observer.join()
        log.info("Bridge stopped.")


if __name__ == "__main__":
    main()
