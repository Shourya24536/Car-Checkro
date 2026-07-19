# Flask-based HTTP API Receiver and Dashboard Server
import os
import time
import queue
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from .config import PORT, HOST, API_PREFIX, REPORTS_DIR, DIGITAL_TWINS_DIR, INSPECTIONS_DIR, CROPS_DIR
from .parser import parse_multipart_request
from .logger import log_info, log_error, log_warn, log_raw_payload

# Initialize Flask app
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"))

# Startup timestamp for uptime calculation
START_TIME = time.time()
LAST_INSPECTION_TIME = None

# Active SSE listener queues
sse_listeners = []
sse_lock = threading_lock = None # Python lock initialized below

class SSEManager:
    """Manages Server-Sent Events subscribers and broadcasting."""
    def __init__(self):
        import threading
        self.listeners = []
        self.lock = threading.Lock()

    def add_listener(self):
        q = queue.Queue(maxsize=100)
        with self.lock:
            self.listeners.append(q)
        return q

    def remove_listener(self, q):
        with self.lock:
            if q in self.listeners:
                self.listeners.remove(q)

    def broadcast(self, event_type: str, data: dict):
        payload = {"event": event_type, "data": data, "timestamp": datetime.now().isoformat()}
        with self.lock:
            for q in self.listeners:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    # Drop message if client is disconnected or slow
                    pass

sse_manager = SSEManager()

# --- HTTP ENDPOINTS ---

@app.route(f"{API_PREFIX}/health", methods=["GET"])
def health():
    """Receiver Health Check Endpoint."""
    global LAST_INSPECTION_TIME
    manager = app.config.get("INSPECTION_MANAGER")
    stats = manager.database.get_stats() if manager else {}
    
    uptime_sec = time.time() - START_TIME
    uptime_str = str(datetime.utcfromtimestamp(uptime_sec).strftime('%H:%M:%S'))
    
    return jsonify({
        "status": "ok",
        "receiver": "running",
        "version": "1.0",
        "uptime": uptime_str,
        "last_inspection": LAST_INSPECTION_TIME,
        "database_stats": stats
    }), 200


@app.route(f"{API_PREFIX}/inspection", methods=["POST"])
def post_inspection():
    """
    Receives inspection metadata and camera/crops multipart form upload from UNO Q.
    """
    global LAST_INSPECTION_TIME
    manager = app.config.get("INSPECTION_MANAGER")
    if not manager:
        log_error("InspectionManager not registered on Flask application config.")
        return jsonify({"status": "error", "message": "Server initialization incomplete."}), 500

    # 1. Check for metadata field
    metadata_str = request.form.get("metadata")
    if not metadata_str:
        log_error("Missing 'metadata' parameter in form-data.")
        return jsonify({"status": "error", "message": "Missing 'metadata' field in multipart request."}), 400

    # 2. Parse payload and attachments
    try:
        # Load raw JSON payload dictionary for logging before converting to models
        raw_payload = json.loads(metadata_str)
        request_id = raw_payload.get("request_id")
        
        # Save raw JSON copy
        if request_id:
            log_raw_payload(request_id, raw_payload)
            
        # Parser constructs immutable model
        msg = parse_multipart_request(metadata_str, request.files)
    except ValueError as val_err:
        log_error(f"Validation error: {val_err}")
        return jsonify({"status": "error", "message": str(val_err)}), 400
    except Exception as e:
        log_error(f"Error parsing request payload: {e}")
        return jsonify({"status": "error", "message": "Internal parser error."}), 500

    # 3. Dispatch to InspectionManager (orchestrated pipeline execution)
    LAST_INSPECTION_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Run the manager update (which handles database, digital twin, report generator, logs, SSE)
    success = manager.handle_new_inspection(msg)
    
    if success:
        return jsonify({
            "status": "success",
            "request_id": msg.request_id,
            "inspection_id": msg.inspection_id,
            "message": "Inspection successfully processed."
        }), 200
    else:
        return jsonify({
            "status": "partial_success",
            "request_id": msg.request_id,
            "inspection_id": msg.inspection_id,
            "message": "Inspection received, but report generation steps encountered errors."
        }), 202


# --- DASHBOARD WEB INTERFACE ---

@app.route("/", methods=["GET"])
@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Renders the HTML live inspection monitoring dashboard."""
    manager = app.config.get("INSPECTION_MANAGER")
    stats = manager.database.get_stats() if manager else {}
    history = manager.database.get_history(limit=30) if manager else []
    return render_template("dashboard.html", stats=stats, history=history)


@app.route("/stream", methods=["GET"])
def sse_stream():
    """Server-Sent Events route to push live updates to dashboard client."""
    q = sse_manager.add_listener()
    
    def event_generator():
        # Push initial connection status
        yield f"data: {json.dumps({'event': 'connected', 'message': 'SSE Connection Established'})}\n\n"
        try:
            while True:
                # Wait for event
                payload = q.get()
                yield f"data: {json.dumps(payload)}\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_manager.remove_listener(q)

    return Response(event_generator(), mimetype="text/event-stream")


# --- STATIC FILES ROUTING (Reports, Images, Twins) ---

@app.route("/output/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORTS_DIR, filename)

@app.route("/output/digital_twins/<path:filename>")
def serve_twin(filename):
    return send_from_directory(DIGITAL_TWINS_DIR, filename)

@app.route("/output/inspections/<path:filename>")
def serve_inspection_image(filename):
    return send_from_directory(INSPECTIONS_DIR, filename)

@app.route("/output/crops/<path:filename>")
def serve_crop_image(filename):
    return send_from_directory(CROPS_DIR, filename)

# Shutdown helper
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'
