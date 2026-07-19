# Car-Checkro
AI-powered automated vehicle inspection system using multi-camera vision, YOLO11, and Qualcomm AI Hub for real-time scratch and dent detection.

An intelligent, multi-node distributed quality analysis and dent detection system designed to inspect cylindrical containers (such as beverage cans) on a high-speed production line. The system utilizes edge filtering, C++ computer vision, and real-time dashboard telemetry.

---

## 👥 Team Information

*   **Shourya Singh** — shourya24536@iiitd.ac.in
*   **Pratik Yadav** — pratik24430@iiitd.ac.in
*   **Vedant Singh** — vedant24615@iiitd.ac.in
*   **Gagan Kharb** — Gagan24213@iiitd.ac.in
*   **Chaitanya Thakur** — thakurchaitanya784@gmail.com

---

## 📐 System Architecture

The pipeline splits computation across three nodes to achieve low latency, high frame filtering efficiency, and reliable edge inference:

```
                  Samsung S23 (Camera Stream Source)
                                │
                                │ MJPEG Stream @ :8080/video
                                ▼
             OnePlus AI Camera Gateway (Android Edge Node)
                                │
                                ├─ Frame Quality Filtering (Blur, Motion, Glare, Exposure)
                                └─ Re-encodes accepted frames to MJPEG Relay @ :8090/stream
                                ▼
            Qualcomm Arduino UNO-Q (C++ Edge Inference Node)
                                │
                                ├─ cv::VideoCapture reads clean stream
                                ├─ LED Profile Extraction & Calibration
                                └─ Writes pixel deviations → ../data/inspection.json
                                ▼
                       UNO-Q → AI PC Bridge
                                │
                                ├─ Watchdog monitors inspection.json changes
                                └─ Translates pixels → mm, POSTs with images to AI PC
                                ▼
                  AI PC Receiver (Central Orchestration)
                                │
                                ├─ Flask server accepts POST @ :8000/api/v1/inspection
                                ├─ Inserts metrics into JSON Database
                                ├─ Compiles 3D Digital Twin HTML & PDF reports
                                ├─ Archives reports in output/out{N} folders
                                └─ Pushes real-time updates via SSE to Dashboard
```

---

## 📂 Repository Structure

*   `gateway-android/`: OnePlus AI Camera Gateway Android Application (Kotlin, OpenCV, CameraX).
*   `dent-detector-cpp/`:
    *   `dent_detector/`: C++ dent detection engine using OpenCV profile analysis.
    *   `bridge/`: Watchdog bridge script that translates measurements and uploads results.
*   `aipc-receiver-python/`:
    *   `src/`: Flask server, database, report generator, and digital twin engine.
    *   `scratch/`: Simulation scripts for pipeline verification.

---

## 🛠️ Dependency & Installation Guide

### 1. OnePlus AI Camera Gateway (Android Node)
*   **IDE:** Android Studio (Hedgehog or newer recommended).
*   **JDK:** Version 17.
*   **SDK:** Target/Compile SDK 34 (Android 14), Min SDK 26 (Android 8.0).
*   **Libraries:** Included automatically via `build.gradle.kts` (OpenCV, CameraX, Retrofit2, OkHttp3).

### 2. Qualcomm Arduino UNO-Q (C++ Inference Node)
Ensure compiler tools and OpenCV development libraries are installed on the device (Ubuntu/Debian example):
```bash
sudo apt update
sudo apt install build-essential cmake libopencv-dev python3-pip python3-dev -y
```

### 3. AI PC Receiver (Python Orchestration Node)
Install the required Python modules:
```bash
pip install flask reportlab pillow requests watchdog
```

---

## 🚀 Run & Usage Instructions

Follow this sequence to launch the entire end-to-end pipeline:

### Step 1: Start the AI PC Receiver
Run the central receiver on your AI PC:
```bash
cd aipc-receiver-python/src
python main.py
```
*The receiver will start on `http://0.0.0.0:8000` and automatically launch your browser to show the live dashboard at `http://127.0.0.1:8000/dashboard`.*

### Step 2: Set up the Samsung S23 Source
1. Install and run **IP Webcam** (or any compatible MJPEG server) on your Samsung S23.
2. Start the server in the app. Note the address (e.g., `http://192.168.1.100:8080/video`).

### Step 3: Run the OnePlus AI Camera Gateway
1. Open `gateway-android/` in Android Studio and deploy the app to your OnePlus device.
2. In the app Settings:
   * Enter the Samsung S23 stream URL: `http://192.168.1.100:8080/video`
   * Check that the camera mode includes Samsung S23.
3. Tap **Start Stream**. The phone will filter the feed and automatically spin up the MJPEG relay server on port `8090`.
4. Note your OnePlus phone's IP address (e.g., `192.168.1.200`).

### Step 4: Build & Run the UNO-Q C++ Dent Detector
Compile the native engine on the UNO-Q device:
```bash
cd dent-detector-cpp/dent_detector
mkdir build && cd build
cmake ..
make -j4
```
Start the detector, pointing it to the OnePlus relay stream:
```bash
./dent_detector http://192.168.1.200:8090/stream
```

### Step 5: Start the UNO-Q → AI PC Bridge
In a second terminal window on the UNO-Q device, run the bridge script:
```bash
cd dent-detector-cpp/bridge
pip install -r requirements.txt
python bridge.py --host <AI-PC-IP> --pixels-per-mm 5.3
```
*(Replace `<AI-PC-IP>` with the actual IP address of your AI PC running the receiver).*

---

## 🧪 Verification & Testing Instructions

To verify that each component works without needing the physical hardware connected, run these simulation tests:

### 1. Test AI PC Receiver (Simulation)
Ensure the Python server is running, then run the HTTP mock sender:
```bash
cd aipc-receiver-python
python scratch/simulate_uno_q_http.py
```
*This sends simulated inspection payloads and images to the Flask server. Verify that the counts increment on the dashboard, and new sequential output folders `output/out1/`, `output/out2/`, etc., are created containing PDF/HTML reports.*

### 2. Test Android Compilation & Unit Tests
To verify the Android codebase compiles and passes its quality logic tests:
```bash
cd gateway-android
./gradlew testDebugUnitTest
```

### 3. Verify C++ Profile Processing
Verify the C++ detector parses reference files correctly by checking the build output:
```bash
cd dent-detector-cpp/dent_detector/build
./dent_detector --help
```

---

## 📝 Technical Notes & Calibration

### Pixel to Millimetre Calibration
The dent detector outputs defect boundaries in pixels. The watchdog bridge converts these to physical millimetres using the `--pixels-per-mm` parameter.
*   **Formula:** `pixels_per_mm = image_width_pixels / physical_width_mm`
*   *Default calibration is set to 5.3 px/mm, corresponding to a 640x480 resolution capturing a ~120mm section of a standard aluminum can.*

### 3D Digital Twin Material Properties
The generated 3D twin has been updated to represent a realistic grey metallic finish (`0xcccccc`) with custom micro-geometry properties:
*   **Metalness:** 0.30 (realistic aluminum specularity)
*   **Roughness:** 0.35 (satin finish, reducing specular glare)

---

## 📄 References & Libraries Used
*   **OpenCV Core:** Real-time profile extraction and image processing.
*   **Android Jetpack CameraX:** Hardware camera abstraction and frame extraction.
*   **Retrofit 2:** Client-side type-safe HTTP interface.
*   **Three.js:** Embedded 3D Digital Twin visualization in reports.
*   **ReportLab:** Native Python canvas-based PDF generation.
*   **Watchdog (Python):** Event-based directory monitoring.
