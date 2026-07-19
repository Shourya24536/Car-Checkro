# HTML Report Template for Coke Can Inspection Digital Twin
# Renders a premium, interactive WebGL 3D cylinder with Bezier curves,
# active defect markings, dynamic vertex deformations for dents,
# view controls, and camera rig helpers.

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coke Can Inspection Dashboard - ID __INSPECTION_ID__</title>
    <style>
        :root {
            --bg-color: #0b0b0d;
            --panel-bg: #141417;
            --accent-red: #dd0b12;
            --accent-blue: #0076ff;
            --text-main: #f0f0f5;
            --text-muted: #8e8e93;
            --border-color: #2c2c2e;
            --pass-green: #34c759;
            --fail-red: #ff3b30;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            overflow-x: hidden;
            padding: 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 25px;
        }

        .header-title h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: #ffffff;
        }

        .header-title p {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        .tab-nav {
            display: flex;
            gap: 10px;
        }

        .tab-btn {
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .tab-btn:hover {
            color: var(--text-main);
            border-color: #545456;
        }

        .tab-btn.active {
            background-color: var(--accent-red);
            color: #ffffff;
            border-color: var(--accent-red);
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Grid layouts */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }

        .metric-card {
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            position: relative;
        }

        .metric-card.result-card {
            border-left: 5px solid var(--border-color);
        }

        .metric-card.result-card.pass {
            border-left-color: var(--pass-green);
        }

        .metric-card.result-card.fail {
            border-left-color: var(--fail-red);
        }

        .metric-card h3 {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .metric-card .value {
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }

        .metric-card .subtitle {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        /* 3D Visualizer Workspace */
        .workspace {
            display: flex;
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            height: 680px;
            margin-bottom: 25px;
        }

        .viewport-container {
            flex: 1;
            position: relative;
            background-color: #0e0e11;
        }

        #canvas-container {
            width: 100%;
            height: 100%;
        }

        .viewport-overlay {
            position: absolute;
            top: 15px;
            left: 15px;
            background-color: rgba(20, 20, 23, 0.85);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            color: var(--text-muted);
            pointer-events: none;
            backdrop-filter: blur(8px);
        }

        /* Right Sidebar Controls */
        .sidebar {
            width: 330px;
            border-left: 1px solid var(--border-color);
            background-color: var(--panel-bg);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 18px;
        }

        .sidebar-section {
            margin-bottom: 20px;
        }

        .sidebar-section h2 {
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            border-bottom: 1px solid #2c2c2e;
            padding-bottom: 6px;
        }

        .sidebar-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .status-badge {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
        }

        .status-badge.pass {
            background-color: rgba(52, 199, 89, 0.15);
            color: var(--pass-green);
            border: 1px solid rgba(52, 199, 89, 0.3);
        }

        .status-badge.fail {
            background-color: rgba(255, 59, 48, 0.15);
            color: var(--fail-red);
            border: 1px solid rgba(255, 59, 48, 0.3);
        }

        .defect-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-height: 180px;
            overflow-y: auto;
            margin-bottom: 12px;
        }

        .defect-item {
            display: flex;
            gap: 6px;
        }

        .defect-btn {
            flex: 1;
            background-color: #1e1e24;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 10px;
            font-size: 12px;
            text-align: left;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .defect-btn:hover {
            background-color: #2a2a32;
        }

        .defect-btn.dent {
            border-left: 3px solid var(--accent-red);
        }

        .defect-btn.scratch {
            border-left: 3px solid var(--accent-blue);
        }

        .defect-delete-btn {
            background-color: #2c2c35;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            width: 32px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            font-size: 11px;
            transition: all 0.15s;
        }

        .defect-delete-btn:hover {
            background-color: var(--fail-red);
            color: #ffffff;
            border-color: var(--fail-red);
        }

        .no-defects {
            font-size: 12px;
            color: var(--text-muted);
            font-style: italic;
            padding: 8px 0;
        }

        /* Sliders / Injection form */
        .form-group {
            margin-bottom: 12px;
        }

        .form-group label {
            display: block;
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        .form-group select, .form-group input[type="range"] {
            width: 100%;
        }

        .form-group select {
            background-color: #1e1e24;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 6px;
            font-size: 12px;
            border-radius: 4px;
            outline: none;
        }

        .slider-wrapper {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .slider-wrapper input[type="range"] {
            flex: 1;
            accent-color: var(--accent-red);
        }

        .slider-val {
            font-size: 11px;
            color: var(--text-main);
            width: 45px;
            text-align: right;
            font-family: monospace;
        }

        .btn-submit {
            width: 100%;
            background-color: var(--accent-red);
            color: #ffffff;
            border: none;
            padding: 8px 0;
            font-size: 12px;
            font-weight: 700;
            border-radius: 4px;
            cursor: pointer;
            transition: opacity 0.15s;
        }

        .btn-submit:hover {
            opacity: 0.9;
        }

        /* Camera grid */
        .camera-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
        }

        .cam-btn {
            background-color: #1e1e24;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 6px 0;
            font-size: 11px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.15s;
        }

        .cam-btn:hover {
            background-color: #2a2a32;
        }

        .cam-btn.active {
            background-color: var(--accent-red);
            border-color: var(--accent-red);
        }

        .cam-btn-full {
            grid-column: span 2;
            background-color: #2c2c35;
        }

        .separator {
            height: 1px;
            background-color: var(--border-color);
            margin: 15px 0;
        }

        /* Defect Details Logs & Cards */
        .logs-section {
            margin-bottom: 25px;
        }

        .logs-section-title {
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 15px;
            color: #ffffff;
        }}

        .defects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }

        .defect-card {
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            display: flex;
            overflow: hidden;
            height: 180px;
        }

        .defect-card.scratch {
            border-left: 4px solid var(--accent-blue);
        }

        .defect-card.dent {
            border-left: 4px solid var(--accent-red);
        }

        .defect-image-area {
            width: 160px;
            background-color: #0e0e11;
            display: flex;
            justify-content: center;
            align-items: center;
            border-right: 1px solid var(--border-color);
            position: relative;
        }

        .defect-image-area img {
            max-width: 100%;
            max-height: 100%;
            object-fit: cover;
        }

        .defect-image-area .no-image-label {
            font-size: 10px;
            color: var(--text-muted);
            text-align: center;
        }

        .defect-info-area {
            flex: 1;
            padding: 15px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .defect-info-title {
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .defect-info-title.dent {
            color: var(--accent-red);
        }

        .defect-info-title.scratch {
            color: var(--accent-blue);
        }

        .defect-badge {
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
        }

        .defect-badge.dent {
            background-color: rgba(221, 11, 18, 0.15);
            color: var(--accent-red);
        }

        .defect-badge.scratch {
            background-color: rgba(0, 118, 255, 0.15);
            color: var(--accent-blue);
        }

        .details-list {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            font-size: 11.5px;
        }

        .details-item {
            display: flex;
            flex-direction: column;
        }

        .details-label {
            color: var(--text-muted);
            font-size: 10px;
            text-transform: uppercase;
        }

        .details-value {
            font-weight: 600;
            color: var(--text-main);
        }

        /* Camera streams annotated frames */
        .cameras-section {
            margin-bottom: 25px;
        }

        .cameras-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 15px;
        }

        .camera-container {
            background-color: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            padding: 10px;
        }

        .camera-title {
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .camera-feed-box {
            width: 100%;
            height: auto;
            max-height: 400px;
            background-color: #000000;
            display: flex;
            justify-content: center;
            align-items: center;
            border-radius: 4px;
            overflow: hidden;
        }

        .camera-feed-box img {
            width: 100%;
            height: auto;
            max-height: 400px;
            object-fit: contain;
        }

        .no-feed-msg {
            font-size: 12px;
            color: var(--text-muted);
            padding: 40px 0;
        }
    </style>
    <!-- Load Three.js and OrbitControls -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>Coke Can Automated Inspection Gateway</h1>
            <p>Inspection Session: __INSPECTION_ID__ &bull; Date: __DATE__ &bull; Time: __TIME__</p>
        </div>
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('tab-twin')">3D Digital Twin</button>
            <button class="tab-btn" onclick="switchTab('tab-logs')">Inspection Logs & Crops</button>
        </div>
    </header>

    <div class="metrics-grid">
        <div class="metric-card result-card __RESULT_CLASS__">
            <h3>Inspection Result</h3>
            <div class="value">__RESULT__</div>
            <div class="subtitle">__RECOMMENDATION__</div>
        </div>
        <div class="metric-card">
            <h3>Dents Detected</h3>
            <div class="value" id="metrics-dents">__NUM_DENTS__</div>
            <div class="subtitle">Critical limit: 0 allowed</div>
        </div>
        <div class="metric-card">
            <h3>Scratches Detected</h3>
            <div class="value" id="metrics-scratches">__NUM_SCRATCHES__</div>
            <div class="subtitle">Acceptance threshold: &le; 3</div>
        </div>
        <div class="metric-card">
            <h3>Process Duration</h3>
            <div class="value">__PROCESSING_TIME__s</div>
            <div class="subtitle">Gateway Processing speed</div>
        </div>
    </div>

    <!-- TAB 1: 3D DIGITAL TWIN -->
    <div id="tab-twin" class="tab-content active">
        <div class="workspace">
            <div class="viewport-container">
                <div class="viewport-overlay">WebGL 3D Viewport &bull; Left Click + Drag to Rotate &bull; Right Click + Drag to Pan</div>
                <div id="canvas-container"></div>
            </div>
            <div class="sidebar">
                <div class="sidebar-section">
                    <div class="sidebar-title">COKE CAN DIGITAL TWIN</div>
                    <div id="sidebar-status-badge" class="status-badge __RESULT_CLASS__">__RESULT_BADGE__</div>
                </div>

                <div class="sidebar-section">
                    <h2>Active Defects</h2>
                    <div class="defect-list" id="active-defect-list">
                        <!-- Filled by JS -->
                    </div>
                </div>

                <div class="sidebar-section">
                    <h2>Defect Injection Tool</h2>
                    <div class="form-group">
                        <label for="inject-type">Defect Type</label>
                        <select id="inject-type">
                            <option value="dent">Dent</option>
                            <option value="scratch">Scratch</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Angle (Degrees 0-359)</label>
                        <div class="slider-wrapper">
                            <input type="range" id="inject-angle" min="0" max="359" value="120" oninput="updateSliderVal('angle', this.value)">
                            <span class="slider-val" id="val-angle">120°</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Height (Z in meters)</label>
                        <div class="slider-wrapper">
                            <input type="range" id="inject-height" min="-50" max="50" value="20" oninput="updateSliderVal('height', this.value/1000)">
                            <span class="slider-val" id="val-height">0.020m</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Confidence (0.0 - 1.0)</label>
                        <div class="slider-wrapper">
                            <input type="range" id="inject-conf" min="0" max="100" value="95" oninput="updateSliderVal('conf', this.value/100)">
                            <span class="slider-val" id="val-conf">0.95</span>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Defect Size / Radius (meters)</label>
                        <div class="slider-wrapper">
                            <input type="range" id="inject-size" min="1" max="10" value="3" oninput="updateSliderVal('size', this.value/1000)">
                            <span class="slider-val" id="val-size">0.003m</span>
                        </div>
                    </div>
                    <button class="btn-submit" onclick="handleInjectDefect()">Inject Defect</button>
                </div>

                <div class="sidebar-section">
                    <h2>Camera Controls</h2>
                    <div class="camera-grid">
                        <button class="cam-btn" id="btn-cam-front" onclick="setCameraPreset('Front')">Front</button>
                        <button class="cam-btn" id="btn-cam-back" onclick="setCameraPreset('Back')">Back</button>
                        <button class="cam-btn" id="btn-cam-left" onclick="setCameraPreset('Left')">Left</button>
                        <button class="cam-btn" id="btn-cam-right" onclick="setCameraPreset('Right')">Right</button>
                        <button class="cam-btn" id="btn-cam-top" onclick="setCameraPreset('Top')">Top</button>
                        <button class="cam-btn" id="btn-cam-bottom" onclick="setCameraPreset('Bottom')">Bottom</button>
                        <button class="cam-btn cam-btn-full" id="btn-cam-rig" onclick="toggleCameraRig()">Toggle Camera Rig</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- TAB 2: DETECTED LOGS & CROP IMAGES -->
    <div id="tab-logs" class="tab-content">
        <div class="logs-section">
            <h2 class="logs-section-title">Defect Detail Logs & Crop Images</h2>
            <div class="defects-grid" id="details-defects-grid">
                <!-- Filled by JS/Python -->
                __DEFECT_DETAILS_CARDS__
            </div>
        </div>

        <div class="cameras-section">
            <h2 class="logs-section-title">Annotated Camera Captures</h2>
            <div class="cameras-grid">
                <div class="camera-container">
                    <div class="camera-title">Camera 1 (Top-Right View) - Annotated Feed</div>
                    <div class="camera-feed-box">
                        __CAMERA_1_FEED_CONTENT__
                    </div>
                </div>
                <div class="camera-container">
                    <div class="camera-title">Camera 2 (Top-Left View) - Annotated Feed</div>
                    <div class="camera-feed-box">
                        __CAMERA_2_FEED_CONTENT__
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Switch between tabs
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            
            // Find clicked button
            const btnText = tabId === 'tab-twin' ? '3D Digital Twin' : 'Inspection Logs & Crops';
            document.querySelectorAll('.tab-btn').forEach(b => {
                if (b.innerText === btnText) b.classList.add('active');
            });

            if (tabId === 'tab-twin' && window.onResizeCanvas) {
                window.onResizeCanvas();
            }
        }

        // Slider value update helpers
        function updateSliderVal(name, val) {
            const el = document.getElementById('val-' + name);
            if (name === 'angle') el.innerText = val + '°';
            else if (name === 'height') el.innerText = parseFloat(val).toFixed(3) + 'm';
            else if (name === 'conf') el.innerText = parseFloat(val).toFixed(2);
            else if (name === 'size') el.innerText = parseFloat(val).toFixed(3) + 'm';
        }

        // Data arrays from pipeline backend
        let defectsData = __DEFECTS_JSON_LIST__;

        // Standard can dimensions (meters)
        const CAN_HEIGHT = 0.115;
        const CAN_BODY_RADIUS = 0.033;
        const BOTTOM_RIM_RADIUS = 0.0245;
        const BOTTOM_DOME_DEPTH = 0.012;
        const TOP_NECK_RADIUS = 0.027;
        const TOP_RIM_RADIUS = 0.0285;
        const TOP_LID_RADIUS = 0.0262;
        const h2 = CAN_HEIGHT / 2.0;

        // 3D Scene variables
        let container, scene, camera, renderer, controls;
        let canBodyMesh, pullTabMesh, combinedCanGroup;
        let activeMarkers = [];
        let cameraRigHelpers = [];
        let showCameraRig = false;
        let originalVertices = [];

        // Bezier 2D curve evaluator
        function evaluateBezier2D(p0, p1, p2, p3, numPoints) {
            const points = [];
            for (let i = 0; i < numPoints; i++) {
                const t = i / (numPoints - 1);
                const mt = 1 - t;
                const w0 = mt * mt * mt;
                const w1 = 3 * mt * mt * t;
                const w2 = 3 * mt * t * t;
                const w3 = t * t * t;
                const x = w0 * p0[0] + w1 * p1[0] + w2 * p2[0] + w3 * p3[0];
                const y = w0 * p0[1] + w1 * p1[1] + w2 * p2[1] + w3 * p3[1];
                points.push(new THREE.Vector2(x, y));
            }
            return points;
        }

        // Initialize 3D Engine
        function init3D() {
            container = document.getElementById('canvas-container');
            if (!container) return;

            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0e0e11);

            // Camera
            camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.01, 10);
            camera.position.set(0, 0.02, 0.22); // Front preset position

            // Renderer
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.shadowMap.enabled = true;
            container.appendChild(renderer.domElement);

            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.maxDistance = 0.4;
            controls.minDistance = 0.08;

            // Lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
            scene.add(ambientLight);

            const sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
            sunLight.position.set(0.1, 0.1, 0.2);
            scene.add(sunLight);

            const rimLight = new THREE.DirectionalLight(0xffffff, 0.7);
            rimLight.position.set(-0.1, 0.0, -0.2);
            scene.add(rimLight);

            // Generate procedural can profile
            const profilePoints = [];
            // 1. Bottom Dome
            profilePoints.push(...evaluateBezier2D([0.0, -h2 + BOTTOM_DOME_DEPTH], [0.008, -h2 + BOTTOM_DOME_DEPTH], [0.022, -h2 + 0.002], [0.022, -h2], 25));
            // 2. Bottom Rim
            profilePoints.push(...evaluateBezier2D([0.022, -h2], [0.022, -h2 - 0.0005], [0.0242, -h2 - 0.0005], [0.0245, -h2 + 0.001], 15));
            // 3. Bottom Taper
            profilePoints.push(...evaluateBezier2D([0.0245, -h2 + 0.001], [0.0250, -h2 + 0.005], [CAN_BODY_RADIUS, -h2 + 0.008], [CAN_BODY_RADIUS, -h2 + 0.015], 20));
            // 4. Main Body Cylindrical section
            const bodySteps = 50;
            for (let i = 0; i < bodySteps; i++) {
                const t = i / (bodySteps - 1);
                const y = (-h2 + 0.015) * (1 - t) + (h2 - 0.018) * t;
                profilePoints.push(new THREE.Vector2(CAN_BODY_RADIUS, y));
            }
            // 5. Top Shoulder Taper
            profilePoints.push(...evaluateBezier2D([CAN_BODY_RADIUS, h2 - 0.018], [CAN_BODY_RADIUS, h2 - 0.012], [TOP_NECK_RADIUS, h2 - 0.009], [TOP_NECK_RADIUS, h2 - 0.006], 30));
            // 6. Top Neck
            profilePoints.push(new THREE.Vector2(TOP_NECK_RADIUS, h2 - 0.006));
            profilePoints.push(new THREE.Vector2(TOP_NECK_RADIUS, h2 - 0.004));
            // 7. Rolled Rim Outer
            profilePoints.push(...evaluateBezier2D([TOP_NECK_RADIUS, h2 - 0.004], [TOP_NECK_RADIUS, h2 - 0.001], [TOP_RIM_RADIUS - 0.0005, h2], [TOP_RIM_RADIUS - 0.0005, h2], 15));
            // 8. Rolled Rim Inner
            profilePoints.push(...evaluateBezier2D([TOP_RIM_RADIUS - 0.0005, h2], [TOP_RIM_RADIUS - 0.0020, h2 - 0.0005], [TOP_LID_RADIUS, h2 - 0.0015], [TOP_LID_RADIUS, h2 - 0.0015], 15));
            // 9. Flat Lid
            profilePoints.push(new THREE.Vector2(TOP_LID_RADIUS, h2 - 0.0015));
            profilePoints.push(new THREE.Vector2(0.0, h2 - 0.0015));

            // Create Lathe Geometry
            const latheGeo = new THREE.LatheGeometry(profilePoints, 64);
            
            // Backup original vertices for deformation resets
            const posAttr = latheGeo.attributes.position;
            for (let i = 0; i < posAttr.count; i++) {
                originalVertices.push(new THREE.Vector3().fromBufferAttribute(posAttr, i));
            }

            const alumMaterial = new THREE.MeshStandardMaterial({
                color: 0xcccccc,  // Solid light grey
                metalness: 0.30,   // Low metalness to prevent turning black from dark environment
                roughness: 0.35,   // Semi-matte finish
                flatShading: false
            });

            canBodyMesh = new THREE.Mesh(latheGeo, alumMaterial);
            canBodyMesh.castShadow = true;
            canBodyMesh.receiveShadow = true;

            // Generate Pull-Tab procedural representation
            const tabGroup = new THREE.Group();
            const ringGeo = new THREE.RingGeometry(0.004, 0.008, 32);
            const tabMat = new THREE.MeshStandardMaterial({ color: 0x999999, metalness: 0.9, roughness: 0.2 });
            const tabRing = new THREE.Mesh(ringGeo, tabMat);
            tabRing.rotation.x = -Math.PI / 2;
            tabRing.position.set(0.008, h2 - 0.001, 0.0);
            tabGroup.add(tabRing);

            const tabBodyGeo = new THREE.BoxGeometry(0.02, 0.0005, 0.012);
            const tabBody = new THREE.Mesh(tabBodyGeo, tabMat);
            tabBody.position.set(0.008, h2 - 0.001, 0.0);
            tabGroup.add(tabBody);

            combinedCanGroup = new THREE.Group();
            combinedCanGroup.add(canBodyMesh);
            combinedCanGroup.add(tabGroup);
            scene.add(combinedCanGroup);

            // Setup camera rig helpers representation
            initCameraRigHelpers();

            // Setup initial defects
            refreshDefects();

            // Resize listener
            window.onResizeCanvas = function() {
                if (!container || !renderer) return;
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            };
            window.addEventListener('resize', window.onResizeCanvas);

            // Start animation loop
            animate();
        }

        // Setup Representation of Camera Rig
        function initCameraRigHelpers() {
            const rigCameras = [
                { name: "Cam_Front", pos: [0.0, 0.0, 0.22] },
                { name: "Cam_Back", pos: [0.0, 0.0, -0.22] },
                { name: "Cam_Left", pos: [-0.22, 0.0, 0.0] },
                { name: "Cam_Right", pos: [0.22, 0.0, 0.0] },
                { name: "Cam_Top", pos: [0.0, 0.22, 0.0] },
                { name: "Cam_Bottom", pos: [0.0, -0.22, 0.0] }
            ];

            rigCameras.forEach(cam => {
                // Draw a small camera box/cone representation
                const camGeo = new THREE.ConeGeometry(0.008, 0.018, 4);
                const camMat = new THREE.MeshBasicMaterial({ color: 0xdd0b12, wireframe: true });
                const helper = new THREE.Mesh(camGeo, camMat);
                helper.position.set(cam.pos[0], cam.pos[1], cam.pos[2]);
                
                // Point camera helper to the center can body
                helper.lookAt(0, 0, 0);
                helper.rotateX(Math.PI / 2); // Correct direction
                
                helper.visible = showCameraRig;
                scene.add(helper);
                cameraRigHelpers.push(helper);
            });
        }

        // Toggle camera rig representation
        function toggleCameraRig() {
            showCameraRig = !showCameraRig;
            cameraRigHelpers.forEach(helper => {
                helper.visible = showCameraRig;
            });
            const btn = document.getElementById('btn-cam-rig');
            if (showCameraRig) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }

        // Surface coordinates mapper (cylinder coordinate mapping loopback check equivalent)
        function getSurfaceCoords(angleDeg, height) {
            const theta = angleDeg * Math.PI / 180;
            const x = CAN_BODY_RADIUS * Math.cos(theta);
            const z = CAN_BODY_RADIUS * Math.sin(theta);
            return new THREE.Vector3(x, height, z);
        }

        // Refresh Can deform status and markers based on data array
        function refreshDefects() {
            // 1. Clear active markers
            activeMarkers.forEach(m => scene.remove(m));
            activeMarkers = [];

            // 2. Reset mesh vertices to original can model
            const posAttr = canBodyMesh.geometry.attributes.position;
            for (let i = 0; i < posAttr.count; i++) {
                posAttr.setXYZ(i, originalVertices[i].x, originalVertices[i].y, originalVertices[i].z);
            }

            // 3. Deform can mesh for dents
            defectsData.forEach(d => {
                if (d.type === 'dent') {
                    applyDentDeformation(d.angle, d.height, d.size || 0.003);
                }
            });

            // Mark positions buffer as needing update
            posAttr.needsUpdate = true;
            canBodyMesh.geometry.computeVertexNormals();

            // 4. Place pulsating markers
            defectsData.forEach(d => {
                const pos = getSurfaceCoords(d.angle, d.height);
                const color = d.type === 'dent' ? 0xdd0b12 : 0x0076ff;
                
                const markerGeo = new THREE.SphereGeometry(d.size ? d.size * 0.8 : 0.0024, 16, 16);
                const markerMat = new THREE.MeshBasicMaterial({ color: color, transparent: true, opacity: 0.85 });
                const marker = new THREE.Mesh(markerGeo, markerMat);
                marker.position.copy(pos);
                
                // Add reference to defect ID
                marker.userData = { defectId: d.id, baseSize: d.size || 0.003 };
                scene.add(marker);
                activeMarkers.push(marker);
            });

            // 5. Re-render HTML Sidebar list
            updateSidebarList();

            // 6. Update general metrics
            updateGeneralMetrics();
        }

        // Apply dynamic dent indentation (CPU vertex shift equivalent to deform_mesh_for_dent)
        function applyDentDeformation(dentAngle, dentHeight, size) {
            const dentAngleRad = dentAngle * Math.PI / 180;
            const dentRadius = size * 2.2;
            const dentDepth = size * 0.7;

            const posAttr = canBodyMesh.geometry.attributes.position;
            const v = new THREE.Vector3();

            for (let i = 0; i < posAttr.count; i++) {
                v.fromBufferAttribute(posAttr, i);
                
                // Get vertex angular coordinates
                let vAngle = Math.atan2(v.z, v.x);
                if (vAngle < 0) vAngle += Math.PI * 2;
                
                let diffAngle = Math.abs(vAngle - dentAngleRad);
                if (diffAngle > Math.PI) diffAngle = Math.PI * 2 - diffAngle;

                const arcDistance = CAN_BODY_RADIUS * diffAngle;
                const vDistance = v.y - dentHeight;
                const dist = Math.sqrt(arcDistance * arcDistance + vDistance * vDistance);

                if (dist < dentRadius) {
                    const indent = dentDepth * Math.cos((Math.PI / 2) * (dist / dentRadius));
                    // Indent toward center axis (0, y, 0)
                    const radialDirectionX = -Math.cos(vAngle);
                    const radialDirectionZ = -Math.sin(vAngle);
                    
                    posAttr.setXYZ(
                        i, 
                        v.x + radialDirectionX * indent, 
                        v.y, 
                        v.z + radialDirectionZ * indent
                    );
                }
            }
        }

        // Render defects list on HTML Sidebar
        function updateSidebarList() {
            const listEl = document.getElementById('active-defect-list');
            listEl.innerHTML = '';

            if (defectsData.length === 0) {
                listEl.innerHTML = '<div class="no-defects">No defects detected.</div>';
                return;
            }

            defectsData.forEach(d => {
                const row = document.createElement('div');
                row.className = 'defect-item';

                const btn = document.createElement('button');
                btn.className = `defect-btn ${d.type}`;
                btn.innerText = `[${d.type.toUpperCase()}] ${d.id} (${(d.confidence * 100).toFixed(0)}%)`;
                btn.onclick = () => focusOnDefect(d);

                const delBtn = document.createElement('button');
                delBtn.className = 'defect-delete-btn';
                delBtn.innerText = 'X';
                delBtn.onclick = () => handleDeleteDefect(d.id);

                row.appendChild(btn);
                row.appendChild(delBtn);
                listEl.appendChild(row);
            });
        }

        // Update PASS/FAIL and statistics metrics
        function updateGeneralMetrics() {
            const numDents = defectsData.filter(d => d.type === 'dent').length;
            const numScratches = defectsData.filter(d => d.type === 'scratch').length;
            
            // Update counter values
            document.getElementById('metrics-dents').innerText = numDents;
            document.getElementById('metrics-scratches').innerText = numScratches;

            // Re-evaluate pass/fail status
            const hasCriticalDents = defectsData.some(d => d.type === 'dent' && d.confidence > 0.80);
            const tooManyScratches = numScratches > 3;
            const passes = !hasCriticalDents && !tooManyScratches;

            const badge = document.getElementById('sidebar-status-badge');
            if (passes) {
                badge.innerText = 'STATUS: PASS';
                badge.className = 'status-badge pass';
            } else {
                badge.innerText = 'STATUS: REJECTED';
                badge.className = 'status-badge fail';
            }
        }

        // Defect selection zoom/orbit animation
        function focusOnDefect(defect) {
            const pos = getSurfaceCoords(defect.angle, defect.height);
            
            // Position camera slightly facing the defect perpendicular normal vector
            const angleRad = defect.angle * Math.PI / 180;
            const normalX = Math.cos(angleRad);
            const normalZ = Math.sin(angleRad);
            
            const targetCamPos = new THREE.Vector3(
                pos.x + 0.14 * normalX,
                pos.y + 0.015,
                pos.z + 0.14 * normalZ
            );

            // Animate target focus and camera position
            controls.target.copy(pos);
            camera.position.copy(targetCamPos);
            controls.update();
        }

        // Helper to focus on defect by ID (used for cross-tab linking)
        function focusOnDefectById(defectId) {
            const d = defectsData.find(x => x.id === defectId);
            if (d) focusOnDefect(d);
        }

        // Delete active defect marker
        function handleDeleteDefect(defectId) {
            defectsData = defectsData.filter(d => d.id !== defectId);
            
            // Delete its detail card in Tab 2 if present
            const card = document.getElementById('card-' + defectId);
            if (card) card.remove();

            refreshDefects();
        }

        // Inject defect using UI slider inputs
        function handleInjectDefect() {
            const type = document.getElementById('inject-type').value;
            const angle = parseInt(document.getElementById('inject-angle').value);
            const height = parseFloat(document.getElementById('inject-height').value) / 1000;
            const confidence = parseFloat(document.getElementById('inject-conf').value) / 100;
            const size = parseFloat(document.getElementById('inject-size').value) / 1000;

            const newId = 'DEF_INJ_' + Math.floor(Math.random() * 900 + 100);
            
            const newDefect = {
                id: newId,
                type: type,
                angle: angle,
                height: height,
                confidence: confidence,
                size: size,
                camera_id: "Manual_Injection",
                area_mm2: (Math.PI * Math.pow(size * 1000, 2)).toFixed(1)
            };

            if (type === 'dent') {
                newDefect.diameter_mm = (size * 2000).toFixed(1);
                newDefect.depth_mm = (size * 700).toFixed(2);
                newDefect.severity = confidence > 0.80 ? "Critical" : "Major";
            } else {
                newDefect.length_mm = (size * 4000).toFixed(1);
                newDefect.width_mm = (size * 800).toFixed(2);
            }

            defectsData.push(newDefect);
            
            // Dynamically inject detail card in Tab 2
            injectDefectCard(newDefect);

            refreshDefects();
        }

        // Add detail card to Tab 2
        function injectDefectCard(d) {
            const grid = document.getElementById('details-defects-grid');
            if (!grid) return;

            const card = document.createElement('div');
            card.id = 'card-' + d.id;
            card.className = `defect-card ${d.type}`;

            const imgArea = document.createElement('div');
            imgArea.className = 'defect-image-area';
            imgArea.innerHTML = '<div class="no-image-label">Manual Injection<br>No Camera Crop</div>';
            card.appendChild(imgArea);

            const infoArea = document.createElement('div');
            infoArea.className = 'defect-info-area';

            const title = document.createElement('div');
            title.className = `defect-info-title ${d.type}`;
            title.innerHTML = `<span>[${d.type.toUpperCase()}] ${d.id}</span> <span class="defect-badge ${d.type}">INJECTED</span>`;
            infoArea.appendChild(title);

            const details = document.createElement('div');
            details.className = 'details-list';
            
            if (d.type === 'dent') {
                details.innerHTML = `
                    <div class="details-item"><span class="details-label">Diameter</span><span class="details-value">${d.diameter_mm} mm</span></div>
                    <div class="details-item"><span class="details-label">Depth</span><span class="details-value">${d.depth_mm} mm</span></div>
                    <div class="details-item"><span class="details-label">Area</span><span class="details-value">${d.area_mm2} mm²</span></div>
                    <div class="details-item"><span class="details-label">Severity</span><span class="details-value">${d.severity}</span></div>
                `;
            } else {
                details.innerHTML = `
                    <div class="details-item"><span class="details-label">Length</span><span class="details-value">${d.length_mm} mm</span></div>
                    <div class="details-item"><span class="details-label">Width</span><span class="details-value">${d.width_mm} mm</span></div>
                    <div class="details-item"><span class="details-label">Area</span><span class="details-value">${d.area_mm2} mm²</span></div>
                `;
            }

            details.innerHTML += `
                <div class="details-item"><span class="details-label">Confidence</span><span class="details-value">${(d.confidence*100).toFixed(0)}%</span></div>
                <div class="details-item"><span class="details-label">Angle</span><span class="details-value">${d.angle.toFixed(1)}°</span></div>
                <div class="details-item"><span class="details-label">Height</span><span class="details-value">${d.height.toFixed(3)} m</span></div>
                <div class="details-item"><span class="details-label">Camera</span><span class="details-value">${d.camera_id}</span></div>
            `;

            infoArea.appendChild(details);
            card.appendChild(infoArea);
            grid.appendChild(card);
        }

        // Setup camera position presets
        function setCameraPreset(preset) {
            const dist = 0.22;
            document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
            
            const btn = document.getElementById('btn-cam-' + preset.toLowerCase());
            if (btn) btn.classList.add('active');

            controls.target.set(0, 0, 0);

            if (preset === 'Front') camera.position.set(0, 0.015, dist);
            else if (preset === 'Back') camera.position.set(0, 0.015, -dist);
            else if (preset === 'Left') camera.position.set(-dist, 0.015, 0);
            else if (preset === 'Right') camera.position.set(dist, 0.015, 0);
            else if (preset === 'Top') camera.position.set(0, dist, 0);
            else if (preset === 'Bottom') camera.position.set(0, -dist, 0);

            controls.update();
        }

        // Main animation loop
        let clock = new THREE.Clock();
        function animate() {
            requestAnimationFrame(animate);
            
            const elapsedTime = clock.getElapsedTime();
            controls.update();

            // Animate active pulsating markers
            activeMarkers.forEach(m => {
                // Pulse size
                const pulse = 1.0 + 0.20 * Math.sin(elapsedTime * 8);
                m.scale.set(pulse, pulse, pulse);
            });

            renderer.render(scene, camera);
        }

        // Start 3D Engine on page load
        window.onload = function() {
            init3D();
        };
    </script>
</body>
</html>
"""
