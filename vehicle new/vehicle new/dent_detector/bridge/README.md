# UNO-Q → AI PC Bridge

This bridge script connects the Qualcomm Arduino UNO-Q dent detector with the AI PC receiver using the **MJPEG relay architecture**.

## System Architecture

```
Samsung S23
    │ MJPEG Stream (port 8080)
    ▼
OnePlus AI Camera Gateway (Android App)
    │  - Receives S23 stream via MJPEGSource
    │  - Filters: blur / motion / exposure / glare
    │  - Accepted frames → MjpegRelayServer (port 8090)
    ▼
UNO-Q dent_detector (C++)
    │  cv::VideoCapture("http://<OnePlus-IP>:8090/stream")
    │  - LED reflection profile analysis
    │  - Dent detection
    │  - Writes ../data/inspection.json
    ▼
bridge.py  ← THIS SCRIPT
    │  - Watches inspection.json via watchdog
    │  - Translates pixel → mm measurements
    │  - Attaches camera images
    │  - POSTs to AI PC
    ▼
AI PC Flask Receiver (port 8000)
    │  POST /api/v1/inspection
    ├─ 3D Digital Twin HTML
    ├─ PDF Report
    ├─ JSON Database
    └─ Live Dashboard (SSE)
```

## Setup

```bash
cd dent_detector/bridge
pip install -r requirements.txt
```

## Usage

```bash
# Basic — replace 192.168.1.50 with your AI PC's IP
python3 bridge.py --host 192.168.1.50

# With custom port and watch path
python3 bridge.py --host 192.168.1.50 --port 8000 --watch ../data/inspection.json

# With custom pixel-per-mm calibration (measure on your specific setup)
python3 bridge.py --host 192.168.1.50 --pixels-per-mm 5.3

# Debug mode (verbose logging)
python3 bridge.py --host 192.168.1.50 --debug
```

## Calibration (pixels-per-mm)

The dent_detector outputs measurements in **pixels**. The AI PC expects **millimetres**.
You need to calibrate `PIXELS_PER_MM` for your specific camera setup:

1. Place a ruler in the camera's field of view
2. Count how many pixels correspond to 1 cm (10 mm)
3. Divide by 10 → that's your `pixels_per_mm` value
4. Pass it via `--pixels-per-mm <value>`

Default value: **5.3 px/mm** (calibrated for 640×480 viewing a ~120mm can section)

## Running with dent_detector

Terminal 1 — Start the dent_detector (pointing at the OnePlus relay):
```bash
cd dent_detector/build
./dent_detector http://192.168.1.200:8090/stream
```

Terminal 2 — Start the bridge:
```bash
cd dent_detector/bridge
python3 bridge.py --host 192.168.1.50
```

The bridge will automatically detect each new inspection.json written by the C++ detector and forward it to the AI PC.

## Metadata Sent to AI PC

The bridge translates and sends:

| Field | Source |
|---|---|
| `version` | Fixed `"1.0"` |
| `request_id` | Generated UUID |
| `inspection_id` | Timestamp-based |
| `status` | `"PASS"` / `"FAIL"` from `dent` boolean |
| `confidence` | Average dent confidence (0.0–1.0) |
| `processing_time` | `processing_time_ms` ÷ 1000 |
| `dents[].diameter_mm` | `width` (px) ÷ PIXELS_PER_MM |
| `dents[].depth_mm` | `depth` (px) ÷ PIXELS_PER_MM |
| `dents[].severity` | Passed through from C++ |
| `camera_1_frame` | `../data/detection.jpg` |
| `crop_ROI` | `../data/cropped.jpg` |
